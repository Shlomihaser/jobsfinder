import pytest
from httpx import Response, Request

@pytest.fixture
def mock_httpx_response():
    def _mock(status_code=200, json_data=None, text=None, url="https://mock.com"):
        request = Request(method="GET", url=url)
        return Response(status_code=status_code, json=json_data, text=text, request=request)
    return _mock
