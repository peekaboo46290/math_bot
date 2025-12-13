from typing import List, Optional
from pydantic import BaseModel, Field


class Theorem(BaseModel):
    name: str = Field(..., description="Name or title of the theorem")
    statement: str = Field(..., description="Formal statement of the theorem")
    proof: Optional[str] = Field(default="Not provided", description="Proof of the theorem")
    subject: str = Field(..., description="Mathematical subject (e.g., Algebra, Analysis)")
    domain: str = Field(..., description="Specific domain (e.g., Linear Algebra)")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies on other theorems")
    type: str = Field(default= "Theorem", description="Theorem, Lemma, Proposition, or Corollary")
    
    class Config:
        populate_by_name = True
