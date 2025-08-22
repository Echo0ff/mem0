"""create history table

Revision ID: 001
Revises: 
Create Date: 2025-08-22 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create history table
    op.create_table(
        'history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('memory_id', sa.String(), nullable=True),
        sa.Column('old_memory', sa.Text(), nullable=True),
        sa.Column('new_memory', sa.Text(), nullable=True),
        sa.Column('event', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Integer(), nullable=True),
        sa.Column('actor_id', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_history_id'), 'history', ['id'], unique=False)
    op.create_index(op.f('ix_history_memory_id'), 'history', ['memory_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_history_memory_id'), table_name='history')
    op.drop_index(op.f('ix_history_id'), table_name='history')
    op.drop_table('history')