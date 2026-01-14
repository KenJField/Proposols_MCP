"""Hybrid search tools for internal resources and experience."""

from typing import List, Dict, Optional
from fastmcp import Context
from supabase import create_client
from src.config import Config
from src.services.embeddings import get_embedding_service


# Initialize Supabase client
supabase = create_client(
    Config.SUPABASE_URL,
    Config.SUPABASE_SERVICE_ROLE_KEY
)


async def search_internal_resources(
    query: str,
    resource_type: Optional[str] = None,
    max_results: int = 10,
    match_threshold: float = 0.7,
    ctx: Optional[Context] = None
) -> List[Dict]:
    """
    Search internal company resources using hybrid semantic + keyword search.
    
    Args:
        query: Natural language search query
        resource_type: Filter by type (staff, tool, asset, facility, license)
        max_results: Maximum number of results to return
        match_threshold: Minimum similarity threshold (0.0-1.0)
        ctx: FastMCP context (optional)
        
    Returns:
        List of matching internal resources
    """
    # Generate embedding for semantic search
    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.generate_embedding(query)
    
    # Call hybrid search function (no tenant_id parameter needed)
    result = supabase.rpc(
        'search_internal_resources',
        {
            'query_text': query,
            'query_embedding': query_embedding,
            'match_threshold': match_threshold,
            'match_count': max_results
        }
    ).execute()
    
    resources = result.data or []
    
    # Filter by resource_type if specified
    if resource_type:
        resources = [r for r in resources if r.get('resource_type') == resource_type]
    
    return resources


async def search_experience(
    query: str,
    entity_type: Optional[str] = None,
    max_results: int = 20,
    match_threshold: float = 0.6,
    ctx: Optional[Context] = None
) -> List[Dict]:
    """
    Search the AI knowledge base (experience table) for relevant learnings.
    
    Args:
        query: Natural language search query
        entity_type: Filter by entity type (internal_resource, external_resource, policy, etc.)
        max_results: Maximum number of results to return
        match_threshold: Minimum similarity threshold (0.0-1.0)
        ctx: FastMCP context (optional)
        
    Returns:
        List of matching experience entries
    """
    # Generate embedding for semantic search
    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.generate_embedding(query)
    
    # Call hybrid search function (no tenant_id parameter needed)
    result = supabase.rpc(
        'search_experience',
        {
            'query_text': query,
            'query_embedding': query_embedding,
            'match_threshold': match_threshold,
            'match_count': max_results,
            'p_entity_type': entity_type
        }
    ).execute()
    
    return result.data or []
