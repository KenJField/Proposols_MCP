"""Unit tests for configuration management."""

import pytest
import os
from unittest.mock import patch
from src.config import Config


class TestConfig:
    """Test configuration validation and loading."""
    
    def test_config_validation_success(self, env_vars):
        """Test that config validation passes with all required vars."""
        # Patch Config attributes since they're set at import time
        with patch.object(Config, 'SUPABASE_URL', 'https://test.supabase.co'), \
             patch.object(Config, 'SUPABASE_SERVICE_ROLE_KEY', 'test-key'), \
             patch.object(Config, 'OPENAI_API_KEY', 'test-openai-key'):
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
        # These should work regardless of env vars
        assert Config.OPENAI_EMBEDDING_MODEL == "text-embedding-3-small" or Config.OPENAI_EMBEDDING_MODEL == os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        # STATELESS_HTTP depends on env var, so check it's a boolean
        assert isinstance(Config.STATELESS_HTTP, bool)
    
    def test_config_optional_vars(self, env_vars):
        """Test that optional configuration variables are handled."""
        # These should not cause validation to fail
        assert Config.SMTP_HOST is None or isinstance(Config.SMTP_HOST, str)
        assert Config.TEAMS_ACCESS_TOKEN is None or isinstance(Config.TEAMS_ACCESS_TOKEN, str)
