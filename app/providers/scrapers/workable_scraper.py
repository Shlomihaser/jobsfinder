import httpx
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger
from urllib.parse import urlparse

from app.schemas.job import JobSchema
from app.providers.scrapers.base import BaseScraper
from app.core.exceptions import RetryableProviderError, FatalProviderError, ProviderError

class WorkableScraper(BaseScraper):

    def __init__(self, company_name: str, config: Dict[str, Any]):
        super().__init__(company_name, config)
        self.slug = config.get("name")

    @classmethod
    async def is_valid_config(cls, config: Dict[str, Any]) -> bool:
        slug = config.get("name")
        if not slug: 
            return False
            
        try:

            api_url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
            payload = {"location": [{"country": "Israel", "countryCode": "IL"}]}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(api_url, json=payload)
                resp.raise_for_status() 
                data = resp.json()
                if "results" in data:
                    return True
                return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [403, 404]:
                logger.warning(f"Workable Validation Failed: {e.response.status_code} - Invalid Config")
                return False
            
            logger.error(f"Workable API Error during validation: {e}")
            raise RetryableProviderError(f"API Error during validation: {e}", provider="Workable")
            
        except httpx.RequestError as e:
            logger.error(f"Network error during Workable validation: {e}")
            raise RetryableProviderError(f"Network error validating config: {e}", provider="Workable")
            
        except Exception as e:
            logger.error(f"Unexpected error during Workable validation: {e}")
            raise ProviderError(f"Unexpected validation error: {e}", provider="Workable")
        
        return False

    async def fetch_jobs(self) -> List[JobSchema]:
        slug = self.slug
        
        if not slug:
            logger.error(f"Missing name for company {self.company_name}")
            return []

        list_api_url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
        base_detail_url = f"https://apply.workable.com/api/v2/accounts/{slug}/jobs/"

        all_jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://apply.workable.com"
        }
        payload = {"location": [{"country": "Israel", "countryCode": "IL"}]}

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            try:
                logger.debug(f"[{self.company_name}] Fetching jobs list for Workable slug '{slug}'...")
                resp = await client.post(list_api_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                job_results = data.get("results", [])
                total = data.get("total", len(job_results))
                
                if not job_results:
                    logger.info(f"[{self.company_name}] No jobs found for Workable.")
                    return []
                
                logger.info(f"[{self.company_name}] Discovered {total} total jobs in search. Processing details...")
                
                semaphore = asyncio.Semaphore(5)
                
                async def fetch_job_detail(job_summary):
                    shortcode = job_summary.get("shortcode")
                    title = job_summary.get("title")
                    
                    if not shortcode:
                        logger.warning(f"Job {title} has no shortcode, skipping details.")
                        return None
                        
                    detail_url = f"{base_detail_url}{shortcode}"
                    
                    try:
                        async with semaphore:
                            detail_resp = await client.get(detail_url)
                            
                        if detail_resp.status_code == 200:
                            detail_data = detail_resp.json()
                            
                            description_html = detail_data.get("description", "")
                            requirements_html = detail_data.get("requirements", "")
                            benefits_html = detail_data.get("benefits", "")
                            
                            
                            full_description = ""
                            if description_html:
                                full_description += f"<h4>Description</h4>{description_html}"
                            if requirements_html:
                                full_description += f"<h4>Requirements</h4>{requirements_html}"
                            if benefits_html:
                                full_description += f"<h4>Benefits</h4>{benefits_html}"
                                
                            location_data = detail_data.get("location", {})
                            city = location_data.get("city")
                            country = location_data.get("country")

                            external_url = f"https://apply.workable.com/{slug}/j/{shortcode}/"
                            
                            return JobSchema(
                                title=detail_data.get("title", title),
                                external_id=str(detail_data.get("id")) if detail_data.get("id") else shortcode,
                                url=external_url,
                                location=country,
                                city=city,
                                description=full_description,
                                published_at=detail_data.get("published"),
                                raw_data=detail_data
                            )
                        else:
                            logger.warning(f"Failed to fetch details for {title}: {detail_resp.status_code}")
                            return None
                            
                    except Exception as e:
                        logger.warning(f"Skipping malformed Workable job '{title}': {e}")
                        return None

                tasks = [fetch_job_detail(js) for js in job_results]
                page_results = await asyncio.gather(*tasks)
                
                valid_jobs = [j for j in page_results if j is not None]
                all_jobs.extend(valid_jobs)

            except httpx.HTTPStatusError as e:
                 if e.response.status_code == 403:
                     logger.warning(f"Access denied (403) for {self.company_name}.")
                     raise FatalProviderError("Blocked by WAF/Cloudflare", provider="Workable")
                 raise RetryableProviderError(f"HTTP Error: {e}", provider="Workable")
            except Exception as e:
                logger.error(f"Unexpected error scraping Workable: {e}")
                raise ProviderError(f"Unexpected: {e}", provider="Workable")

        logger.info(f"Successfully parsed {len(all_jobs)} jobs for {self.company_name}")
        return all_jobs
