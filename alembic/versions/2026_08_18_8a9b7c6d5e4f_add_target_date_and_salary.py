"""add target_date and salary fields

Revision ID: 8a9b7c6d5e4f
Revises: 0bb2c2fbdd79
Create Date: 2026-08-18 21:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a9b7c6d5e4f'
down_revision: Union[str, None] = '0bb2c2fbdd79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('saving_goals', sa.Column('target_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('monthly_salary', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('users', sa.Column('pay_cycle_days', sa.Integer(), server_default='30', nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'pay_cycle_days')
    op.drop_column('users', 'monthly_salary')
    op.drop_column('saving_goals', 'target_date')
