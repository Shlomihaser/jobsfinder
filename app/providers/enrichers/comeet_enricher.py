from app.providers.enrichers.base import BaseEnricher
from app.models.company import Company
from app.schemas.company import CompanyUpdate
from app.core.exceptions import EnrichmentRateLimitError
from app.providers.scrapers.comeet_scraper import ComeetScraper
import re
import asyncio
import httpx
from typing import Optional, Dict, Any, NamedTuple
from ddgs import DDGS
from loguru import logger

class ComeetSourceData(NamedTuple):
    uid: str
    token: str
    career_url: str
    logo_url: Optional[str]

class ComeetEnricher(BaseEnricher):
    CAREERS_BASE = "https://www.comeet.com/jobs"

    RE_COMPANY_UID = r"comeet\.com/jobs/{company_name}/([A-Z0-9\.]+)"
    RE_ATS_TOKEN   = r"""token["']?\s*[:=]\s*["']([^"']+)["']"""
    RE_OG_LOGO     = r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"'

    async def enrich(self, company: Company) -> Optional[CompanyUpdate]:
        if not company.name: return

        source_data = await self._fetch_valid_source(company)
        if not source_data: return

        update_payload = self._calculate_diff(company, source_data)
        if update_payload:
            logger.success(f"[{company.name}] Updates identified: {list(update_payload.keys())}")
            return CompanyUpdate(**update_payload)

        return

    async def _fetch_valid_source(self, company: Company) -> Optional[ComeetSourceData]:
        name = company.name.lower()
        config = company.metadata_config or {}
        existing_uid = config.get("uid")

        if existing_uid:
            data = await self._scrape_page(existing_uid, name)
            if data: return data
            logger.warning(f"[{name}] Stored UID {existing_uid} is stale/invalid.")

        return await self._discover_via_search(name)

    async def _scrape_page(self, uid: str, company_name: str) -> Optional[ComeetSourceData]:
        url = f"{self.CAREERS_BASE}/{company_name}/{uid}"
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                
                token = self._parse(self.RE_ATS_TOKEN, resp.text)
                if not token: return

                if not await ComeetScraper.is_valid_config({"uid": uid, "token": token}):
                    logger.warning(f"[{company_name}] Scraped token for UID {uid}, but API validation failed.")
                    return

                return ComeetSourceData(
                    uid=uid,
                    token=token,
                    career_url=url,
                    logo_url=self._parse(self.RE_OG_LOGO, resp.text)
                )
        except httpx.HTTPStatusError as e:
            logger.warning(f"[{company_name}] HTTP {e.response.status_code} accessing {url}")
            return
        except httpx.RequestError as e:
            logger.error(f"[{company_name}] Network error scraping {url}: {e}")
            return
        except Exception as e:
            logger.error(f"[{company_name}] Unexpected error scraping {url}: {e}")
            return

    async def _discover_via_search(self, company_name: str) -> Optional[ComeetSourceData]:
        queries = [
            f"jobs at {company_name} site:comeet.com",
            f"site:comeet.com/jobs/{company_name}",
            f"site:comeet.com inurl:jobs {company_name}"
        ]
        
        for query in queries:
            try:
                await asyncio.sleep(1.0)
                results = await asyncio.to_thread(lambda: list(DDGS().text(query, max_results=5)))
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "too many requests" in err_msg:
                     raise EnrichmentRateLimitError(f"DuckDuckGo rate limit for {company_name}")
                logger.warning(f"Discovery query '{query}' failed for {company_name}: {e}")
                continue
                
            uid_pattern = self.RE_COMPANY_UID.format(company_name=re.escape(company_name))
            
            for res in results:
                match = re.search(uid_pattern, res.get("href", ""), re.IGNORECASE)
                if match:
                    uid = match.group(1).rstrip(".")
                    data = await self._scrape_page(uid, company_name)
                    if data: return data
        
        return

    def _calculate_diff(self, company: Company, fresh: ComeetSourceData) -> Dict[str, Any]:
        updates = {}
        old_config = company.metadata_config or {}
        
        if old_config.get("uid") != fresh.uid or old_config.get("token") != fresh.token:
            updates["metadata_config"] = {"uid": fresh.uid, "token": fresh.token}

        if company.career_page_url != fresh.career_url:
            updates["career_page_url"] = fresh.career_url
            
        if fresh.logo_url and fresh.logo_url != company.logo_url:
            updates["logo_url"] = fresh.logo_url

        return updates

    @staticmethod
    def _parse(pattern: str, text: str) -> Optional[str]:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None