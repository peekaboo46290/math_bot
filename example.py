from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo

from base_logger import BaseLogger

class Example(BaseModel):
    logger: BaseLogger = Field(default= BaseLogger(), description="Too log information")

    name: str = Field(..., description="Title or identifier of the example")
    content: str = Field(..., description="The actual example with solution")
    subject: str = Field(..., description="Mathematical subject")
    domain: str = Field(..., description="Specific domain")
    illustrates_theorems: List[str] = Field(default_factory=list, description="Theorems this example illustrates")
    difficulty: str = Field(default="Medium", description="Easy, Medium, or Hard")#for indexing

    @field_validator('name', 'content', 'subject', 'domain')
    @classmethod
    def not_empty(cls, v:str):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()
    
    @field_validator('difficulty')
    @classmethod
    def valid_difficulty(cls, v:str, info: ValidationInfo):
        valid_levels = ['Easy', 'Medium', 'Hard']
        if info.data and v not in valid_levels:
            info.data['logger'].warning(f"Invalid difficulty '{v}', defaulting to 'Medium'")
            return 'Medium'
        return v
