from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel

class JobSchema(BaseModel):
    title: str
    external_id: str
    url: str
    location: str | None = None
    published_at: datetime | None = None
    description: str | None = None
    raw_data: Dict[str, Any]