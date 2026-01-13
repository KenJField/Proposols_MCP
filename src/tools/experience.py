"""Experience recording and knowledge management tools."""

from typing import List, Dict, Optional
from fastmcp import Context
from supabase import create_client
from src.config import Config
from src.services.embeddings import get_embedding_service
from src.utils.keywords import extract_keywords


# Initialize Supabase client
supabase = create_client(
    Config.SUPABASE_URL,
    Config.SUPABASE_SERVICE_ROLE_KEY
)


async def record_experience(
    description: str,
    keywords: Optional[List[str]] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    source_type: str = "ai_inference",
    confidence_score: float = 0.8,
    source_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    ctx: Optional[Context] = None
) -> Dict:
    """
    Record a learned fact or knowledge update in the experience table.
    This is the primary way the AI builds institutional knowledge.
    
    Args:
        description: Detailed description of the learned fact
        keywords: Keywords for search and categorization (auto-extracted if not provided)
        entity_type: Type of entity (internal_resource, external_resource, policy)
        entity_id: ID of the associated entity
        entity_name: Name of the associated entity for display
        source_type: How this knowledge was obtained (validation_response, rfp_analysis, etc.)
        confidence_score: AI confidence in this fact (0.0-1.0)
        source_id: Reference to validation request, proposal, etc.
        tenant_id: Tenant ID (extracted from context if not provided)
        ctx: FastMCP context (optional)
        
    Returns:
        Dictionary with success status and experience_id
    """
    # Extract tenant_id from context if available
    # In FastMCP, tenant_id should come from JWT claims via SupabaseProvider
    if not tenant_id:
        # Try to get from context
        if ctx and hasattr(ctx, 'request_context'):
            tenant_id = ctx.request_context.get("tenant_id")
        # If still not available, try to get from auth context
        # This will be set by SupabaseProvider from JWT claims
        if not tenant_id:
            raise ValueError("tenant_id is required. Ensure JWT contains tenant_id claim.")
    
    # Auto-extract keywords if not provided
    if not keywords:
        keywords = extract_keywords(description)
    
    # Generate embedding
    embedding_service = get_embedding_service()
    embedding = await embedding_service.generate_embedding(description)
    
    # Insert experience
    result = supabase.table('experience').insert({
        'tenant_id': tenant_id,
        'description': description,
        'keywords': keywords,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'entity_name': entity_name,
        'source_type': source_type,
        'source_id': source_id,
        'confidence_score': confidence_score,
        'embedding': embedding,
        'created_by': 'ai'
    }).execute()
    
    return {
        "success": True,
        "experience_id": result.data[0]['id'],
        "message": f"Recorded experience about {entity_name or 'general topic'}"
    }
