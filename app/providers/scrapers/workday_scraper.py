import httpx
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger
from urllib.parse import urlparse, parse_qs

from app.schemas.job import JobSchema
from app.providers.scrapers.base import BaseScraper
from app.core.exceptions import RetryableProviderError, FatalProviderError, ProviderError

class WorkdayScraper(BaseScraper):
    
    def __init__(self, company_name: str, config: Dict[str, Any]):
        super().__init__(company_name, config)
        self.careers_url = config.get("careers_url")

    @classmethod
    async def is_valid_config(cls, config: Dict[str, Any]) -> bool:
        url = config.get("careers_url")
        if not url: return False
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                resp.raise_for_status() 
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [403, 404]:
                logger.warning(f"Workday Validation Failed: {e.response.status_code} - Invalid Config")
                return False
            
            logger.error(f"Workday API Error during validation: {e}")
            raise RetryableProviderError(f"API Error during validation: {e}", provider="Workday")
            
        except httpx.RequestError as e:
            logger.error(f"Network error during Workday validation: {e}")
            raise RetryableProviderError(f"Network error validating config: {e}", provider="Workday")
            
        except Exception as e:
            logger.error(f"Unexpected error during Workday validation: {e}")
            raise ProviderError(f"Unexpected validation error: {e}", provider="Workday")
        
        return True

    async def fetch_jobs(self) -> List[JobSchema]:
        if not self.careers_url:
            logger.error(f"Missing careers_url for company {self.company_name}")
            return []

        url_parts = urlparse(self.careers_url)

        host = url_parts.netloc # acme.myworkdayjobs.com
        tenant = host.split(".")[0] # acme
        path_parts = url_parts.path.strip("/").split("/")[1:] # acme_careers        
        site_id = path_parts[0]
        api_url = f"https://{host}/wday/cxs/{tenant}/{site_id}/jobs"
        params = parse_qs(url_parts.query)
        logger.debug(f"FOUND Workday API Base: {api_url}")

        all_jobs = []
        offset = 0

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json,application/xml",
            "Origin": "https://myworkdayjobs.com",
            "Referer": self.careers_url
        }
        
 
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            try:
                await client.get(self.careers_url)
                
                while True:
                   
                    payload = {
                        "appliedFacets": params,
                        "limit": 20, # only 20 is allowed , other is bad request
                        "offset": offset,
                        "searchText": ""
                    }
                    
                    logger.debug(f"[{self.company_name}] Fetching offset {offset}...")
                    
                    resp = await client.post(api_url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    current_total = data.get("total")
                    if offset == 0:
                        total = current_total or 0
                    
                    job_postings = data.get("jobPostings")
                    if not job_postings:
                        logger.info(f"[{self.company_name}] No more jobs found at offset {offset}.")
                        break
                    
                    if offset == 0:
                        logger.info(f"[{self.company_name}] Discovered {total} total jobs. Starting to fetch details...")
                    
                    logger.debug(f"[{self.company_name}] Response: Found {len(job_postings)} jobs at offset {offset}.")
                    semaphore = asyncio.Semaphore(20)
                    
                    async def fetch_job_detail(job_summary):
                        title = job_summary.get("title")
                        external_path = job_summary.get("externalPath")
                        
                        if not external_path:
                            logger.warning(f"Job {title} has no externalPath, skipping details.")
                            return None

                        detail_api_url = f"{api_url.removesuffix('/jobs')}{external_path}"
                        
                        try:
                            async with semaphore:
                                detail_resp = await client.get(detail_api_url)
                                
                            if detail_resp.status_code == 200:
                                detail_data = detail_resp.json()
                                job_posting_info = detail_data.get("jobPostingInfo", {})
                                
                                description = job_posting_info.get("jobDescription")
                                external_url = job_posting_info.get("externalUrl") 
                                
                                if not external_url:
                                     external_url = f"https://{host}/en-US/{site_id}{external_path}"
                                
                                return JobSchema(
                                    title=title,
                                    external_id=job_posting_info.get("jobReqId") or job_posting_info.get("id"),
                                    url=external_url,
                                    location=job_summary.get("locationsText"), 
                                    city=None,
                                    description=description, 
                                    published_at=None, 
                                    raw_data=job_posting_info
                                )
                            else:
                                logger.warning(f"Failed to fetch details for {title}: {detail_resp.status_code}")
                                return
                                
                        except Exception as e:
                            logger.warning(f"Skipping malformed Workday job '{title}': {e}")
                            return 

                    tasks = [fetch_job_detail(js) for js in job_postings]
                    page_results = await asyncio.gather(*tasks)
                    
                    valid_jobs = [j for j in page_results if j is not None]
                    all_jobs.extend(valid_jobs)

                    offset += 20
                    
                    if offset >= total:
                        logger.info(f"[{self.company_name}] Reached end of pagination (Offset {offset} >= Total {total}).")
                        break
                        
                    await asyncio.sleep(1)
                    
            except httpx.HTTPStatusError as e:
                 if e.response.status_code == 403:
                     logger.warning(f"Access denied (403) for {self.company_name}.")
                     raise FatalProviderError("Blocked by WAF/Cloudflare", provider="Workday")
                 raise RetryableProviderError(f"HTTP Error: {e}", provider="Workday")
            except Exception as e:
                logger.error(f"Unexpected error scraping Workday: {e}")
                raise ProviderError(f"Unexpected: {e}", provider="Workday")

        logger.info(f"Successfully parsed {len(all_jobs)} jobs for {self.company_name}")
        return all_jobs
