import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Numeric, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID, INET

from app.core.database import Base


class RiskAuditLog(Base):
    __tablename__ = "risk_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), nullable=False)
    account_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    subscription_id = Column(UUID(as_uuid=True), nullable=True)
    decision = Column(String(16), nullable=False)
    layer = Column(String(16), nullable=False)
    rule_id = Column(String(64), nullable=True)
    ai_model = Column(String(64), nullable=True)
    ai_score = Column(Numeric(6, 5), nullable=True)
    reason = Column(Text, nullable=False)
    context = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DeviceFingerprint(Base):
    __tablename__ = "device_fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint = Column(String(128), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class TrialUsage(Base):
    __tablename__ = "trial_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_fingerprint = Column(String(128), index=True)
    card_fingerprint = Column(String(128), index=True)
    email_domain = Column(String(255))
    account_id = Column(UUID(as_uuid=True), nullable=False)
    consumed = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class CardFingerprintEvent(Base):
    __tablename__ = "card_fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_fingerprint = Column(String(128), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), nullable=True)
    device_fingerprint = Column(String(128), index=True)
    ip_address = Column(INET, nullable=True)
    outcome = Column(String(16))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)