"""initial

Revision ID: be288a524be3
Revises:
Create Date: 2025-04-09 10:34:09.369498
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "be288a524be3"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing tables
    op.create_table(
        "carts",
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(), nullable=False),
        sa.Column("payment", sa.String(), nullable=True),
        sa.Column("character_class", sa.String(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("customer_id"),
    )
    op.create_table(
        "global_inventory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gold", sa.Integer(), nullable=False),
        sa.Column("red_ml", sa.Integer(), nullable=False),
        sa.Column("green_ml", sa.Integer(), nullable=False),
        sa.Column("blue_ml", sa.Integer(), nullable=False),
        sa.Column("red_potions", sa.Integer(), nullable=False),
        sa.Column("green_potions", sa.Integer(), nullable=False),
        sa.Column("blue_potions", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("item_sku", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.customer_id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # NEW: bottling_logs table
    op.create_table(
        "bottling_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("red_ml_used", sa.Integer(), nullable=False, default=0),
        sa.Column("green_ml_used", sa.Integer(), nullable=False, default=0),
        sa.Column("blue_ml_used", sa.Integer(), nullable=False, default=0),
        sa.Column("dark_ml_used", sa.Integer(), nullable=False, default=0),
        sa.Column("red_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("green_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("blue_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("dark_qty", sa.Integer(), nullable=False, default=0),
    )

    # NEW: checkout_logs table
    op.create_table(
        "checkout_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("gold_spent", sa.Integer(), nullable=False),
        sa.Column("red_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("green_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("blue_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("dark_qty", sa.Integer(), nullable=False, default=0),
        sa.Column("catalog_variety", sa.Integer(), nullable=False),
    )

    # NEW: catalog_snapshots table
    op.create_table(
        "catalog_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column("red_available", sa.Boolean(), nullable=True),
        sa.Column("green_available", sa.Boolean(), nullable=True),
        sa.Column("blue_available", sa.Boolean(), nullable=True),
        sa.Column("dark_available", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("catalog_snapshots")
    op.drop_table("checkout_logs")
    op.drop_table("bottling_logs")
    op.drop_table("cart_items")
    op.drop_table("global_inventory")
    op.drop_table("carts")
