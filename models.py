from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional


class EnvelopeType(str, Enum):
    EXPENSE = "Expense"
    GOAL = "Goal"


class Envelope(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    category_type: EnvelopeType
    target: float = Field(default=0.0)
    monthly_target: float = Field(default=0.0)  # NEW FIELD
    allocated: float = Field(default=0.0)
    position: int = Field(default=0)
    
    transactions: list["Transaction"] = Relationship(back_populates="envelope")


class Transaction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    amount: float
    envelope_id: int | None = Field(default=None, foreign_key="envelope.id")
    note: str = ""
    # THIS LINE CHANGED to include timezone.utc
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    is_allocation: bool = Field(default=False)
    allocation_data: str = Field(default="{}") 
    
    envelope: Optional["Envelope"] = Relationship(back_populates="transactions")