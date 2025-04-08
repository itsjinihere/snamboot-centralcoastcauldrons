"""Create carts and cart_items tables

Revision ID: 4a9b04a56823
Revises: 53da3aa57fac
Create Date: 2025-04-08 00:30:09.608075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a9b04a56823'
down_revision: Union[str, None] = '53da3aa57fac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "carts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("customer_name", sa.String, nullable=False),
        sa.Column("payment", sa.String, nullable=True),
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cart_id", sa.Integer, sa.ForeignKey("carts.id"), nullable=False),
        sa.Column("sku", sa.String, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price", sa.Integer, nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("cart_items")
    op.drop_table("carts")