"""Tests for JWT token creation and auth dependency."""

from app.auth import create_access_token, normalize_redirect_uri
import pytest


class TestCreateAccessToken:
    def test_creates_valid_token(self):
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_different_users_different_tokens(self):
        t1 = create_access_token("user-1")
        t2 = create_access_token("user-2")
        assert t1 != t2


class TestNormalizeRedirectUri:
    def test_adds_callback_path(self):
        result = normalize_redirect_uri("http://localhost:5173")
        assert result == "http://localhost:5173/auth/callback"

    def test_preserves_existing_path(self):
        result = normalize_redirect_uri("http://localhost:5173/custom/path")
        assert result == "http://localhost:5173/custom/path"

    def test_invalid_uri_raises(self):
        with pytest.raises(Exception):
            normalize_redirect_uri("not-a-url")

    def test_empty_string_uses_settings_default(self):
        # With ZHIHU_REDIRECT_URI set in env, empty string falls back to it
        result = normalize_redirect_uri("")
        assert "/auth/callback" in result
