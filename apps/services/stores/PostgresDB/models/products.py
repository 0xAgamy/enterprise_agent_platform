
from sqlalchemy import (
    Integer,
    String,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
class Product(Base):

    __tablename__ = "product"
    __table_args__ = (
         {
                    "schema": "product",
        },
     )
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_asin: Mapped[str] = mapped_column(
            String(255),
            nullable=False,
        )

    description:Mapped[str]= mapped_column(
        String,
        nullable=False
    )
    rating_number:Mapped[int]= mapped_column(
        Integer,
        nullable=True
    )

    image: Mapped[str]= mapped_column(
            String(255),
            nullable=True
        )
    average_rating:Mapped[float]= mapped_column(
        Float(2),
            nullable=True

    )

    price:Mapped[float]= mapped_column(
        Float,
        nullable=True

    )
