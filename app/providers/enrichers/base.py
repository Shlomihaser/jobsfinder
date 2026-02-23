from abc import ABC, abstractmethod
from typing import Optional
from app.models.company import Company
from app.schemas.company import CompanyUpdate

class BaseEnricher(ABC):
    @abstractmethod
    async def enrich(self, company: Company) -> Optional[CompanyUpdate]:
        pass
