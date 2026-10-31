import uuid
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.types import GUID


class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"
    __table_args__ = (CheckConstraint("validity_days >= 1", name="ck_templates_validity_days"),)

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=False, index=True)
    validity_days = Column(Integer, default=30, server_default="30", nullable=False)
    payment_terms = Column(Integer, default=15, server_default="15", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plan = relationship("Plan")
    lines = relationship(
        "QuotationTemplateLine", back_populates="template", cascade="all, delete-orphan"
    )


class QuotationTemplateLine(Base):
    __tablename__ = "quotation_template_lines"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_template_lines_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_template_lines_unit_price"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    template_id = Column(
        GUID(), ForeignKey("quotation_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = Column(GUID(), ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(GUID(), ForeignKey("product_variants.id"), nullable=True, index=True)
    quantity = Column(Integer, default=1, server_default="1", nullable=False)
    # NULL means "use the catalogue price when the quote is created"
    unit_price = Column(Numeric(12, 2), nullable=True)

    template = relationship("QuotationTemplate", back_populates="lines")
    product = relationship("Product")
    variant = relationship("ProductVariant")

