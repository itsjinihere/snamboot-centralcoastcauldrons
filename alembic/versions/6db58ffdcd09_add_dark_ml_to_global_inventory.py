"""Add dark_ml to global_inventory

Revision ID: 6db58ffdcd09
Revises: 4a9b04a56823
Create Date: 2025-04-08 01:09:37.241309

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6db58ffdcd09"
down_revision: Union[str, None] = "4a9b04a56823"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dark_ml column to global_inventory."""
    op.add_column(
        "global_inventory",
        sa.Column("dark_ml", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Remove dark_ml column from global_inventory."""
    op.drop_column("global_inventory", "dark_ml")
