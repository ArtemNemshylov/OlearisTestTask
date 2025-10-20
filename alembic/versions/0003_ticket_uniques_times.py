from alembic import op
import sqlalchemy as sa


revision = "0003_ticket_uniques_times"
down_revision = "0002_ticket_viewed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("in_progress_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("done_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("requester_ip", sa.String(length=64), nullable=True))
    op.add_column("tickets", sa.Column("requester_ua", sa.String(length=256), nullable=True))
    op.create_unique_constraint("uq_ticket_client_content", "tickets", ["title", "description", "client_id"])


def downgrade() -> None:
    op.drop_constraint("uq_ticket_client_content", "tickets", type_="unique")
    op.drop_column("tickets", "requester_ua")
    op.drop_column("tickets", "requester_ip")
    op.drop_column("tickets", "done_at")
    op.drop_column("tickets", "in_progress_at")
    op.drop_column("tickets", "assigned_at")


