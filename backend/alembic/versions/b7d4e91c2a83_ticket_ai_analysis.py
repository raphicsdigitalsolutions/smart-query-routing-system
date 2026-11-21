"""ticket AI analysis and approval state

Revision ID: b7d4e91c2a83
Revises: 47ebce833eae
Create Date: 2026-11-21 20:15:00.000000

Adds one Phase 6 table for bounded agent output, draft validation and idempotent
human approval. No existing table, row, volume or database is recreated.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7d4e91c2a83'
down_revision: Union[str, None] = '47ebce833eae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ticket_ai_analyses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('requested_by_id', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='completed'),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('classification_json', sa.JSON(), nullable=True),
        sa.Column('priority_recommendation', sa.String(length=20), nullable=True),
        sa.Column('department_recommendation_json', sa.JSON(), nullable=True),
        sa.Column('staff_recommendation_json', sa.JSON(), nullable=True),
        sa.Column('knowledge_sources_json', sa.JSON(), nullable=True),
        sa.Column('draft_json', sa.JSON(), nullable=True),
        sa.Column('validation_json', sa.JSON(), nullable=True),
        sa.Column('no_evidence', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('abstention_reason', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_metadata_json', sa.JSON(), nullable=True),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_message_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('completed', 'failed')", name=op.f('ck_ticket_ai_analyses_ai_status_valid')),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], name=op.f('fk_ticket_ai_analyses_approved_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_message_id'], ['messages.id'], name=op.f('fk_ticket_ai_analyses_approved_message_id_messages'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], name=op.f('fk_ticket_ai_analyses_requested_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], name=op.f('fk_ticket_ai_analyses_ticket_id_tickets'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ticket_ai_analyses')),
        sa.UniqueConstraint('ticket_id', 'version', name='uq_ticket_ai_analyses_ticket_id_version'),
    )
    op.create_index(op.f('ix_ticket_ai_analyses_requested_by_id'), 'ticket_ai_analyses', ['requested_by_id'], unique=False)
    op.create_index(op.f('ix_ticket_ai_analyses_ticket_id'), 'ticket_ai_analyses', ['ticket_id'], unique=False)
    op.create_index('ix_ticket_ai_analyses_created_at', 'ticket_ai_analyses', ['created_at'], unique=False)
    op.create_index('ix_ticket_ai_analyses_ticket_current', 'ticket_ai_analyses', ['ticket_id', 'is_current'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ticket_ai_analyses_ticket_current', table_name='ticket_ai_analyses')
    op.drop_index('ix_ticket_ai_analyses_created_at', table_name='ticket_ai_analyses')
    op.drop_index(op.f('ix_ticket_ai_analyses_ticket_id'), table_name='ticket_ai_analyses')
    op.drop_index(op.f('ix_ticket_ai_analyses_requested_by_id'), table_name='ticket_ai_analyses')
    op.drop_table('ticket_ai_analyses')
