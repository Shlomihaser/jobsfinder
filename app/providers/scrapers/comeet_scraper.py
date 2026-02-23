import httpx
from typing import Dict, Any, List, Optional
from loguru import logger

from app.schemas.job import JobSchema
from app.providers.scrapers.base import BaseScraper

from app.core.exceptions import RetryableProviderError, FatalProviderError, ProviderError

class ComeetScraper(BaseScraper):
    BASE_URL = "https://www.comeet.co/careers-api/2.0/company"

    def __init__(self, company_name: str, config: Dict[str, Any]):
        super().__init__(company_name, config)
        self.uid = config.get("uid")
        self.token = config.get("token")

    @classmethod
    async def is_valid_config(cls, config: Dict[str, Any]) -> bool:
        uid = config.get("uid")
        token = config.get("token")
        
        if not uid or not token: return False
            
        url = f"{cls.BASE_URL}/{uid}/positions"
        params = {
            "token": token,
            "details": "false",
            "limit": 1
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status() 
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [403, 404]:
                logger.warning(f"Comeet Validation Failed: {e.response.status_code} - Invalid Config")
                return False
            
            logger.error(f"Comeet API Error during validation: {e}")
            raise RetryableProviderError(f"API Error during validation: {e}", provider="Comeet")
            
        except httpx.RequestError as e:
            logger.error(f"Network error during Comeet validation: {e}")
            raise RetryableProviderError(f"Network error validating config: {e}", provider="Comeet")
            
        except Exception as e:
            logger.error(f"Unexpected error during Comeet validation: {e}")
            raise ProviderError(f"Unexpected validation error: {e}", provider="Comeet")


    async def fetch_jobs(self) -> List[JobSchema]:
        """
        Fetches all jobs from Comeet API in a single request.
        """
        if not self.uid or not self.token:
            logger.error(f"Missing uid or token for company {self.company_name}")
            return []

        url = f"{self.BASE_URL}/{self.uid}/positions"
        params = { "token": self.token, "details": "true" }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                jobs_data = resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [404, 403]:
                    logger.error(f"Fatal error for {self.company_name}: {e}")
                    raise FatalProviderError(f"Company not found or access denied: {e}", provider="Comeet")
                if e.response.status_code == 429 or e.response.status_code >= 500:
                    logger.warning(f"Temporary error for {self.company_name}: {e}")
                    raise RetryableProviderError(f"Service unavailable: {e}", provider="Comeet")
                raise ProviderError(f"HTTP {e.response.status_code}: {e}", provider="Comeet")
            except httpx.RequestError as e:
                logger.error(f"Connection failed for {self.company_name}: {e}")
                raise RetryableProviderError(f"Connection failed: {e}", provider="Comeet")
            except Exception as e:
                logger.error(f"Unexpected error for {self.company_name}: {e}")
                raise ProviderError(f"Unexpected error: {e}", provider="Comeet")

        return self._parse_jobs(jobs_data)

    def _parse_jobs(self, jobs: List[Dict[str, Any]]) -> List[JobSchema]:
        parsed_jobs = []
        for job in jobs:
            try:
                description_html = self._parse_details(job.get("details", []))

                schema = JobSchema(
                    title=job.get("name"),
                    external_id=job.get("uid"),
                    url=job.get("url_active_page"),
                    location=job.get("location", {}).get("country"),
                    city=job.get("location", {}).get("city"),
                    description=description_html,
                    published_at=job.get("time_updated"),
                    raw_data=job
                )
                parsed_jobs.append(schema)
            except Exception as e:
                logger.warning(f"Skipping malformed job {job.get('uid')}: {e}")

        logger.info(f"Successfully parsed {len(parsed_jobs)} jobs for {self.company_name}")
        return parsed_jobs

    def _parse_details(self, details: List[Dict[str, Any]]) -> Optional[str]:
        """
        Concatenates all detail sections (Description, Requirements, etc.)
        Job.details is a list: [{'name': 'Description', 'value': 'HTML', 'order': 1}, ...]
        """
        if not details: return 
    
        sorted_details = sorted(details, key=lambda x: x.get("order", 0))
        
        parts = []
        for item in sorted_details:
            section_name = item.get("name", "")
            content = item.get("value", "")
            if content:
                parts.append(f"<h4>{section_name}</h4>{content}")
        
        return "<br><br>".join(parts) if parts else None