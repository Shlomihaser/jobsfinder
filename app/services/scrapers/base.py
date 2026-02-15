
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from app.schemas.job import JobSchema

class BaseScraper(ABC):

    def __init__(self, company_name: str,config: Dict[str, Any]):
        self.company_name = company_name
        self.config = config

    @abstractmethod
    async def fetch_jobs(self) -> List[JobSchema]:
        pass
