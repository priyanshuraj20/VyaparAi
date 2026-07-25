"""Initial Schema Creation for VyaparAI

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-07-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Customers table
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('alias_notes', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('whatsapp_opted_in', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('opted_in_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_customers_name', 'customers', ['name'])
    op.create_index('ix_customers_phone', 'customers', ['phone'])

    # Transactions table (enums created automatically on first table reference)
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', postgresql.ENUM('credit_given', 'payment_received', name='transaction_type'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('item_description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('pending_confirmation', 'confirmed', 'rejected', 'undone', name='transaction_status'), nullable=False, server_default='confirmed'),
        sa.Column('source', postgresql.ENUM('text', 'voice', 'ocr', name='transaction_source'), nullable=False, server_default='text'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('raw_input', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_transactions_customer_id', 'transactions', ['customer_id'])
    op.create_index('ix_transactions_status', 'transactions', ['status'])
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])
    op.create_index('idx_transactions_customer_status', 'transactions', ['customer_id', 'status'])

    # Reminders table
    op.create_table(
        'reminders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount_at_time', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('proposed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('approved_by_owner', sa.Boolean(), nullable=True),
        sa.Column('channel_used', postgresql.ENUM('conversational', 'template', 'owner_only', name='reminder_channel'), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_reminders_customer_id', 'reminders', ['customer_id'])

    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_message_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('direction', postgresql.ENUM('inbound', 'outbound', name='message_direction'), nullable=False),
        sa.Column('type', postgresql.ENUM('text', 'voice', 'image', name='message_type'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('media_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])

    # OCR Documents table
    op.create_table(
        'ocr_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('extracted_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('reviewed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_ocr_documents_message_id', 'ocr_documents', ['message_id'])


def downgrade() -> None:
    op.drop_table('ocr_documents')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('reminders')
    op.drop_table('transactions')
    op.drop_table('customers')

    op.execute('DROP TYPE IF EXISTS message_type')
    op.execute('DROP TYPE IF EXISTS message_direction')
    op.execute('DROP TYPE IF EXISTS reminder_channel')
    op.execute('DROP TYPE IF EXISTS transaction_source')
    op.execute('DROP TYPE IF EXISTS transaction_status')
    op.execute('DROP TYPE IF EXISTS transaction_type')
