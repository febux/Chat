"""
Unit tests for auth-related exception handlers.

Ensures that authentication errors under `/api/**` return JSON with the correct
HTTP status, while HTML routes continue to redirect to `/auth`.
"""
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from src.backend.app.handlers.exception_handlers import add_exceptions_handlers
from src.backend.common.exceptions.api.token_exceptions import (
    ForbiddenError, TokenExpiredError, TokenNotFoundError)
from src.backend.common.exceptions.api.user_exceptions import UserNotFoundError


@pytest.fixture
def app():
    app = FastAPI()
    add_exceptions_handlers(app)

    @app.get("/api/protected")
    def api_route():
        raise TokenNotFoundError()

    @app.get("/html/protected")
    def html_route():
        raise TokenNotFoundError()

    @app.get("/api/admin")
    def api_admin_route():
        raise ForbiddenError()

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestAuthExceptionsOnApiRoutes:
    @pytest.mark.parametrize(
        "path, exc_factory, expected_status",
        [
            ("/api/token-expired", TokenExpiredError, 401),
            ("/api/token-missing", TokenNotFoundError, 401),
            ("/api/user-missing", UserNotFoundError, 401),
            ("/api/forbidden", ForbiddenError, 403),
        ],
    )
    def test_returns_json_with_status(
        self, app, client, path, exc_factory, expected_status
    ):
        # Register a dynamic route that raises the requested exception.
        @app.get(path)
        def _route():
            raise exc_factory()

        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == expected_status
        data = resp.json()
        assert "detail" in data


class TestAuthExceptionsOnHtmlRoutes:
    @pytest.mark.parametrize(
        "path, exc_factory",
        [
            ("/html/token-expired", TokenExpiredError),
            ("/html/token-missing", TokenNotFoundError),
            ("/html/user-missing", UserNotFoundError),
        ],
    )
    def test_redirects_to_auth(self, app, client, path, exc_factory):
        @app.get(path)
        def _route():
            raise exc_factory()

        resp = client.get(path, follow_redirects=False)
        assert resp.status_code in (307, 302)
        assert resp.headers["location"] == "/auth"
