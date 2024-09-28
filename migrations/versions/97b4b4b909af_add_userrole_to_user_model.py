"""Add UserRole to User model

Revision ID: 97b4b4b909af
Revises: 5c9984e61d79
Create Date: 2023-06-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '97b4b4b909af'
down_revision = '5c9984e61d79'
branch_labels = None
depends_on = None

def upgrade():
    # Add the new column as nullable first
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.Enum('BUYER', 'SELLER', name='userrole'), nullable=True))

    # Update existing rows to have a default value
    op.execute("UPDATE user SET role = 'BUYER' WHERE role IS NULL")

    # Now make the column non-nullable
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('role', nullable=False)

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('role')