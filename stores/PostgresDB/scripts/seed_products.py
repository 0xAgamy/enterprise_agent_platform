import asyncio
import json

from sqlalchemy import select

from stores.PostgresDB.models.database import AsyncSessionLocal
from stores.PostgresDB.models.products import Product


JSONL_FILE = "data/data.json"


async def seed_products():
    async with AsyncSessionLocal() as session:

        with open(JSONL_FILE, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):

                # Skip empty lines
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON on line {line_number}: {e}")
                    continue

                parent_asin = data.get("parent_asin")

                if not parent_asin:
                    print(f"Skipping line {line_number}: no parent_asin")
                    continue

                # Check if product already exists
                result = await session.execute(
                    select(Product).where(
                        Product.parent_asin == parent_asin
                    )
                )

                existing_product = result.scalar_one_or_none()

                if existing_product:
                    continue

                product = Product(
                    parent_asin=parent_asin,
                    description=data.get("description"),
                    rating_number=data.get("rating_number"),
                    image=data.get("image"),
                    average_rating=data.get("average_rating"),
                    price=data.get("price"),
                )

                session.add(product)

        await session.commit()

    print("Products seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_products())
