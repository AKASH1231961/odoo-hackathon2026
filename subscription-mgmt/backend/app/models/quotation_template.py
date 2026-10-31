import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.types import GUID


class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=False, index=True)
    validity_days = Column(Integer, default=30, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plan = relationship("Plan")

