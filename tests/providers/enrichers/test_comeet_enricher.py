import pytest
from unittest.mock import AsyncMock, patch

from app.models.company import Company, ATSProvider
from app.models.job import Job
from app.providers.enrichers.comeet_enricher import ComeetEnricher
from app.schemas.company import CompanyUpdate

@pytest.fixture
def enricher():
    return ComeetEnricher()

@pytest.fixture
def company():
    return Company(name="TestCorp", ats_provider=ATSProvider.COMEET)

@pytest.mark.asyncio
async def test_enrich_full_success(enricher, company, mock_httpx_response):
    """Should find both UID (via DDG) and Token (via Career Page)"""
    
    # Mock DuckDuckGo
    with patch("app.providers.enrichers.comeet_enricher.ComeetEnricher._ddg_search") as mock_ddg:
        mock_ddg.return_value = [{"href": "https://www.comeet.com/jobs/testcorp/12.ABC"}]
        
        # Mock Career Page Fetch
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            token_html = """<html><script>company.token = 'XYZ-TOKEN';</script></html>"""
            mock_get.return_value = mock_httpx_response(
                200, 
                text=token_html,
                url="https://www.comeet.com/jobs/testcorp/12.ABC"
            )

            result = await enricher.enrich(company)

            assert isinstance(result, CompanyUpdate)
            assert result.metadata_config["uid"] == "12.ABC"
            assert result.metadata_config["token"] == "XYZ-TOKEN"
            assert result.career_page_url == "https://www.comeet.com/jobs/testcorp/12.ABC"


@pytest.mark.asyncio
async def test_enrich_no_uid(enricher, company):
    """Should return None if DuckDuckGo finds nothing"""
    with patch("app.providers.enrichers.comeet_enricher.ComeetEnricher._ddg_search") as mock_ddg:
        mock_ddg.return_value = []  # No results
        
        result = await enricher.enrich(company)
        assert result is None


@pytest.mark.asyncio
async def test_enrich_uid_but_no_career_page(enricher, company, mock_httpx_response):
    """Should return just UID if career page 404s (partial enrichment)"""
    with patch("app.providers.enrichers.comeet_enricher.ComeetEnricher._ddg_search") as mock_ddg:
        mock_ddg.return_value = [{"href": "https://www.comeet.com/jobs/testcorp/12.ABC"}]
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            # 404 on career page fetch
            mock_get.return_value = mock_httpx_response(404)

            result = await enricher.enrich(company)

            assert result is not None
            assert result.metadata_config["uid"] == "12.ABC"
            assert "token" not in result.metadata_config


@pytest.mark.asyncio
async def test_enrich_uid_but_no_token(enricher, company, mock_httpx_response):
    """Should return UID and URL, but no token if regex fails"""
    with patch("app.providers.enrichers.comeet_enricher.ComeetEnricher._ddg_search") as mock_ddg:
        mock_ddg.return_value = [{"href": "https://www.comeet.com/jobs/testcorp/12.ABC"}]
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            # Page loads but has no token
            mock_get.return_value = mock_httpx_response(
                200, 
                text="<html>No token here</html>",
                url="https://www.comeet.com/jobs/testcorp/12.ABC"
            )

            result = await enricher.enrich(company)

            assert result is not None
            assert result.metadata_config["uid"] == "12.ABC"
            assert result.career_page_url == "https://www.comeet.com/jobs/testcorp/12.ABC"
            assert "token" not in result.metadata_config


@pytest.mark.asyncio
async def test_enrich_skip_if_complete(enricher, company):
    """Should skip if company already has UID and Token"""
    company.metadata_config = {"uid": "EXISTS", "token": "EXISTS"}
    result = await enricher.enrich(company)
    assert result is None
