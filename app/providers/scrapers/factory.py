from typing import Type, Dict, Any
from app.models.company import ATSProvider, Company
from app.providers.scrapers.base import BaseScraper
from app.providers.scrapers.comeet_scraper import ComeetScraper
from app.providers.scrapers.workday_scraper import WorkdayScraper
from app.providers.scrapers.workable_scraper import WorkableScraper
from app.core.exceptions import FatalProviderError

class ScraperFactory:
    _registry = {
        ATSProvider.COMEET: ComeetScraper,
        ATSProvider.WORKDAY: WorkdayScraper,
        ATSProvider.WORKABLE: WorkableScraper,
    }

    @classmethod
    def get_scraper(cls, company: Company) -> BaseScraper:
        """
        Returns an instance of the appropriate Scraper for the company.
        """
        if not company.ats_provider:
             raise FatalProviderError(f"Company {company.name} has no ATS Provider configured.")

        scraper_cls = cls._registry.get(company.ats_provider)
        if not scraper_cls:
            raise FatalProviderError(f"No scraper implemented for ATS: {company.ats_provider}")

        return scraper_cls(company.name, company.metadata_config)

    @classmethod
    async def validate_provider_config(cls, ats_provider: ATSProvider, config: Dict[str, Any]) -> bool:
        scraper_cls = cls._registry.get(ats_provider)
        if not scraper_cls:
            return False
        return await scraper_cls.is_valid_config(config)
