import pytest
from unittest.mock import AsyncMock, patch
from httpx import Response

from app.providers.scrapers.comeet_scraper import ComeetScraper
from app.core.exceptions import FatalProviderError, RetryableProviderError

@pytest.fixture
def scraper():
    return ComeetScraper(
        company_name="TestCorp",
        config={"uid": "123", "token": "abc"}
    )


@pytest.mark.asyncio
async def test_fetch_jobs_success(scraper, mock_httpx_response):
    """Should return parsed jobs when API succeeds"""
    mock_data = [
        {
            "name": "Software Engineer",
            "uid": "AB.123",
            "url_active_page": "https://comeet.com/jobs/test/AB.123",
            "location": {"country": "Israel", "city": "Tel Aviv"},
            "time_updated": "2024-02-14T10:00:00Z",
            "details": [
                {"name": "Description", "value": "<p>Code stuff</p>", "order": 1}
            ]
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_httpx_response(200, json_data=mock_data)
        
        jobs = await scraper.fetch_jobs()

        assert len(jobs) == 1
        assert jobs[0].title == "Software Engineer"
        assert jobs[0].external_id == "AB.123"
        assert jobs[0].city == "Tel Aviv"
        assert "<p>Code stuff</p>" in jobs[0].description


@pytest.mark.asyncio
async def test_fetch_jobs_fatal_error(scraper, mock_httpx_response):
    """Should raise FatalProviderError on 404/403 (bad config)"""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_httpx_response(404)
        
        with pytest.raises(FatalProviderError):
            await scraper.fetch_jobs()


@pytest.mark.asyncio
async def test_fetch_jobs_retryable_error(scraper, mock_httpx_response):
    """Should raise RetryableProviderError on 500/429"""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_httpx_response(500)
        
        with pytest.raises(RetryableProviderError):
            await scraper.fetch_jobs()


@pytest.mark.asyncio
async def test_validate_config_success(scraper, mock_httpx_response):
    """Should return True if API check succeeds"""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_httpx_response(200)
        assert await ComeetScraper.validate_config({"uid": "1", "token": "a"}) is True


@pytest.mark.asyncio
async def test_validate_config_failure(scraper, mock_httpx_response):
    """Should return False if API check fails"""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_httpx_response(401)
        assert await ComeetScraper.validate_config({"uid": "1", "token": "a"}) is False
