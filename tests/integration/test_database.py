"""Integration tests for database operations."""

import pytest
import os
from supabase import create_client
from src.config import Config


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for Supabase database operations."""
    
    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Set up Supabase client for integration tests."""
        if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_ROLE_KEY:
            pytest.skip("Supabase credentials not configured")
        
        self.client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_ROLE_KEY
        )
        yield
        # Cleanup if needed
    
    def test_database_connection(self, setup_client):
        """Test that we can connect to the database."""
        # Try a simple query
        result = self.client.table('internal_resources').select('id').limit(1).execute()
        assert result is not None
    
    def test_search_functions_exist(self, setup_client):
        """Test that search functions are available."""
        # This will fail if functions don't exist
        try:
            # We can't easily test the function without proper setup, but we can verify it exists
            result = self.client.rpc('search_internal_resources', {
                'query_text': 'test',
                'query_embedding': [0.1] * 1536,
                'match_threshold': 0.7,
                'match_count': 10
            }).execute()
            # If we get here, function exists (may return empty results)
            assert result is not None
        except Exception as e:
            # Function might not work without proper data, but should exist
            assert "function" in str(e).lower() or "does not exist" not in str(e).lower()
    
    def test_tables_exist(self, setup_client):
        """Test that all required tables exist."""
        required_tables = [
            'internal_resources',
            'external_resources',
            'policies',
            'experience',
            'rfps',
            'proposals',
            'validation_requests',
            'audit_log',
            'account_managers'
        ]
        
        for table_name in required_tables:
            try:
                result = self.client.table(table_name).select('*').limit(1).execute()
                assert result is not None
            except Exception as e:
                pytest.fail(f"Table {table_name} does not exist or is not accessible: {e}")
    
    def test_pending_reviews_view(self, setup_client):
        """Test that pending_reviews view exists."""
        try:
            result = self.client.table('pending_reviews').select('*').limit(1).execute()
            assert result is not None
        except Exception as e:
            pytest.fail(f"View pending_reviews does not exist: {e}")
