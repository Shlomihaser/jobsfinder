import re
import asyncio
import httpx
from typing import Optional
from ddgs import DDGS
from loguru import logger

from app.models.company import Company, ATSProvider
from app.schemas.company import CompanyUpdate
from app.providers.enrichers.base import BaseEnricher


class ComeetEnricher(BaseEnricher):
    """
    Enricher for Comeet ATS.
    
    Enrichment flow:
      1. Find UID         → check metadata_config, else search DuckDuckGo
      2. Find career page → try slug variations to get the working URL + HTML
      3. Extract token    → regex the HTML for the API token
      4. Return CompanyUpdate with discovered uid, token, career_page_url
    """

    CAREERS_BASE = "https://www.comeet.com/jobs"

    async def enrich(self, company: Company) -> Optional[CompanyUpdate]:
        config = company.metadata_config or {}
        uid = config.get("uid", "").strip()
        token = config.get("token", "").strip()

        if uid and token:
            logger.info(f"{company.name}: UID and Token already present & valid")
            return

        # Step 1: Find UID
        if not uid:
            uid = await self._find_uid(company.name)
            if not uid:
                logger.warning(f"{company.name}: Could not find Comeet UID.")
                return

        # Step 2: Find career page
        if not token:
            result = await self._find_career_page(company.name, uid)
            if not result:
                logger.warning(f"{company.name}: Found UID ({uid}) but career page not reachable.")
                return CompanyUpdate(
                    metadata_config={**config, "uid": uid},
                )

            career_page_url, html = result

            # Step 3: Extract token
            token = self._extract_token(html)
            if not token:
                logger.warning(f"{company.name}: Career page found but could not extract token.")
                return CompanyUpdate(
                    career_page_url=career_page_url,
                    metadata_config={**config, "uid": uid},
                )
        else:
            career_page_url = company.career_page_url

        return CompanyUpdate(
            ats_provider=ATSProvider.COMEET,
            career_page_url=career_page_url,
            metadata_config={**config, "uid": uid, "token": token},
        )

    async def _find_uid(self, company_name: str) -> Optional[str]:
        """Search DuckDuckGo for the company's Comeet careers page and extract UID from URL."""
        queries = [
            f"site:comeet.com {company_name}",
            f"{company_name} comeet jobs",
        ]

        for query in queries:
            logger.debug(f"Searching: {query}")
            try:
                results = await asyncio.to_thread(self._ddg_search, query)
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed for '{query}': {e}")
                continue

            for result in results:
                url = result.get("href", "")
                matches = re.findall(r"comeet\.com/jobs/[^/]+/([A-Z0-9\.]+)", url, re.IGNORECASE)
                valid = [m.rstrip(".") for m in matches if len(m) > 4]
                if valid:
                    logger.success(f"Found UID for {company_name}: {valid[0]}")
                    return valid[0]

        return

    @staticmethod
    def _ddg_search(query: str) -> list:
        """Synchronous DuckDuckGo search — called via asyncio.to_thread."""
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=5))

    async def _find_career_page(self, company_name: str, uid: str) -> Optional[tuple[str, str]]:
        """Fetch the Comeet career page. Returns (url, html) or None."""
        slug = company_name.lower().replace(" ", "")
        url = f"{self.CAREERS_BASE}/{slug}/{uid}"
        logger.debug(f"Fetching career page: {url}")

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return str(resp.url), resp.text
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")

        return

    @staticmethod
    def _extract_token(html: str) -> Optional[str]:
        """Extract the Comeet API token from career page HTML."""
        match = re.search(
            r"""token["']?\s*[:=]\s*["']([^"']+)["']""",
            html,
            re.IGNORECASE,
        )
        return match.group(1) if match else None
