from qdrant_client import QdrantClient
from qdrant_client.models import  FieldCondition, Filter, Prefetch, FusionQuery, MatchAny, Document, MatchValue
from psycopg2.extras import RealDictCursor
from typing import Annotated
from psycopg2 import pool
from langgraph.prebuilt import InjectedState
from agents.models.agents_state import AgentState
from langsmith import traceable
from helpers.config import get_settings
settings=get_settings()

qd_client= QdrantClient(url=settings.QDRANT_URL)
connection_pool= pool.SimpleConnectionPool(
    1,
    10,
    settings.PRESISTANCE_STATE_URL
)



@traceable(
        name="Add items to user shopping cart",
        run_type="tool"
)
def adding_to_shopping_cart(items: list[dict], state: Annotated[AgentState, InjectedState]):
    """Adding a list of provided itmes to the shopping cart

    Args:
        items: a list of items to add to the shopping cart. Each item is a dictonary with the following keys: product_id, quantity.
        state: the Agent state
    Returns:
        A list of the items adding to shopping cart.
    """
    conn = connection_pool.getconn()
    user_id= state.user_id
    cart_id= state.cart_id
    conn.autocommit= True

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        for item in items:
            product_id = item["product_id"]
            quantity= item["quantity"]


            payload= qd_client.query_points(
                collection_name=settings.QDRANT_ITEMS_COLLECTION_NAME,
                prefetch=[
                    Prefetch(
                        filter=Filter(
                            must=[
                                FieldCondition(
                                    key="parent_asin",
                                    match=MatchValue(value=product_id)
                                )
                            ]
                        ),
                    limit=20
                    )
                ],
                query=FusionQuery(fusion='rrf'),
                limit=1,

            ).points[0].payload
            product_image_url= payload.get("image")
            price= payload.get("price")
            currency="USD"   

            ## Check if the item is already exist

            check_query="""
            SELECT id, quantity, price
            FROM shopping_carts.shopping_cart_items
            WHERE user_id = %s AND shopping_cart_id = %s AND product_id= %s
            """

            cursor.execute(check_query,(user_id,cart_id, product_id))

            existing_item= cursor.fetchone()

            if existing_item:
                max_quantity= existing_item["quantity"] + quantity

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
            else:
                # INSERT NEW items
                insert_query= """
                INSERT INTO shopping_carts.shopping_cart_items (
                user_id, shopping_cart_id, product_id,
                price, quantity, currency, product_image_url
                ) VALUES (%s, %s, %s,%s,%s,%s,%s)
                RETURNING id, quantity, price
                """
                cursor.execute(insert_query, (user_id, cart_id, product_id, price, quantity, currency,product_image_url))
    connection_pool.putconn(conn)
    return f"{items} successfully added to the user  shopping cart"        

@traceable(
        name="Get user items from shopping cart",
        run_type="tool"
)
def getting_shopping_cart(state: Annotated[AgentState, InjectedState]):
    """Retrieve all items in a user's shopping cart

    Args:
        state: the Agent state
    Return:
        List of dictionaries containing cart items
    """
    conn = connection_pool.getconn()

    user_id= state.user_id
    cart_id= state.cart_id
    conn.autocommit= True

    with conn.cursor(cursor_factory=RealDictCursor) as cursor :
        query= """
        SELECT 
            product_id , price, quantity, 
            currency
            (price * quantity) as total_price
        FROM shopping_carts.shopping_cart_items
        WHERE user_id = %s AND shopping_cart_id = %s
        ORDER BY added_at DESC
        """
        cursor.execute(query,(user_id,cart_id))
        connection_pool.putconn(conn)
        return [ dict(row) for row in cursor.fetchall()]


@traceable(
        name="Remove user item in shopping cart",
        run_type="tool"
)
def remove_from_cart(product_id:str,  state: Annotated[AgentState, InjectedState])->bool:
    """Remove an item complately from the shopping cart

    Args:
        product_id: Product ID to remove
        state: the Agent state
    Return:
        True if item was removed, False if the item wasn't found

    """
    conn = connection_pool.getconn()

    user_id= state.user_id
    cart_id= state.cart_id
    conn.autocommit= True
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor :
        query= """
            DELETE FROM shopping_carts.shopping_cart_items
            WHERE user_id = %s AND shopping_cart_id = %s AND product_id = %s
        """
        cursor.execute(query,(user_id,cart_id,product_id))

        return cursor.rowcount > 0 
    conn.close()
    connection_pool.putconn(conn)


def getting_user_shopping_cart(user_id:str, cart_id:str):
    """Retrieve all items in a user's shopping cart

    Args:
        user_id: shopping cart user's id
        cart_id: shopping cart cart's id
    Return:
        List of dictionaries containing cart items
    """
    conn = connection_pool.getconn()

    conn.autocommit= True

    with conn.cursor(cursor_factory=RealDictCursor) as cursor :
        query= """
        SELECT 
            product_id , price, quantity, 
            currency, product_image_url,
            (price * quantity) as total_price
        FROM shopping_carts.shopping_cart_items
        WHERE user_id = %s AND shopping_cart_id = %s
        ORDER BY added_at DESC
        """
        cursor.execute(query,(user_id,cart_id))
        return [ dict(row) for row in cursor.fetchall()]
    connection_pool.putconn(conn)