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
    updated_information: Optional[Dict] = None
) -> Dict:
    """
    Store a validation response. This just stores the raw response data.
    The AI should then read this response and call record_experience() to process it.
    
    This tool is typically called by a webhook handler to store raw responses.
    The AI will process the response and extract learnings.
    
    Args:
        validation_id: ID of the validation request
        approved: Whether the information was approved
        corrections: Text description of corrections (raw, stored as-is)
        updated_information: Structured updated data (raw, stored as-is)
        
    Returns:
        Dictionary with success status and details
    """
    # Update validation request with raw response data
    validation_update = {
        'validation_status': 'approved' if approved else 'rejected',
        'response_received_at': 'now()',
        'corrections_provided': corrections,
        'response_data': {
            'approved': approved,
            'corrections': corrections,
            'updated_information': updated_information
        }
    }
    
    validation_result = supabase.table('validation_requests').update(
        validation_update
    ).eq('id', validation_id).select().execute()
    
    if not validation_result.data:
        raise ValueError(f"Validation request {validation_id} not found")
    
    return {
        "success": True,
        "validation_id": validation_id,
        "message": "Validation response stored. AI should process this and call record_experience() if corrections were provided."
    }
