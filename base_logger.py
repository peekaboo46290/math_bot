from pydantic import BaseModel
from typing import Any
class BaseLogger(BaseModel):
    info: Any = print
