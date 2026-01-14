"""Experience recording and knowledge management tools."""

from typing import Dict, Optional
from supabase import create_client
from src.config import Config
from src.services.embeddings import get_embedding_service


# Initialize Supabase client
supabase = create_client(
    Config.SUPABASE_URL,
    Config.SUPABASE_SERVICE_ROLE_KEY
)


async def record_experience(
    description: str,
    entity_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_name: Optional[str] = None,
    confidence: float = 0.8,
    requires_review: bool = True,
    source_type: str = "ai_inference",
    source_id: Optional[str] = None
) -> Dict:
    """
    Record a learned fact or knowledge update in the experience table.
    This is the primary way the AI builds institutional knowledge.
    
    The AI should provide a clear description. Embeddings are generated synchronously.
    Keywords are optional - AI can provide them if needed, but they're not required.
    
    Args:
        description: Detailed description of the learned fact (AI provides this)
        entity_id: ID of the associated entity
        entity_type: Type of entity (internal_resource, external_resource, policy)
        entity_name: Name of the associated entity for display
        confidence: AI confidence in this fact (0.0-1.0)
        requires_review: Whether this should go to review queue (default: True)
        source_type: How this knowledge was obtained (validation_response, rfp_analysis, etc.)
        source_id: Reference to validation request, proposal, etc.
        
    Returns:
        Dictionary with success status and experience_id
    """
    # Generate embedding synchronously (<1 second)
    embedding_service = get_embedding_service()
    embedding = await embedding_service.generate_embedding(description)
    
    # Insert experience
    result = supabase.table('experience').insert({
        'description': description,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'entity_name': entity_name,
        'source_type': source_type,
        'source_id': source_id,
        'confidence_score': confidence,
        'embedding': embedding,
        'is_validated': not requires_review,  # Manual review gate
        'created_by': 'ai'
    }).execute()
    
    return {
        "success": True,
        "experience_id": result.data[0]['id'],
        "message": f"Recorded experience about {entity_name or 'general topic'}"
    }
