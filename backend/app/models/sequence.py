from sqlalchemy import Column, Integer, String
from app.core.database import Base


class NumberSequence(Base):
    """Last number issued per prefix, e.g. INV-202611-. Updated atomically."""
    __tablename__ = "number_sequences"

    prefix = Column(String(30), primary_key=True)
    last_value = Column(Integer, nullable=False)
