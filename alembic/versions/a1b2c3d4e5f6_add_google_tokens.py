"""Add google_tokens table

Revision ID: a1b2c3d4e5f6
Revises: 4864af9dfa48
Create Date: 2026-03-18 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4864af9dfa48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'google_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_email', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_uri', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('client_secret', sa.String(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_email'),
    )
    op.create_index(op.f('ix_google_tokens_id'), 'google_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_google_tokens_employee_email'), 'google_tokens', ['employee_email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_google_tokens_employee_email'), table_name='google_tokens')
    op.drop_index(op.f('ix_google_tokens_id'), table_name='google_tokens')
    op.drop_table('google_tokens')
