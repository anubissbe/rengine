"""The api application imports and describes itself.

Every other api test calls services directly, so a dependency upgrade that breaks the app
at import time (fastapi-pagination against a newer FastAPI, say) passed them all while the
server itself could not start.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.main import app

pytestmark = pytest.mark.api


def test_the_app_builds_its_openapi_schema_with_every_router():
    paths = app.openapi()["paths"]
    assert any(path.startswith(settings.API_V1_PREFIX) for path in paths)
    assert len(paths) > 100


async def test_the_app_serves_its_schema_over_http():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == settings.APP_NAME
