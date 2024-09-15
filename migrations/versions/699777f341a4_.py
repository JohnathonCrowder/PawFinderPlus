"""empty message

Revision ID: 699777f341a4
Revises: 0b5e1bf51f80
Create Date: 2024-09-14 19:55:17.433366

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '699777f341a4'
down_revision = '0b5e1bf51f80'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('website', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('facebook', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('instagram', sa.String(length=200), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('instagram')
        batch_op.drop_column('facebook')
        batch_op.drop_column('website')

    # ### end Alembic commands ###
