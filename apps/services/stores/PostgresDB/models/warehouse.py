from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Computed,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    __table_args__ = (
        CheckConstraint(
            "total_quantity >= 0",
            name="positive_total_quantity",
        ),
        CheckConstraint(
            "reserved_quantity >= 0",
            name="positive_reserved_quantity",
        ),
        CheckConstraint(
            "reserved_quantity <= total_quantity",
            name="valid_reservation",
        ),

        UniqueConstraint(
            "warehouse_id",
            "product_id",
            name="unique_warehouse_product",
        ),

        Index(
            "idx_inventory_product",
            "product_id",
        ),

        {
            "schema": "warehouses",
        },
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    warehouse_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    product_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    total_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    reserved_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    available_quantity: Mapped[int] = mapped_column(
        Integer,
        Computed(
            "total_quantity - reserved_quantity",
            persisted=True,
        ),
        nullable=False,
    )

    warehouse_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    warehouse_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    estimated_processing_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )