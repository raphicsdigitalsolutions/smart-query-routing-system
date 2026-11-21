"""Phase 7 platform capabilities

Revision ID: feedf21773e1
Revises: b7d4e91c2a83
Create Date: 2026-11-21 22:00:00.000000

Additive migration for BYOK credentials, governed knowledge, notifications,
announcements, instructor leave, OAuth links, attachments, agent telemetry,
and ticket channel/SLA metadata. No existing table is recreated and no row is
deleted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'feedf21773e1'
down_revision: Union[str, None] = 'b7d4e91c2a83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    ]


def upgrade() -> None:
    # --- ticket metadata: intake channel, SLA timing and resolution summary ---
    op.add_column('tickets', sa.Column('channel', sa.String(length=20), server_default='web', nullable=False))
    op.add_column('tickets', sa.Column('auto_routed', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('tickets', sa.Column('escalated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tickets', sa.Column('first_response_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tickets', sa.Column('resolution_summary', sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f('ck_tickets_channel_valid'),
        'tickets',
        "channel IN ('web', 'email', 'whatsapp')",
    )
    op.create_index('ix_tickets_channel_created', 'tickets', ['channel', 'created_at'], unique=False)

    # --- BYOK encrypted credentials ---
    op.create_table(
        'user_api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=30), server_default='openai', nullable=False),
        sa.Column('encrypted_key', sa.String(length=512), nullable=False),
        sa.Column('key_hint', sa.String(length=20), nullable=False),
        sa.Column('is_valid', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_api_keys_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_api_keys')),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_api_keys_user_provider'),
    )
    op.create_index(op.f('ix_user_api_keys_user_id'), 'user_api_keys', ['user_id'], unique=False)
    op.create_index('ix_user_api_keys_user_provider', 'user_api_keys', ['user_id', 'provider'], unique=True)

    # --- Google OAuth identity links ---
    op.create_table(
        'user_oauth_accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=30), server_default='google', nullable=False),
        sa.Column('provider_subject', sa.String(length=255), nullable=False),
        sa.Column('provider_email', sa.String(length=255), nullable=True),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_oauth_accounts_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_oauth_accounts')),
        sa.UniqueConstraint('provider', 'provider_subject', name='uq_user_oauth_provider_subject'),
    )
    op.create_index('ix_user_oauth_accounts_user', 'user_oauth_accounts', ['user_id'], unique=False)

    # --- governed knowledge base ---
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('source_key', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=120), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=False),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_approved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "source_type IN ('text', 'txt', 'md', 'pdf')",
            name=op.f('ck_knowledge_documents_knowledge_source_type_valid'),
        ),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], name=op.f('fk_knowledge_documents_approved_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_knowledge_documents_department_id_departments'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], name=op.f('fk_knowledge_documents_uploaded_by_id_users'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_knowledge_documents')),
        sa.UniqueConstraint('source_key', 'version', name='uq_knowledge_documents_source_version'),
    )
    op.create_index(op.f('ix_knowledge_documents_source_key'), 'knowledge_documents', ['source_key'], unique=False)
    op.create_index(op.f('ix_knowledge_documents_uploaded_by_id'), 'knowledge_documents', ['uploaded_by_id'], unique=False)
    op.create_index('ix_knowledge_documents_department', 'knowledge_documents', ['department_id'], unique=False)
    op.create_index('ix_knowledge_documents_approval', 'knowledge_documents', ['is_approved', 'is_active'], unique=False)

    # --- notification delivery/outbox ---
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=True),
        sa.Column('recipient_user_id', sa.Integer(), nullable=True),
        sa.Column('recipient_address', sa.String(length=255), nullable=True),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('event_type', sa.String(length=60), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('provider_id', sa.String(length=120), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_internal', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "channel IN ('in_app', 'email', 'whatsapp')",
            name=op.f('ck_notifications_notification_channel_valid'),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name=op.f('ck_notifications_notification_status_valid'),
        ),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], name=op.f('fk_notifications_recipient_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], name=op.f('fk_notifications_ticket_id_tickets'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
    )
    op.create_index(op.f('ix_notifications_recipient_user_id'), 'notifications', ['recipient_user_id'], unique=False)
    op.create_index('ix_notifications_recipient_created', 'notifications', ['recipient_user_id', 'created_at'], unique=False)
    op.create_index('ix_notifications_ticket_event', 'notifications', ['ticket_id', 'event_type'], unique=False)

    # --- announcements ---
    op.create_table(
        'announcements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('audience_roles_json', sa.JSON(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_announcements_created_by_id_users'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_announcements_department_id_departments'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_announcements')),
    )
    op.create_index(op.f('ix_announcements_department_id'), 'announcements', ['department_id'], unique=False)
    op.create_index('ix_announcements_published', 'announcements', ['is_active', 'published_at'], unique=False)

    # --- instructor leave / auto-reply ---
    op.create_table(
        'instructor_leaves',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('auto_reply', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint('end_at > start_at', name=op.f('ck_instructor_leaves_instructor_leave_window_valid')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_instructor_leaves_created_by_id_users'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_instructor_leaves_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_instructor_leaves')),
    )
    op.create_index(op.f('ix_instructor_leaves_user_id'), 'instructor_leaves', ['user_id'], unique=False)
    op.create_index('ix_instructor_leaves_user_active', 'instructor_leaves', ['user_id', 'is_active'], unique=False)

    # --- message attachments (metadata only) ---
    op.create_table(
        'message_attachments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], name=op.f('fk_message_attachments_message_id_messages'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_message_attachments')),
    )
    op.create_index('ix_message_attachments_message', 'message_attachments', ['message_id'], unique=False)

    # --- bounded agent run telemetry ---
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('requested_by_id', sa.Integer(), nullable=True),
        sa.Column('analysis_id', sa.Integer(), nullable=True),
        sa.Column('workflow', sa.String(length=80), nullable=False),
        sa.Column('model', sa.String(length=80), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('tool_io_json', sa.JSON(), nullable=True),
        sa.Column('permission_outcome', sa.String(length=40), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('completed', 'failed', 'abstained')",
            name=op.f('ck_agent_runs_agent_run_status_valid'),
        ),
        sa.ForeignKeyConstraint(['analysis_id'], ['ticket_ai_analyses.id'], name=op.f('fk_agent_runs_analysis_id_ticket_ai_analyses'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], name=op.f('fk_agent_runs_requested_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], name=op.f('fk_agent_runs_ticket_id_tickets'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_runs')),
    )
    op.create_index('ix_agent_runs_ticket_created', 'agent_runs', ['ticket_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_agent_runs_ticket_created', table_name='agent_runs')
    op.drop_table('agent_runs')
    op.drop_index('ix_message_attachments_message', table_name='message_attachments')
    op.drop_table('message_attachments')
    op.drop_index('ix_instructor_leaves_user_active', table_name='instructor_leaves')
    op.drop_index(op.f('ix_instructor_leaves_user_id'), table_name='instructor_leaves')
    op.drop_table('instructor_leaves')
    op.drop_index('ix_announcements_published', table_name='announcements')
    op.drop_index(op.f('ix_announcements_department_id'), table_name='announcements')
    op.drop_table('announcements')
    op.drop_index('ix_notifications_ticket_event', table_name='notifications')
    op.drop_index('ix_notifications_recipient_created', table_name='notifications')
    op.drop_index(op.f('ix_notifications_recipient_user_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_knowledge_documents_approval', table_name='knowledge_documents')
    op.drop_index('ix_knowledge_documents_department', table_name='knowledge_documents')
    op.drop_index(op.f('ix_knowledge_documents_uploaded_by_id'), table_name='knowledge_documents')
    op.drop_index(op.f('ix_knowledge_documents_source_key'), table_name='knowledge_documents')
    op.drop_table('knowledge_documents')
    op.drop_index('ix_user_oauth_accounts_user', table_name='user_oauth_accounts')
    op.drop_table('user_oauth_accounts')
    op.drop_index('ix_user_api_keys_user_provider', table_name='user_api_keys')
    op.drop_index(op.f('ix_user_api_keys_user_id'), table_name='user_api_keys')
    op.drop_table('user_api_keys')
    op.drop_index('ix_tickets_channel_created', table_name='tickets')
    op.drop_constraint(op.f('ck_tickets_channel_valid'), 'tickets', type_='check')
    op.drop_column('tickets', 'resolution_summary')
    op.drop_column('tickets', 'first_response_at')
    op.drop_column('tickets', 'escalated_at')
    op.drop_column('tickets', 'auto_routed')
    op.drop_column('tickets', 'channel')
