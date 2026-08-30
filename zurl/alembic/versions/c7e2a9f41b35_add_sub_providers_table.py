"""add sub providers table

Revision ID: c7e2a9f41b35
Revises: 94b0cb3b951f
Create Date: 2025-08-30 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e2a9f41b35'
down_revision: Union[str, Sequence[str], None] = '94b0cb3b951f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('zurl_sub_providers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('url', sa.String(length=2048), nullable=True),
    sa.Column('created_at', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('zurl_sub_providers', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_zurl_sub_providers_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_zurl_sub_providers_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_zurl_sub_providers_url'), ['url'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('zurl_sub_providers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_zurl_sub_providers_url'))
        batch_op.drop_index(batch_op.f('ix_zurl_sub_providers_name'))
        batch_op.drop_index(batch_op.f('ix_zurl_sub_providers_id'))

    op.drop_table('zurl_sub_providers')
