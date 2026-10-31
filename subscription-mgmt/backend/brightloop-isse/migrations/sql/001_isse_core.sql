-- ===== ISSE core tables =====================================================

CREATE TABLE IF NOT EXISTS risk_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    request_id      UUID NOT NULL,
    account_id      UUID,
    subscription_id UUID,
    decision        VARCHAR(16) NOT NULL,     -- ALLOW / CHALLENGE / REVIEW / BLOCK
    layer           VARCHAR(16) NOT NULL,     -- RULE / AI / ORCHESTRATOR
    rule_id         VARCHAR(64),
    ai_model        VARCHAR(64),
    ai_score        NUMERIC(6,5),
    reason          TEXT NOT NULL,
    context         JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_risk_audit_account ON risk_audit_log(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS device_fingerprints (
    id              BIGSERIAL PRIMARY KEY,
    fingerprint     VARCHAR(128) NOT NULL,
    account_id      UUID,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(fingerprint, account_id)
);

CREATE TABLE IF NOT EXISTS trial_usage (
    id                  BIGSERIAL PRIMARY KEY,
    device_fingerprint  VARCHAR(128),
    card_fingerprint    VARCHAR(128),
    email_domain        VARCHAR(255),
    account_id          UUID NOT NULL,
    consumed            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_trial_device ON trial_usage(device_fingerprint);
CREATE INDEX IF NOT EXISTS idx_trial_card ON trial_usage(card_fingerprint);

CREATE TABLE IF NOT EXISTS card_fingerprints (
    id                  BIGSERIAL PRIMARY KEY,
    card_fingerprint    VARCHAR(128) NOT NULL,
    account_id          UUID,
    device_fingerprint  VARCHAR(128),
    ip_address          INET,
    outcome             VARCHAR(16),  -- success / declined / chargeback
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_card_fp_window ON card_fingerprints(card_fingerprint, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_card_fp_device ON card_fingerprints(device_fingerprint, created_at DESC);

CREATE TABLE IF NOT EXISTS disposable_email_domains (
    domain VARCHAR(255) PRIMARY KEY
);

-- ===== $0 invoice / price-tamper guard ======================================

CREATE OR REPLACE FUNCTION guard_invoice_amount()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.total_amount = 0 THEN
        IF NOT EXISTS (
            SELECT 1 FROM plans p
            WHERE p.id = NEW.plan_id AND p.base_price = 0
        ) AND NEW.discount_id IS NULL THEN
            RAISE EXCEPTION
              'ISSE_BLOCK: invoice % rejected - $0 total without zero-price plan or approved discount',
              NEW.id;
        END IF;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_guard_invoice_amount ON invoices;
CREATE TRIGGER trg_guard_invoice_amount
BEFORE INSERT OR UPDATE ON invoices
FOR EACH ROW EXECUTE FUNCTION guard_invoice_amount();

-- ===== idempotency guard against duplicate invoice generation ===============
CREATE UNIQUE INDEX IF NOT EXISTS uq_invoice_period
ON invoices(subscription_id, billing_period_start)
WHERE status <> 'void';