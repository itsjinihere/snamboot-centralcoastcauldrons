from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from src.database import Base
from datetime import datetime

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
    customer_id = Column(Integer, primary_key=True)  # Changed 'id' to 'customer_id'
    customer_name = Column(String, nullable=False)
    payment = Column(String, nullable=True)
    character_class = Column(String, nullable=False)  # Added character_class column
    level = Column(Integer, nullable=False)  # Added level column


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.customer_id"), nullable=False)  # Updated to 'customer_id'
    item_sku = Column(String, nullable=False)  # Changed from 'sku' to 'item_sku'
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)  # Added timestamp column
