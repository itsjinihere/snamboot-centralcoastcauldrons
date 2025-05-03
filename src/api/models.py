from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from src.database import Base
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

# ---- LEDGER ENTRIES ----
class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource = Column(String, nullable=False)  # e.g., 'gold', 'red_ml', 'blue_potion'
    change = Column(Integer, nullable=False)
    context = Column(String, nullable=True)  # e.g., 'Purchased barrel', 'Checkout'
    timestamp = Column(DateTime, default=datetime.utcnow)


# ---- EXECUTED ORDERS ----
class ExecutedOrder(Base):
    __tablename__ = "executed_orders"
    order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)


# ---- CART & CART ITEMS ----
class Cart(Base):
    __tablename__ = "carts"
    customer_id = Column(Integer, primary_key=True)
    customer_name = Column(String, nullable=False)
    payment = Column(String, nullable=True)
    character_class = Column(String, nullable=False)
    level = Column(Integer, nullable=False)


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey("carts.customer_id"), nullable=False)
    item_sku = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


# ---- OPTIONAL (if you still use catalog-backed types) ----
class PotionType(Base):
    __tablename__ = "potion_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    red = Column(Integer, nullable=False)
    green = Column(Integer, nullable=False)
    blue = Column(Integer, nullable=False)
    dark = Column(Integer, nullable=False)


# ---- REMOVE IF DEPRECATED ----
# class GlobalInventory(Base):
#     __tablename__ = "global_inventory"
#     id = Column(Integer, primary_key=True)
#     gold = Column(Integer, nullable=False)
#     red_ml = Column(Integer, nullable=False, default=0)
#     green_ml = Column(Integer, nullable=False, default=0)
#     blue_ml = Column(Integer, nullable=False, default=0)
#     red_potions = Column(Integer, nullable=False, default=0)
#     green_potions = Column(Integer, nullable=False, default=0)
#     blue_potions = Column(Integer, nullable=False, default=0)
