from typing import Dict, Type, Optional
from app.models.company import ATSProvider
from app.providers.enrichers.base import BaseEnricher
from app.providers.enrichers.comeet_enricher import ComeetEnricher

class EnricherFactory:
    """
    Factory to retrieve the appropriate Enricher strategy based on ATS Provider.
    """
    _registry: Dict[ATSProvider, Type[BaseEnricher]] = {
        ATSProvider.COMEET: ComeetEnricher,
    }
    
    @classmethod
    def get_enricher(cls, provider: ATSProvider) -> Optional[BaseEnricher]:
        enricher_cls = cls._registry.get(provider)
        if not enricher_cls:
            return None
        return enricher_cls()
