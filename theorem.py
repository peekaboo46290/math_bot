from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo

from base_logger import BaseLogger


class Theorem(BaseModel):
    logger: BaseLogger = Field(default= BaseLogger(), description="Too log information")

    name: str = Field(..., description="Name or title of the theorem")
    statement: str = Field(..., description="Formal statement of the theorem")
    proof: Optional[str] = Field(default="Not provided", description="Proof of the theorem")
    subject: str = Field(..., description="Mathematical subject (e.g., Algebra, Analysis)")
    domain: str = Field(..., description="Specific domain (e.g., Linear Algebra)")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies on other theorems")
    type: str = Field(default= "Theorem", description="Theorem, Lemma, Proposition, or Corollary")


    @field_validator('name', 'statement', 'subject', 'domain')
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()
    
    @field_validator('type')
    @classmethod
    def valid_type(cls, v:str, info: ValidationInfo):
        valid_types = ['theorem', 'lemma', 'proposition', 'corollary', 'conjecture', 'definition', "property", "hypothesis"]
        if info.data and  v.lower() not in valid_types:
            info.data['logger'].warning(f"Invalid type '{v}', defaulting to 'Theorem'")
            return 'Theorem'
        return v
