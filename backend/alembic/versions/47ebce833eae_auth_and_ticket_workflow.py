"""auth and ticket workflow

Revision ID: 47ebce833eae
Revises: 44273a775ed8
Create Date: 2026-11-21 16:36:17.194057

Adds secure authentication columns, the controlled ticket lifecycle columns,
status/assignment history, an audit trail, and the supporting constraints.
No existing table or volume is recreated; existing rows are preserved.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '47ebce833eae'
down_revision: Union[str, None] = '44273a775ed8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_STATUSES = "'new', 'assigned', 'in_progress', 'waiting_for_student', 'resolved', 'closed'"
OLD_STATUSES = "'open', 'in_progress', 'resolved', 'closed'"


def upgrade() -> None:
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('actor_role', sa.String(length=50), nullable=True),
    sa.Column('action', sa.String(length=80), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.String(length=50), nullable=False),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.Column('is_override', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_logs_actor_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor_id'), 'audit_logs', ['actor_id'], unique=False)
    op.create_index('ix_audit_logs_created', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)

    op.create_table('ticket_assignment_history',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.Column('from_assignee_id', sa.Integer(), nullable=True),
    sa.Column('to_assignee_id', sa.Integer(), nullable=True),
    sa.Column('changed_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], name=op.f('fk_ticket_assignment_history_changed_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['from_assignee_id'], ['users.id'], name=op.f('fk_ticket_assignment_history_from_assignee_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], name=op.f('fk_ticket_assignment_history_ticket_id_tickets'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['to_assignee_id'], ['users.id'], name=op.f('fk_ticket_assignment_history_to_assignee_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ticket_assignment_history'))
    )
    op.create_index(op.f('ix_ticket_assignment_history_changed_by_id'), 'ticket_assignment_history', ['changed_by_id'], unique=False)
    op.create_index(op.f('ix_ticket_assignment_history_created_at'), 'ticket_assignment_history', ['created_at'], unique=False)
    op.create_index(op.f('ix_ticket_assignment_history_ticket_id'), 'ticket_assignment_history', ['ticket_id'], unique=False)

    op.create_table('ticket_status_history',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.Column('from_status', sa.String(length=30), nullable=True),
    sa.Column('to_status', sa.String(length=30), nullable=False),
    sa.Column('changed_by_id', sa.Integer(), nullable=True),
    sa.Column('note', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], name=op.f('fk_ticket_status_history_changed_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], name=op.f('fk_ticket_status_history_ticket_id_tickets'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ticket_status_history'))
    )
    op.create_index(op.f('ix_ticket_status_history_changed_by_id'), 'ticket_status_history', ['changed_by_id'], unique=False)
    op.create_index(op.f('ix_ticket_status_history_created_at'), 'ticket_status_history', ['created_at'], unique=False)
    op.create_index(op.f('ix_ticket_status_history_ticket_id'), 'ticket_status_history', ['ticket_id'], unique=False)

    # Ticket workflow columns. Existing 'open' tickets (if any) become 'new'.
    op.add_column('tickets', sa.Column('is_escalated', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_index('ix_tickets_escalated_status', 'tickets', ['is_escalated', 'status'], unique=False)
    op.execute("UPDATE tickets SET status = 'new' WHERE status = 'open'")
    op.alter_column('tickets', 'status', server_default='new', existing_type=sa.String(length=30))
    op.drop_constraint(op.f('ck_tickets_status_valid'), 'tickets', type_='check')
    op.create_check_constraint('status_valid', 'tickets', f"status IN ({NEW_STATUSES})")

    # Password hashes: pre-existing rows get an unusable sentinel, then NOT NULL.
    # '!' is not a valid Argon2 PHC string, so it can never authenticate anyone.
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.execute("UPDATE users SET password_hash = '!' WHERE password_hash IS NULL")
    op.alter_column('users', 'password_hash', nullable=False, existing_type=sa.String(length=255))
    op.alter_column('users', 'is_active', server_default=sa.text('true'), existing_type=sa.Boolean())
    op.create_check_constraint('role_valid', 'users', "role IN ('student', 'staff', 'hod', 'admin')")


def downgrade() -> None:
    op.drop_constraint(op.f('ck_users_role_valid'), 'users', type_='check')
    op.alter_column('users', 'is_active', server_default=None, existing_type=sa.Boolean())
    op.drop_column('users', 'password_hash')

    op.drop_constraint(op.f('ck_tickets_status_valid'), 'tickets', type_='check')
    op.create_check_constraint('status_valid', 'tickets', f"status IN ({OLD_STATUSES})")
    op.execute("UPDATE tickets SET status = 'open' WHERE status IN ('new', 'assigned', 'waiting_for_student')")
    op.alter_column('tickets', 'status', server_default='open', existing_type=sa.String(length=30))
    op.drop_index('ix_tickets_escalated_status', table_name='tickets')
    op.drop_column('tickets', 'is_escalated')

    op.drop_index(op.f('ix_ticket_status_history_ticket_id'), table_name='ticket_status_history')
    op.drop_index(op.f('ix_ticket_status_history_created_at'), table_name='ticket_status_history')
    op.drop_index(op.f('ix_ticket_status_history_changed_by_id'), table_name='ticket_status_history')
    op.drop_table('ticket_status_history')

    op.drop_index(op.f('ix_ticket_assignment_history_ticket_id'), table_name='ticket_assignment_history')
    op.drop_index(op.f('ix_ticket_assignment_history_created_at'), table_name='ticket_assignment_history')
    op.drop_index(op.f('ix_ticket_assignment_history_changed_by_id'), table_name='ticket_assignment_history')
    op.drop_table('ticket_assignment_history')

    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created', table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
