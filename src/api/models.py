from sqlalchemy import Column, Integer, String, ForeignKey
from src.database import Base


class GlobalInventory(Base):
    __tablename__ = "global_inventory"
    id = Column(Integer, primary_key=True)
    gold = Column(Integer, nullable=False)
    red_ml = Column(Integer, nullable=False, default=0)
    green_ml = Column(Integer, nullable=False, default=0)
    blue_ml = Column(Integer, nullable=False, default=0)
    red_potions = Column(Integer, nullable=False, default=0)
    green_potions = Column(Integer, nullable=False, default=0)
    blue_potions = Column(Integer, nullable=False, default=0)


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True)
    customer_name = Column(String, nullable=False)
    payment = Column(String, nullable=True)


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
