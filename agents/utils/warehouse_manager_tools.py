import psycopg2
from psycopg2.extras import RealDictCursor
from helpers.config import get_settings
from langsmith import traceable
settings= get_settings()
conn= psycopg2.connect(settings.PRESISTANCE_STATE_URL)


@traceable(
        name="Check item Availability",
        run_type="tool"
)
def check_warehouse_availability(items:list[dict])-> dict:
    """Check availability of items across warehouse, including partial fulfilment options.
    
    Args:
        items: list of items to check. Each item is a dictionary with keys: product_id, quantity.
    
    Return:
        A dictionary containing:
            - can_fulfill_completely: bool indicating if all items can be fullfilled from at least one warehouse.
            - warehouse_full_fulfillment: list of warehouses that can fulfill the entire order.
            - warehouse_partial_fulfillment: list of warehouses that with partial availability.
            - unavailable_items: list of items that cannot be fullfilled from any warehouse.
            - details: detailed breakdown per warehouse with availability for each item. 
    """
    conn.autocommit= False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            result={
                "can_fulfill_completely":False,
                "warehouse_full_fulfillment":[],
                "warehouse_partial_fulfillment":[],
                "unavailable_items": [],
                "details":[]
            }

            warehouse_query="""
            SELECT DISTINCT warehouse_id, warehouse_name, warehouse_location
            FROM warehouses.inventory
            """

            cursor.execute(warehouse_query)
            warehouses= cursor.fetchall()

            for warehouse in warehouses:
                warehouse_can_fulfill_all= True
                has_any_availability=False
                warehouse_details={
                        "warehouse_id":warehouse["warehouse_id"],
                        "warehouse_name":warehouse["warehouse_name"],
                        "warehouse_location":warehouse["warehouse_location"],
                        "items": [],
                        "can_fulfill_all":False,
                        "has_partial": False

                }

                for item in items:
                    product_id= item["product_id"]
                    requested_quantity= item["quantity"]


                    availability_query= """
                    SELECT product_id, total_quantity, reserved_quantity, available_quantity
                    FROM warehouses.inventory
                    WHERE warehouse_id = %s AND product_id = %s
                    """

                    cursor.execute(availability_query, (warehouse["warehouse_id"], product_id))
                    inventory= cursor.fetchone()
                
                    available_quantity = inventory["available_quantity"] if inventory else 0

                    item_details={
                        "product_id": product_id,
                        "requested":requested_quantity,
                        "available":available_quantity,

                        "can_fulfill_complately":available_quantity>= requested_quantity  ,
                        "can_fulfill_partialy": available_quantity>0 and  available_quantity < requested_quantity
                    }

                    warehouse_details["items"].append(item_details)

                    if available_quantity < requested_quantity:
                        warehouse_can_fulfill_all= False

                    if available_quantity > 0:
                        has_any_availability= True


                if warehouse_can_fulfill_all:
                    warehouse_details["can_fulfill_all"]= True
                    result["warehouse_full_fulfillment"].append({
                        "warehouse_id":warehouse["warehouse_id"],
                        "warehouse_name":warehouse["warehouse_name"],
                        "warehouse_location":warehouse["warehouse_location"],
                    })
                elif  has_any_availability:
                    warehouse_details["has_partial"]= True
                    result["warehouse_partial_fulfillment"].append({
                        "warehouse_id":warehouse["warehouse_id"],
                        "warehouse_name":warehouse["warehouse_name"],
                        "warehouse_location":warehouse["warehouse_location"],
                    })

                result["details"].append(warehouse_details)

            for item in items:
                product_id= item["product_id"]
                requested_quantity= item['quantity']

                total_ava_query="""
                SELECT product_id, SUM(available_quantity) as total_available
                FROM warehouses.inventory
                WHERE product_id = %s
                GROUP BY product_id    
                """

                cursor.execute(total_ava_query,(product_id,))
                total_available=cursor.fetchone()

                total_available_qty= total_available["total_available"] if total_available else 0


                if total_available_qty < requested_quantity:
                    result['unavailable_items'].append({
                        "product_id":product_id,
                        "requested": requested_quantity,
                        "total_available_across_warehouses": total_available_qty,
                        "shortage": requested_quantity - total_available_qty
                    })


            result["can_fulfill_completely"]= len(result["warehouse_full_fulfillment"]) > 0 and len(result["unavailable_items"]) ==0 
            return result



    finally :
        conn.close()

@traceable(
        name="Reserve item from warehouses",
        run_type="tool"
)
def reserve_warehouse_items(reservations:list[dict])->dict:
    """
    Reserve items for multiple warehouse in a single transaction.

    Args:
        - Reservation: A list of reservation. Each reservation is a dictionary with keys:
            - warehouse_id : The warehouse to reserve from.
            - product_id : The product to reserve.
            - quantity : The quantity to reserve.
    
    Returns:
        A dctionary containing :
            - success : bool indicating if all reservations were successful.
            - reserved_items: list of successfully reserved items.
            - failed_items: list of items that could be reserved.
    """
    conn.autocommit= False
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            result={
                "success": False,
                "reserved_items": [],
                "failed_items":[]
            }

            for reservation in reservations:
                warehouse_id= reservation["warehouse_id"]
                product_id= reservation["product_id"]
                quantity= reservation["quantity"]


                check_query="""
                SELECT warehouse_id , product_id, warehouse_name, warehouse_location,
                    total_quantity, reserved_quantity, available_quantity
                FROM warehouses.inventory
                WHERE warehouse_id = %s AND product_id = %s 
                FOR UPDATE
                """

                cursor.execute(check_query,(warehouse_id,product_id))
                inventory= cursor.fetchone()

                if inventory and inventory["available_quantity"] >= quantity:
                    update_query="""
                    UPDATE warehouses.inventory
                    SET reserved_quantity = reserved_quantity + %s
                    WHERE  warehouse_id = %s AND product_id = %s

                    
                    """
                    cursor.execute(update_query, (quantity,warehouse_id,product_id))
                    

                    result["reserved_items"].append({
                        "product_id":product_id,
                        "quantity":quantity,
                        "warehouse_id": warehouse_id,
                        "warehouse_name": inventory["warehouse_name"],
                        "warehouse_location": inventory["warehouse_location"]
                    })
                else:
                    result["failed_items"].append({
                        "product_id":product_id,
                        "warehouse_id": warehouse_id,
                        "requested":quantity,
                        "available": inventory["available_quantity"] if inventory else 0,
                        "reason": "insufficient_stock"  if inventory else "not_in_warehouse"
                        
                    })

            if len(result["failed_items"]) ==0:
                conn.commit()
                result['success']= True
            else:
                conn.rollback()
                result['success']= False
            
            return result


    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()