"""billing rules and integrity

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31 12:47:47.397264
"""
from alembic import op
import sqlalchemy as sa
import app.core.types


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

CHECKS = [
    ('ck_products_sales_price', 'products', 'sales_price >= 0'),
    ('ck_products_cost_price', 'products', 'cost_price >= 0'),
    ('ck_users_email_lowercase', 'users', 'email = lower(email)'),
    ('ck_plans_available_dates', 'plans', 'available_to >= available_from'),
    ('ck_plans_price', 'plans', 'price >= 0'),
    ('ck_plans_min_quantity', 'plans', 'min_quantity >= 1'),
    ('ck_templates_validity_days', 'quotation_templates', 'validity_days >= 1'),
    ('ck_tax_rules_target', 'tax_rules', "(applies_to <> 'product' OR product_id IS NOT NULL) AND (applies_to <> 'plan' OR plan_id IS NOT NULL)"),
    ('ck_tax_rules_rate', 'tax_rules', 'rate >= 0 AND rate <= 1'),
    ('ck_subscriptions_payment_terms', 'subscriptions', 'payment_terms >= 0'),
    ('ck_subscriptions_dates', 'subscriptions', 'expiry_date >= start_date'),
    ('ck_discounts_max_uses', 'discounts', 'max_uses >= 1'),
    ('ck_discounts_value', 'discounts', 'value > 0'),
    ('ck_discounts_min_quantity', 'discounts', 'min_quantity >= 1'),
    ('ck_discounts_percentage', 'discounts', "type <> 'percentage' OR value <= 100"),
    ('ck_discounts_used_count', 'discounts', 'used_count >= 0'),
    ('ck_discounts_dates', 'discounts', 'end_date >= start_date'),
    ('ck_discounts_min_purchase', 'discounts', 'min_purchase >= 0'),
    ('ck_invoices_amount_paid', 'invoices', 'amount_paid >= 0'),
    ('ck_invoices_discount_total', 'invoices', 'discount_total >= 0'),
    ('ck_invoices_tax_total', 'invoices', 'tax_total >= 0'),
    ('ck_invoices_period', 'invoices', 'period_end >= period_start'),
    ('ck_invoices_grand_total', 'invoices', 'grand_total >= 0'),
    ('ck_invoices_subtotal', 'invoices', 'subtotal >= 0'),
    ('ck_subscription_lines_quantity', 'subscription_lines', 'quantity >= 1'),
    ('ck_subscription_lines_unit_price', 'subscription_lines', 'unit_price >= 0'),
    ('ck_subscription_lines_tax', 'subscription_lines', 'tax_amount >= 0'),
    ('ck_invoice_lines_unit_price', 'invoice_lines', 'unit_price >= 0'),
    ('ck_invoice_lines_quantity', 'invoice_lines', 'quantity >= 1'),
    ('ck_invoice_lines_total', 'invoice_lines', 'line_total >= 0'),
    ('ck_payments_amount', 'payments', 'amount > 0'),
]

DEFAULTS = [
    ('products', 'sales_price', '0'),
    ('products', 'is_active', 'true'),
    ('users', 'is_active', 'true'),
    ('plans', 'min_quantity', '1'),
    ('plans', 'auto_close', 'false'),
    ('plans', 'can_pause', 'true'),
    ('plans', 'can_close_early', 'true'),
    ('plans', 'can_renew', 'true'),
    ('plans', 'is_active', 'true'),
    ('product_variants', 'price_delta', '0'),
    ('product_variants', 'is_active', 'true'),
    ('quotation_templates', 'validity_days', '30'),
    ('quotation_templates', 'payment_terms', '15'),
    ('tax_rules', 'is_active', 'true'),
    ('subscriptions', 'payment_terms', '15'),
    ('discounts', 'used_count', '0'),
    ('discounts', 'is_active', 'true'),
    ('invoices', 'amount_paid', '0'),
    ('subscription_lines', 'quantity', '1'),
    ('subscription_lines', 'tax_amount', '0'),
]


def upgrade() -> None:
    # Existing rows first, so the new constraints below hold for them
    op.execute("UPDATE users SET email = lower(email)")

    op.create_table('number_sequences',
    sa.Column('prefix', sa.String(length=30), nullable=False),
    sa.Column('last_value', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('prefix')
    )
    op.create_table('quotation_template_lines',
    sa.Column('id', app.core.types.GUID(), nullable=False),
    sa.Column('template_id', app.core.types.GUID(), nullable=False),
    sa.Column('product_id', app.core.types.GUID(), nullable=False),
    sa.Column('variant_id', app.core.types.GUID(), nullable=True),
    sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.CheckConstraint('quantity >= 1', name='ck_template_lines_quantity'),
    sa.CheckConstraint('unit_price >= 0', name='ck_template_lines_unit_price'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['template_id'], ['quotation_templates.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quotation_template_lines_product_id'), 'quotation_template_lines', ['product_id'], unique=False)
    op.create_index(op.f('ix_quotation_template_lines_template_id'), 'quotation_template_lines', ['template_id'], unique=False)
    op.create_index(op.f('ix_quotation_template_lines_variant_id'), 'quotation_template_lines', ['variant_id'], unique=False)
    op.create_table('discount_redemptions',
    sa.Column('id', app.core.types.GUID(), nullable=False),
    sa.Column('discount_id', app.core.types.GUID(), nullable=False),
    sa.Column('invoice_id', app.core.types.GUID(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.CheckConstraint('amount >= 0', name='ck_redemptions_amount'),
    sa.ForeignKeyConstraint(['discount_id'], ['discounts.id'], ),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('discount_id', 'invoice_id', name='uq_redemptions_discount_invoice')
    )
    op.create_index(op.f('ix_discount_redemptions_discount_id'), 'discount_redemptions', ['discount_id'], unique=False)
    op.create_index(op.f('ix_discount_redemptions_invoice_id'), 'discount_redemptions', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_discount_products_product_id'), 'discount_products', ['product_id'], unique=False)
    op.add_column('discounts', sa.Column('customer_id', app.core.types.GUID(), nullable=True))
    op.add_column('discounts', sa.Column('subscription_id', app.core.types.GUID(), nullable=True))
    op.create_index(op.f('ix_discounts_customer_id'), 'discounts', ['customer_id'], unique=False)
    op.create_index(op.f('ix_discounts_subscription_id'), 'discounts', ['subscription_id'], unique=False)
    op.create_foreign_key(None, 'discounts', 'subscriptions', ['subscription_id'], ['id'])
    op.create_foreign_key(None, 'discounts', 'users', ['customer_id'], ['id'])
    op.create_index(op.f('ix_invoice_lines_product_id'), 'invoice_lines', ['product_id'], unique=False)
    op.add_column('invoices', sa.Column('period_start', sa.Date(), nullable=True))
    op.add_column('invoices', sa.Column('period_end', sa.Date(), nullable=True))
    op.add_column('invoices', sa.Column('customer_name', sa.String(length=255), nullable=True))
    op.add_column('invoices', sa.Column('customer_email', sa.String(length=255), nullable=True))
    op.add_column('invoices', sa.Column('amount_paid', sa.Numeric(precision=12, scale=2), server_default='0', nullable=False))
    op.add_column('invoices', sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('invoices', sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_invoices_created_at', 'invoices', ['created_at'], unique=False)
    op.create_index('ix_invoices_status_due_date', 'invoices', ['status', 'due_date'], unique=False)
    op.create_index('uq_invoices_subscription_period', 'invoices', ['subscription_id', 'period_start'], unique=True, postgresql_where=sa.text("status <> 'cancelled'"), sqlite_where=sa.text("status <> 'cancelled'"))
    op.create_index('ix_payments_created_at', 'payments', ['created_at'], unique=False)
    op.create_index('ix_payments_payment_date', 'payments', ['payment_date'], unique=False)
    op.create_index(op.f('ix_payments_recorded_by'), 'payments', ['recorded_by'], unique=False)
    op.add_column('quotation_templates', sa.Column('payment_terms', sa.Integer(), server_default='15', nullable=False))
    op.add_column('subscription_lines', sa.Column('variant_id', app.core.types.GUID(), nullable=True))
    op.create_index(op.f('ix_subscription_lines_product_id'), 'subscription_lines', ['product_id'], unique=False)
    op.create_index(op.f('ix_subscription_lines_variant_id'), 'subscription_lines', ['variant_id'], unique=False)
    op.create_foreign_key(None, 'subscription_lines', 'product_variants', ['variant_id'], ['id'])
    op.create_index(op.f('ix_subscription_status_history_changed_by'), 'subscription_status_history', ['changed_by'], unique=False)
    op.add_column('subscriptions', sa.Column('quotation_valid_until', sa.Date(), nullable=True))
    op.create_index('ix_subscriptions_created_at', 'subscriptions', ['created_at'], unique=False)
    op.create_index(op.f('ix_subscriptions_created_by'), 'subscriptions', ['created_by'], unique=False)
    op.create_index('ix_subscriptions_status_next_billing', 'subscriptions', ['status', 'next_billing_date'], unique=False)
    op.create_index(op.f('ix_subscriptions_template_id'), 'subscriptions', ['template_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_variant_id'), 'subscriptions', ['variant_id'], unique=False)
    op.add_column('tax_rules', sa.Column('plan_id', app.core.types.GUID(), nullable=True))
    op.create_index(op.f('ix_tax_rules_plan_id'), 'tax_rules', ['plan_id'], unique=False)
    op.create_foreign_key(None, 'tax_rules', 'plans', ['plan_id'], ['id'])
    op.add_column('users', sa.Column('company_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('address', sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE invoices i
        SET customer_name = u.full_name,
            customer_email = u.email,
            amount_paid = COALESCE(
                (SELECT sum(p.amount) FROM payments p WHERE p.invoice_id = i.id), 0
            )
        FROM users u
        WHERE u.id = i.customer_id
        """
    )
    # Continue each month's numbering from the highest number already issued
    for table, column in (("invoices", "invoice_number"), ("subscriptions", "subscription_number")):
        op.execute(
            f"""
            INSERT INTO number_sequences (prefix, last_value)
            SELECT substring({column} from '^[A-Z]+-[0-9]{{6}}-'),
                   max(substring({column} from '[0-9]+$')::int)
            FROM {table}
            WHERE {column} ~ '^[A-Z]+-[0-9]{{6}}-[0-9]+$'
            GROUP BY 1
            """
        )

    for table, column, default in DEFAULTS:
        op.alter_column(table, column, server_default=sa.text(f"'{default}'"))
    for name, table, condition in CHECKS:
        op.create_check_constraint(name, table, condition)


def downgrade() -> None:
    for name, table, _ in CHECKS:
        op.drop_constraint(name, table, type_="check")
    for table, column, _ in DEFAULTS:
        op.alter_column(table, column, server_default=None)
    op.drop_column('users', 'address')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'company_name')
    op.drop_constraint('tax_rules_plan_id_fkey', 'tax_rules', type_='foreignkey')
    op.drop_index(op.f('ix_tax_rules_plan_id'), table_name='tax_rules')
    op.drop_column('tax_rules', 'plan_id')
    op.drop_index(op.f('ix_subscriptions_variant_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_template_id'), table_name='subscriptions')
    op.drop_index('ix_subscriptions_status_next_billing', table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_created_by'), table_name='subscriptions')
    op.drop_index('ix_subscriptions_created_at', table_name='subscriptions')
    op.drop_column('subscriptions', 'quotation_valid_until')
    op.drop_index(op.f('ix_subscription_status_history_changed_by'), table_name='subscription_status_history')
    op.drop_constraint('subscription_lines_variant_id_fkey', 'subscription_lines', type_='foreignkey')
    op.drop_index(op.f('ix_subscription_lines_variant_id'), table_name='subscription_lines')
    op.drop_index(op.f('ix_subscription_lines_product_id'), table_name='subscription_lines')
    op.drop_column('subscription_lines', 'variant_id')
    op.drop_column('quotation_templates', 'payment_terms')
    op.drop_index(op.f('ix_payments_recorded_by'), table_name='payments')
    op.drop_index('ix_payments_payment_date', table_name='payments')
    op.drop_index('ix_payments_created_at', table_name='payments')
    op.drop_index('uq_invoices_subscription_period', table_name='invoices', postgresql_where=sa.text("status <> 'cancelled'"), sqlite_where=sa.text("status <> 'cancelled'"))
    op.drop_index('ix_invoices_status_due_date', table_name='invoices')
    op.drop_index('ix_invoices_created_at', table_name='invoices')
    op.drop_column('invoices', 'paid_at')
    op.drop_column('invoices', 'sent_at')
    op.drop_column('invoices', 'amount_paid')
    op.drop_column('invoices', 'customer_email')
    op.drop_column('invoices', 'customer_name')
    op.drop_column('invoices', 'period_end')
    op.drop_column('invoices', 'period_start')
    op.drop_index(op.f('ix_invoice_lines_product_id'), table_name='invoice_lines')
    op.drop_constraint('discounts_subscription_id_fkey', 'discounts', type_='foreignkey')
    op.drop_constraint('discounts_customer_id_fkey', 'discounts', type_='foreignkey')
    op.drop_index(op.f('ix_discounts_subscription_id'), table_name='discounts')
    op.drop_index(op.f('ix_discounts_customer_id'), table_name='discounts')
    op.drop_column('discounts', 'subscription_id')
    op.drop_column('discounts', 'customer_id')
    op.drop_index(op.f('ix_discount_products_product_id'), table_name='discount_products')
    op.drop_index(op.f('ix_discount_redemptions_invoice_id'), table_name='discount_redemptions')
    op.drop_index(op.f('ix_discount_redemptions_discount_id'), table_name='discount_redemptions')
    op.drop_table('discount_redemptions')
    op.drop_index(op.f('ix_quotation_template_lines_variant_id'), table_name='quotation_template_lines')
    op.drop_index(op.f('ix_quotation_template_lines_template_id'), table_name='quotation_template_lines')
    op.drop_index(op.f('ix_quotation_template_lines_product_id'), table_name='quotation_template_lines')
    op.drop_table('quotation_template_lines')
    op.drop_table('number_sequences')
