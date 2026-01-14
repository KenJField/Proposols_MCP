"""Unit tests for embedding service."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from src.services.embeddings import EmbeddingService


class TestEmbeddingService:
    """Test embedding generation service."""
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, mock_openai_embedding):
        """Test successful embedding generation."""
        with patch('src.services.embeddings.openai.AsyncOpenAI') as mock_client:
            mock_client.return_value.embeddings.create = AsyncMock(
                return_value=Mock(data=[Mock(embedding=[0.1] * 1536)])
            )
            
            service = EmbeddingService()
            embedding = await service.generate_embedding("test text")
            
            assert len(embedding) == 1536
            assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self):
        """Test that empty text raises ValueError."""
        service = EmbeddingService()
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await service.generate_embedding("")
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self):
        """Test batch embedding generation."""
        with patch('src.services.embeddings.openai.AsyncOpenAI') as mock_client:
            mock_response = Mock()
            mock_response.data = [
                Mock(embedding=[0.1] * 1536),
                Mock(embedding=[0.2] * 1536),
                Mock(embedding=[0.3] * 1536)
            ]
            mock_client.return_value.embeddings.create = AsyncMock(
                return_value=mock_response
            )
            
            service = EmbeddingService()
            texts = ["text1", "text2", "text3"]
            embeddings = await service.generate_embeddings_batch(texts)
            
            assert len(embeddings) == 3
            assert all(len(e) == 1536 for e in embeddings)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_empty(self):
        """Test batch generation with empty list."""
        service = EmbeddingService()
        embeddings = await service.generate_embeddings_batch([])
        
        assert embeddings == []
    
    def test_get_embedding_service_singleton(self):
        """Test that get_embedding_service returns singleton."""
        from src.services.embeddings import get_embedding_service
        
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2
