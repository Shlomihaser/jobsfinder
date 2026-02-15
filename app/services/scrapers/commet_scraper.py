import httpx
from typing import Dict, Any, List, Optional
from loguru import logger

from app.schemas.job import JobSchema
from app.services.scrapers.base import BaseScraper

from app.core.exceptions import RetryableProviderError, FatalProviderError, ProviderError

class ComeetScraper(BaseScraper):
    BASE_URL = "https://www.comeet.co/careers-api/2.0/company"

    def __init__(self, company_name: str, config: Dict[str, Any]):
        super().__init__(company_name, config)
        self.uid = config.get("uid")
        self.token = config.get("token")

    async def fetch_jobs(self) -> List[JobSchema]:
        """
        Fetches all jobs from Comeet API in a single request.
        """
        if not self.uid or not self.token:
            logger.error(f"Missing uid or token for company {self.company_name}")
            return []

        url = f"{self.BASE_URL}/{self.uid}/positions?token={self.token}&details=true"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url)
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

    def _parse_jobs(self, jobs_list: List[Dict[str, Any]]) -> List[JobSchema]:
        valid_jobs = []
        for job_data in jobs_list:
            try:
                description_html = self._parse_details(job_data.get("details", []))

                schema = JobSchema(
                    title=job_data.get("name"),
                    external_id=job_data.get("uid"),
                    url=job_data.get("url_active_page"),
                    location=job_data.get("location", {}).get("country"),
                    description=description_html,
                    published_at=job_data.get("time_updated"),
                    raw_data=job_data
                )
                valid_jobs.append(schema)
            except Exception as e:
                logger.warning(f"Skipping malformed job {job_data.get('uid')}: {e}")

        logger.info(f"Successfully parsed {len(valid_jobs)} jobs for {self.company_name}")
        return valid_jobs

    def _parse_details(self, details: List[Dict[str, Any]]) -> Optional[str]:
        """
        Concatenates all detail sections (Description, Requirements, etc.)
        Job.details is a list: [{'name': 'Description', 'value': 'HTML', 'order': 1}, ...]
        """
        if not details:
            return None
    
        sorted_details = sorted(details, key=lambda x: x.get("order", 0))
        
        parts = []
        for item in sorted_details:
            section_name = item.get("name", "")
            content = item.get("value", "")
            if content:
                parts.append(f"<h4>{section_name}</h4>{content}")
        
        return "<br><br>".join(parts) if parts else None