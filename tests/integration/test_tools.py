"""Integration tests for MCP tools."""

import pytest
from unittest.mock import patch, AsyncMock, Mock
from src.tools.search import search_internal_resources, search_experience
from src.tools.experience import record_experience


@pytest.mark.integration
class TestSearchTools:
    """Integration tests for search tools."""
    
    @pytest.mark.asyncio
    async def test_search_internal_resources_mock(self, mock_supabase_client, mock_openai_embedding):
        """Test search_internal_resources with mocked dependencies."""
        with patch('src.tools.search.supabase', mock_supabase_client), \
             patch('src.services.embeddings.openai.AsyncOpenAI') as mock_openai:
            
            mock_openai.return_value.embeddings.create = AsyncMock(
                return_value=Mock(data=[Mock(embedding=[0.1] * 1536)])
            )
            mock_supabase_client.rpc.return_value.execute.return_value = Mock(
                data=[{"id": "123", "name": "Test Resource", "description": "Test"}]
            )
            
            results = await search_internal_resources("Python developer")
            
            assert isinstance(results, list)
            mock_supabase_client.rpc.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_experience_mock(self, mock_supabase_client, mock_openai_embedding):
        """Test search_experience with mocked dependencies (only returns validated experiences)."""
        with patch('src.tools.search.supabase', mock_supabase_client), \
             patch('src.services.embeddings.openai.AsyncOpenAI') as mock_openai:
            
            mock_openai.return_value.embeddings.create = AsyncMock(
                return_value=Mock(data=[Mock(embedding=[0.1] * 1536)])
            )
            mock_supabase_client.rpc.return_value.execute.return_value = Mock(
                data=[{"id": "123", "description": "Test experience", "is_validated": True}]
            )
            
            results = await search_experience("rate update")
            
            assert isinstance(results, list)
            mock_supabase_client.rpc.assert_called_once()


@pytest.mark.integration
class TestExperienceTools:
    """Integration tests for experience tools."""
    
    @pytest.mark.asyncio
    async def test_record_experience_mock(self, mock_supabase_client, mock_context):
        """Test record_experience with mocked dependencies (synchronous embeddings)."""
        with patch('src.tools.experience.supabase', mock_supabase_client), \
             patch('src.services.embeddings.openai.AsyncOpenAI') as mock_openai:
            
            mock_openai.return_value.embeddings.create = AsyncMock(
                return_value=Mock(data=[Mock(embedding=[0.1] * 1536)])
            )
            mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock(
                data=[{"id": "exp-123"}]
            )
            
            result = await record_experience(
                description="Test experience",
                confidence=0.8,
                requires_review=True
            )
            
            assert result["success"] is True
            assert "experience_id" in result
            mock_supabase_client.table.assert_called_with('experience')
            # Verify embedding was generated synchronously
            mock_openai.return_value.embeddings.create.assert_called_once()
