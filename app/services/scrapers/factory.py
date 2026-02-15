from typing import Type
from app.models.company import ATSProvider, Company
from app.services.scrapers.base import BaseScraper
from app.services.scrapers.commet_scraper import ComeetScraper
from app.core.exceptions import FatalProviderError

class ScraperFactory:
    _registry = {
        ATSProvider.COMEET: ComeetScraper,
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
