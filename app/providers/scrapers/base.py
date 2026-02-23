from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.schemas.job import JobSchema

class BaseScraper(ABC):

    def __init__(self, company_name: str, config: Dict[str, Any]):
        self.company_name = company_name
        self.config = config

    @classmethod
    @abstractmethod
    async def is_valid_config(cls, config: Dict[str, Any]) -> bool: 
        pass

    @abstractmethod
    async def fetch_jobs(self) -> List[JobSchema]: 
        pass
