"""Proposal generation and resource allocation tools."""

from typing import Dict, List, Optional
from fastmcp import Context
from supabase import create_client
from src.config import Config
from src.tools.search import search_internal_resources, search_experience
from src.services.embeddings import get_embedding_service


# Initialize Supabase client
supabase = create_client(
    Config.SUPABASE_URL,
    Config.SUPABASE_SERVICE_ROLE_KEY
)


async def parse_rfp(
    document_url: str,
    rfp_number: Optional[str] = None,
    client_name: str = "",
    project_title: str = "",
    ctx: Optional[Context] = None
) -> Dict:
    """
    Parse RFP document and extract structured requirements.
    
    Note: For full LlamaParse integration, install llama-cloud-services and configure API key.
    This is a simplified version that stores the document URL for later processing.
    
    Args:
        document_url: URL or path to the RFP document
        rfp_number: Optional RFP number
        client_name: Name of the client
        project_title: Title of the project
        ctx: FastMCP context (optional)
        
    Returns:
        Dictionary with rfp_id and parsed requirements
    """
    # Extract tenant_id from context
    # In FastMCP, tenant_id should come from JWT claims via SupabaseProvider
    tenant_id = None
    if ctx and hasattr(ctx, 'request_context'):
        tenant_id = ctx.request_context.get("tenant_id")
    
    if not tenant_id:
        raise ValueError("tenant_id is required. Ensure JWT contains tenant_id claim.")
    
    # For now, create a basic RFP entry
    # In production, use LlamaParse to extract structured requirements
    rfp_data = {
        'tenant_id': tenant_id,
        'rfp_number': rfp_number,
        'client_name': client_name or "Unknown Client",
        'project_title': project_title or "Untitled Project",
        'raw_document_url': document_url,
        'parsed_markdown': f"RFP document: {document_url}",
        'parsed_requirements': {
            'summary': f"RFP for {project_title} from {client_name}",
            'requirements': [],
            'deadlines': {},
            'budget': {}
        }
    }
    
    result = supabase.table('rfps').insert(rfp_data).execute()
    rfp_id = result.data[0]['id']
    
    # Generate embedding for the RFP
    embedding_service = get_embedding_service()
    embedding = await embedding_service.generate_embedding(
        f"{project_title} {client_name} {document_url}"
    )
    
    # Update with embedding
    supabase.table('rfps').update({'embedding': embedding}).eq('id', rfp_id).execute()
    
    return {
        "rfp_id": rfp_id,
        "requirements": rfp_data['parsed_requirements']
    }


async def generate_proposal(
    rfp_id: str,
    ctx: Context
) -> str:
    """
    Generate a complete proposal for an RFP, including resource allocation,
    pricing, and validation workflow initiation.
    
    Args:
        rfp_id: ID of the RFP to generate proposal for
        ctx: FastMCP context (required for progress reporting)
        
    Returns:
        String message with proposal ID and summary
    """
    await ctx.report_progress(0, 100, "Loading RFP")
    
    # Get RFP details
    rfp_result = supabase.table('rfps').select('*').eq('id', rfp_id).single().execute()
    rfp_data = rfp_result.data
    
    tenant_id = rfp_data['tenant_id']
    
    await ctx.report_progress(10, 100, "Searching for relevant resources")
    
    # Search for relevant internal resources
    requirements_summary = rfp_data.get('parsed_requirements', {}).get('summary', '')
    if not requirements_summary:
        requirements_summary = f"{rfp_data['project_title']} {rfp_data['client_name']}"
    
    resources = await search_internal_resources(requirements_summary, max_results=20)
    
    # Search experience table for relevant past learnings
    await ctx.report_progress(30, 100, "Consulting institutional knowledge")
    
    experience_results = await search_experience(requirements_summary, max_results=20)
    
    # Generate proposal content (simplified)
    await ctx.report_progress(50, 100, "Drafting proposal")
    
    # Calculate total cost (simplified - use hourly_rate * 160 hours per resource)
    total_cost = sum(
        (r.get('hourly_rate', 0) or 0) * 160 
        for r in resources 
        if r.get('hourly_rate')
    )
    
    proposal_data = {
        'tenant_id': tenant_id,
        'rfp_id': rfp_id,
        'proposal_title': f"Proposal for {rfp_data['project_title']}",
        'proposal_status': 'draft',
        'internal_resources_used': [r['id'] for r in resources],
        'total_cost': total_cost,
        'created_by': 'ai',
        'team_composition': {
            'resources': [
                {
                    'id': r['id'],
                    'name': r.get('name', 'Unknown'),
                    'type': r.get('resource_type'),
                    'rate': r.get('hourly_rate')
                }
                for r in resources
            ]
        }
    }
    
    proposal_result = supabase.table('proposals').insert(proposal_data).execute()
    proposal_id = proposal_result.data[0]['id']
    
    # Create validation requests
    await ctx.report_progress(70, 100, "Creating validation requests")
    
    for resource in resources:
        validation = {
            'tenant_id': tenant_id,
            'proposal_id': proposal_id,
            'entity_type': 'internal_resource',
            'entity_id': resource['id'],
            'validation_question': (
                f"Can {resource.get('name', 'this resource')} be allocated to "
                f"project '{rfp_data['project_title']}' starting {rfp_data.get('project_start_date', 'TBD')}?"
            ),
            'current_information': resource,
            'recipient_name': resource.get('approval_contact_name', 'Manager'),
            'recipient_email': resource.get('approval_contact_email', 'manager@example.com'),
            'delivery_method': 'email'
        }
        supabase.table('validation_requests').insert(validation).execute()
    
    await ctx.report_progress(100, 100, "Proposal draft complete")
    
    return (
        f"Created proposal {proposal_id} with {len(resources)} resources requiring validation. "
        f"Total estimated cost: ${total_cost:,.2f}"
    )
