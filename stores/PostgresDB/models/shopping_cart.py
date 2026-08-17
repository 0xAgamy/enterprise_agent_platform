# models/shopping_cart.py

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Integer,
    Numeric,
    String,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.database import Base


class ShoppingCartItem(Base):
    __tablename__ = "shopping_cart_items"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "shopping_cart_id",
            "product_id",
            name="unique_user_cart_product",
        ),
        CheckConstraint(
            "price >= 0",
            name="positive_price",
        ),
        CheckConstraint(
            "quantity > 0",
            name="positive_quantity",
        ),
        {
            "schema": "shopping_carts",
        },
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    shopping_cart_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="main",
    )

    product_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )

    product_image_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )