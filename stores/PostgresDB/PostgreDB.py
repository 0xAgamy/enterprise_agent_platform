from psycopg2 import pool
from psycopg2.extras import RealDictCursor
class PostgreService:
    def __init__(self, Db_url:str):
        self.Db_url= Db_url
        self.connection_pool= self._get_connection_pool()

    def _get_connection_pool(self):
        return pool.SimpleConnectionPool(1,20,self.Db_url)

    def get_product_by_id(self,product_id:str):
        conn= self.connection_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query="""
                SELECT parent_asin, description, rating_number, image, average_rating, price
                FROM product.product
                WHERE parent_asin = %s
                """
                cursor.execute(query,(product_id,))
                product= cursor.fetchone()
                return product
        finally:
            self.connection_pool.putconn(conn)



    def get_products_by_ids(self, product_ids: list[str]):
        conn = self.connection_pool.getconn()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                    SELECT parent_asin, description, rating_number,
                        image, average_rating, price
                    FROM product.product
                    WHERE parent_asin = ANY(%s)
                """

                cursor.execute(query, (product_ids,))
                return cursor.fetchall()

        finally:
            self.connection_pool.putconn(conn)

    ### Shopping Cart
    def _check_cart_item_exist(self, user_id:str, shopping_cart_id:str, product_id:str):
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                check_query= """
                SELECT id, quantity, price
                FROM shopping_carts.shopping_cart_items
                WHERE user_id = %s AND shopping_cart_id = %s AND product_id= %s
                """
                cursor.execute(check_query,(user_id,shopping_cart_id, product_id))
                existing_item= cursor.fetchone()
                return existing_item
        finally:
            self.connection_pool.putconn(conn)

    def _cart_update_quantity(self,user_id:str,product_id:str, max_quantity, price, product_image_url,cart_id):
        conn = self.connection_pool.getconn()
        currency="USD"
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                update_query="""
                UPDATE shopping_carts.shopping_cart_items
                SET
                    quantity = %s,
                    price = %s,
                    currency = %s,
                    product_image_url = COALESCE(%s, product_image_url)
                WHERE user_id =  %s AND shopping_cart_id = %s AND product_id = %s
                RETURNING id, quantity, price
            """
                cursor.execute(update_query,(max_quantity,price, currency, product_image_url, user_id, cart_id, product_id))
                result=cursor.fetchone()
            conn.commit()
            return result
        except Exception:
                conn.rollback()
                raise
        finally:
            self.connection_pool.putconn(conn)

    def _insert_into_cart(self, user_id, cart_id, product_id, price, quantity,product_image_url):
        conn = self.connection_pool.getconn()
        currency="USD"
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                insert_query="""
                INSERT INTO shopping_carts.shopping_cart_items (
                    user_id, shopping_cart_id, product_id,
                    price, quantity, currency, product_image_url
                    ) VALUES (%s, %s, %s,%s,%s,%s,%s)
                    RETURNING id, quantity, price
                """
                cursor.execute(insert_query, (user_id, cart_id, product_id, price, quantity, currency,product_image_url))
                result=cursor.fetchone()
            conn.commit()
            return result
        except Exception:
                conn.rollback()
                raise

        finally:
            self.connection_pool.putconn(conn)


    def add_to_shopping_cart(self,items:list[dict], user_id:str, cart_id:str):
        for item in items:
            product_id= item["product_id"]
            quantity= item["quantity"]
            product=self.get_product_by_id(product_id)
            price= product.get("price")
            product_image_url= product.get("image")

            existing_item=self._check_cart_item_exist(user_id,cart_id,product_id)
            if existing_item:
                max_quantity= existing_item["quantity"] + quantity
                _=self._cart_update_quantity(user_id,product_id,max_quantity,price,product_image_url,cart_id)
            else:
                _=self._insert_into_cart(
                                    user_id,
                                    cart_id,
                                    product_id,
                                    price,
                                    quantity,
                                    product_image_url
                                    )
                
        return f"{items} successfully added to the user shopping cart"        

    def get_user_shopping_cart(self,user_id:str, cart_id:str):
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                get_query="""
                SELECT 
                    product_id , price, quantity, 
                    currency,
                    (price * quantity) as total_price
                FROM shopping_carts.shopping_cart_items
                WHERE user_id = %s AND shopping_cart_id = %s
                ORDER BY added_at DESC
                """
                cursor.execute(get_query,(user_id,cart_id))
                return [ dict(row) for row in cursor.fetchall()]
        finally:
            self.connection_pool.putconn(conn)
            
    def remove_from_shopping_cart(self, product_id, user_id, cart_id):
        conn = self.connection_pool.getconn()
        try:
            conn.autocommit=True
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query= """
            DELETE FROM shopping_carts.shopping_cart_items
            WHERE user_id = %s AND shopping_cart_id = %s AND product_id = %s
            """
                cursor.execute(query,(user_id,cart_id,product_id))
                deleted= cursor.rowcount > 0 
            conn.commit()
            return cursor.rowcount > 0 
        except Exception:
            conn.rollback()
            raise
        finally:
            self.connection_pool.putconn(conn)







                
