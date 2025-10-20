from alembic import op
import sqlalchemy as sa


revision = "0002_ticket_viewed"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("viewed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_tickets_viewed", "tickets", ["viewed"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tickets_viewed", table_name="tickets")
    op.drop_column("tickets", "viewed")


