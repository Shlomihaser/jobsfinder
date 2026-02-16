from abc import ABC, abstractmethod
from typing import Optional
from app.models.company import Company
from app.schemas.company import CompanyUpdate

class BaseEnricher(ABC):
    """
    Interface for company data enrichment strategies.
    Each implementation handles a specific ATS provider or enrichment source.
    """
    
    @abstractmethod
    async def enrich(self, company: Company) -> Optional[CompanyUpdate]:
        """
        Attempts to enrich the company with missing data (URL, config, etc.).
        Returns CompanyUpdate object with new data if successful, None otherwise.
        """
        pass
