"""Unit tests for configuration management."""

import pytest
import os
from src.config import Config


class TestConfig:
    """Test configuration validation and loading."""
    
    def test_config_validation_success(self, env_vars):
        """Test that config validation passes with all required vars."""
        Config.validate()  # Should not raise
    
    def test_config_validation_missing_supabase_url(self, monkeypatch):
        """Test that validation fails when SUPABASE_URL is missing."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        with pytest.raises(ValueError, match="Missing required environment variables"):
            Config.validate()
    
    def test_config_validation_missing_service_role_key(self, monkeypatch):
        """Test that validation fails when SUPABASE_SERVICE_ROLE_KEY is missing."""
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        with pytest.raises(ValueError, match="Missing required environment variables"):
            Config.validate()
    
    def test_config_validation_missing_openai_key(self, monkeypatch):
        """Test that validation fails when OPENAI_API_KEY is missing."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Missing required environment variables"):
            Config.validate()
    
    def test_config_defaults(self, env_vars):
        """Test that default values are set correctly."""
        assert Config.OPENAI_EMBEDDING_MODEL == "text-embedding-3-small"
        assert Config.STATELESS_HTTP is True
    
    def test_config_optional_vars(self, env_vars):
        """Test that optional configuration variables are handled."""
        # These should not cause validation to fail
        assert Config.SMTP_HOST is None or isinstance(Config.SMTP_HOST, str)
        assert Config.TEAMS_ACCESS_TOKEN is None or isinstance(Config.TEAMS_ACCESS_TOKEN, str)
