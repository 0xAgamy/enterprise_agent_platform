import json
from pathlib import Path

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from stores.PostgresDB.models.warehouse import Inventory
from stores.PostgresDB.models.database import AsyncSessionLocal

from datetime import datetime

DATA_FILE = Path("data/warehouse.json")


async def seed_inventory():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for item in data.values():
        rows.append(
            {
                "warehouse_id": item["warehouse_id"],
                "product_id": item["product_id"],
                "total_quantity": item["total_quantity"],
                "reserved_quantity": item["reserved_quantity"],
                "warehouse_location": item.get("warehouse_location"),
                "warehouse_name": item.get("warehouse_name"),
                "estimated_processing_days": item.get(
                    "estimated_processing_days",
                    1,
                ),
                "updated_at": datetime.fromisoformat(item["updated_at"]),
            }
        )

    async with AsyncSessionLocal() as session:
        await session.execute(
            insert(Inventory),
            rows,
        )

        await session.commit()


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_inventory())