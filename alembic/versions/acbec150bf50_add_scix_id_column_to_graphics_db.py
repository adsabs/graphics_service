"""Add scix_id column to graphics db

Revision ID: acbec150bf50
Revises: de7cb4b6482f
Create Date: 2025-08-26 14:07:37.099701

"""
from alembic import op
from sqlalchemy import Column, String, Integer, TIMESTAMP, DateTime, Text, Index, Boolean

# revision identifiers, used by Alembic.
revision = 'acbec150bf50'
down_revision = 'de7cb4b6482f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('graphics', Column('scix_id', String(19), nullable = True, default=None, unique=True))


def downgrade():
    op.drop_column('graphics', 'scix_id')
