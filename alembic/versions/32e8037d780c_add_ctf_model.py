"""Add ctf model.

Revision ID: 32e8037d780c
Revises: b372d25359fd
Create Date: 2023-03-29 00:47:57.194052

"""
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op
from src.database.utils.password import Password

# revision identifiers, used by Alembic.
revision = "32e8037d780c"
down_revision = "b372d25359fd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "ctf",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", mysql.VARCHAR(length=255), nullable=False),
        sa.Column("guild_id", mysql.BIGINT(display_width=18), nullable=False),
        sa.Column("admin_role_id", mysql.BIGINT(display_width=18), nullable=False),
        sa.Column("participant_role_id", mysql.BIGINT(display_width=18), nullable=False),
        sa.Column("password", Password, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ctf_id"), "ctf", ["id"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_ctf_id"), table_name="ctf")
    op.drop_table("ctf")
    # ### end Alembic commands ###