"""Validation workflow tools for Teams and email-based validation."""

from typing import Dict, Optional
from fastmcp import Context
from supabase import create_client
from src.config import Config
from src.services.teams import create_validation_adaptive_card, send_via_teams_mcp
from src.services.email import (
    create_validation_email_html,
    send_html_email,
    generate_validation_token
)
from src.tools.experience import record_experience
from src.utils.keywords import extract_keywords


# Initialize Supabase client
supabase = create_client(
    Config.SUPABASE_URL,
    Config.SUPABASE_SERVICE_ROLE_KEY
)


async def send_teams_validation(
    validation_id: str,
    recipient_email: str,
    validation_question: str,
    current_information: Dict,
    entity_name: str,
    ctx: Context
) -> str:
    """
    Send a validation request via Microsoft Teams using Adaptive Card.
    
    Args:
        validation_id: ID of the validation request in database
        recipient_email: Email of the person to validate
        validation_question: Question to ask
        current_information: Current data we have about the entity
        entity_name: Name of entity being validated
        ctx: FastMCP context
        
    Returns:
        Success message
    """
    await ctx.report_progress(0, 100, "Creating Adaptive Card")
    
    # Create Adaptive Card for validation
    card = create_validation_adaptive_card(
        validation_id=validation_id,
        question=validation_question,
        current_info=current_information,
        entity_name=entity_name
    )
    
    await ctx.report_progress(50, 100, "Sending to Teams")
    
    # Send via Graph API
    message_result = await send_via_teams_mcp(
        recipient_email=recipient_email,
        card_payload=card
    )
    
    # Update validation request with message ID
    supabase.table('validation_requests').update({
        'message_id': message_result['message_id'],
        'sent_at': 'now()',
        'validation_status': 'sent'
    }).eq('id', validation_id).execute()
    
    await ctx.report_progress(100, 100, "Validation request sent")
    
    return f"Validation sent to {recipient_email} via Teams (Message ID: {message_result['message_id']})"


async def send_email_validation(
    validation_id: str,
    recipient_email: str,
    recipient_name: str,
    validation_question: str,
    current_information: Dict,
    entity_name: str,
    ctx: Context
) -> str:
    """
    Send validation request via email with embedded response form.
    
    Args:
        validation_id: ID of the validation request
        recipient_email: Email of the recipient
        recipient_name: Name of the recipient
        validation_question: Validation question
        current_information: Current information about the entity
        entity_name: Name of the entity being validated
        ctx: FastMCP context
        
    Returns:
        Success message
    """
    await ctx.report_progress(0, 100, "Creating email")
    
    # Generate unique validation token for response link
    validation_token = generate_validation_token(validation_id)
    response_url = f"https://your-portal.com/validate/{validation_token}"
    
    # Create HTML email with embedded form
    html_body = create_validation_email_html(
        recipient_name=recipient_name,
        question=validation_question,
        current_info=current_information,
        entity_name=entity_name,
        response_url=response_url
    )
    
    await ctx.report_progress(50, 100, "Sending email")
    
    # Send email
    send_html_email(
        to_email=recipient_email,
        subject=f"Validation Required: {entity_name}",
        html_body=html_body
    )
    
    # Update validation request
    supabase.table('validation_requests').update({
        'message_id': validation_token,
        'sent_at': 'now()',
        'validation_status': 'sent'
    }).eq('id', validation_id).execute()
    
    await ctx.report_progress(100, 100, "Validation email sent")
    
    return f"Validation email sent to {recipient_email}"


async def process_validation_response(
    validation_id: str,
    approved: bool,
    corrections: Optional[str] = None,
    updated_information: Optional[Dict] = None,
    ctx: Optional[Context] = None
) -> Dict:
    """
    Process a validation response and update knowledge base if corrections provided.
    This tool would typically be called by a webhook handler.
    
    Args:
        validation_id: ID of the validation request
        approved: Whether the information was approved
        corrections: Text description of corrections
        updated_information: Structured updated data
        ctx: FastMCP context (optional)
        
    Returns:
        Dictionary with success status and details
    """
    # Update validation request
    validation_update = {
        'validation_status': 'approved' if approved else 'rejected',
        'response_received_at': 'now()',
        'corrections_provided': corrections
    }
    
    if updated_information:
        validation_update['response_data'] = updated_information
    
    validation_result = supabase.table('validation_requests').update(
        validation_update
    ).eq('id', validation_id).select().execute()
    
    if not validation_result.data:
        raise ValueError(f"Validation request {validation_id} not found")
    
    val_data = validation_result.data[0]
    
    # If corrections provided, create experience entry and update source
    if corrections or updated_information:
        # Extract key learnings from corrections
        keywords = extract_keywords(corrections) if corrections else []
        
        # Record experience
        experience = await record_experience(
            description=corrections or "Updated information from validation",
            keywords=keywords,
            entity_type=val_data['entity_type'],
            entity_id=val_data['entity_id'],
            entity_name=val_data.get('current_information', {}).get('name'),
            source_type='validation_response',
            confidence_score=0.95,  # High confidence from human validation
            source_id=validation_id,
            tenant_id=val_data['tenant_id'],
            ctx=ctx
        )
        
        # Link experience to validation
        supabase.table('validation_requests').update({
            'experience_created': True,
            'experience_id': experience['experience_id']
        }).eq('id', validation_id).execute()
        
        # Update the source entity if structured data provided
        if updated_information and val_data['entity_type'] == 'internal_resource':
            supabase.table('internal_resources').update(
                updated_information
            ).eq('id', val_data['entity_id']).execute()
    
    return {
        "success": True,
        "validation_id": validation_id,
        "knowledge_updated": bool(corrections or updated_information)
    }
