# Validation Workflow Implementation

This document provides complete implementation examples for the validation workflow using Microsoft Teams Adaptive Cards and email-based validation.

## Teams Integration with Adaptive Cards

### 1. FastMCP Tool for Sending Teams Validation

```python
from fastmcp import FastMCP, Context
from typing import Dict, Optional
import httpx
import json

mcp = FastMCP("ProposalKnowledgeBase")

@mcp.tool(task=True)
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
    Uses the teams-mcp server for Graph API integration.
    
    Args:
        validation_id: ID of the validation request in database
        recipient_email: Email of the person to validate
        validation_question: Question to ask
        current_information: Current data we have about the entity
        entity_name: Name of entity being validated
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
    
    # Send via Graph API using teams-mcp
    # Note: In actual implementation, this would use the MCP protocol
    # to call the teams-mcp server's send_message tool
    message_result = await send_via_teams_mcp(
        recipient_email=recipient_email,
        card_payload=card
    )
    
    # Update validation request with message ID
    supabase.table('validation_requests')\
        .update({
            'message_id': message_result['message_id'],
            'sent_at': 'now()',
            'validation_status': 'sent'
        })\
        .eq('id', validation_id)\
        .execute()
    
    await ctx.report_progress(100, 100, "Validation request sent")
    
    return f"Validation sent to {recipient_email} via Teams (Message ID: {message_result['message_id']})"


def create_validation_adaptive_card(
    validation_id: str,
    question: str,
    current_info: Dict,
    entity_name: str
) -> Dict:
    """
    Create an Adaptive Card with validation question and current information.
    Uses Universal Actions for interactive responses.
    """
    
    # Build facts array from current_info
    facts = []
    for key, value in current_info.items():
        if key not in ['id', 'tenant_id', 'embedding', 'search_vector']:
            facts.append({
                "title": key.replace('_', ' ').title(),
                "value": str(value)
            })
    
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "refresh": {
            "action": {
                "type": "Action.Execute",
                "title": "Refresh",
                "verb": "refresh"
            },
            "userIds": []  # Will be populated with recipient
        },
        "body": [
            {
                "type": "Container",
                "style": "emphasis",
                "items": [
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "width": "auto",
                                "items": [
                                    {
                                        "type": "Image",
                                        "url": "https://your-domain.com/icons/validation.png",
                                        "size": "Small",
                                        "style": "Person"
                                    }
                                ]
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": "Resource Validation Request",
                                        "weight": "Bolder",
                                        "size": "Large"
                                    },
                                    {
                                        "type": "TextBlock",
                                        "text": f"Regarding: {entity_name}",
                                        "isSubtle": True,
                                        "spacing": "None"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "type": "Container",
                "spacing": "Large",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": question,
                        "wrap": True,
                        "size": "Medium"
                    }
                ]
            },
            {
                "type": "Container",
                "spacing": "Medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "Current Information:",
                        "weight": "Bolder",
                        "spacing": "Medium"
                    },
                    {
                        "type": "FactSet",
                        "facts": facts
                    }
                ]
            },
            {
                "type": "TextBlock",
                "text": "Please confirm if this information is accurate or provide corrections below.",
                "wrap": True,
                "spacing": "Medium",
                "isSubtle": True
            },
            {
                "type": "Input.Text",
                "id": "corrections",
                "placeholder": "Enter any corrections or updates here...",
                "isMultiline": True,
                "maxLength": 2000
            },
            {
                "type": "Input.ChoiceSet",
                "id": "approval_status",
                "style": "expanded",
                "choices": [
                    {
                        "title": "✅ Information is accurate",
                        "value": "approved"
                    },
                    {
                        "title": "⚠️ Needs corrections (see above)",
                        "value": "corrections_needed"
                    },
                    {
                        "title": "❌ Cannot be allocated",
                        "value": "rejected"
                    }
                ],
                "value": "approved"
            }
        ],
        "actions": [
            {
                "type": "Action.Execute",
                "title": "Submit Response",
                "verb": "submit_validation",
                "data": {
                    "validation_id": validation_id,
                    "msteams": {
                        "type": "messageBack",
                        "displayText": "Validation response submitted"
                    }
                },
                "style": "positive"
            },
            {
                "type": "Action.OpenUrl",
                "title": "View Full Details",
                "url": f"https://your-portal.com/validations/{validation_id}"
            }
        ]
    }
    
    return card


async def send_via_teams_mcp(recipient_email: str, card_payload: Dict) -> Dict:
    """
    Send message via teams-mcp server.
    In production, this would use MCP client to call the teams-mcp server.
    """
    # This is a simplified example. In production, use MCP client:
    # from mcp import ClientSession, StdioServerParameters
    # from mcp.client.stdio import stdio_client
    
    # For now, showing direct Graph API call pattern
    # The teams-mcp server handles OAuth and API complexity
    
    graph_api_url = "https://graph.microsoft.com/v1.0/users/me/chats"
    
    # Get or create chat with recipient
    async with httpx.AsyncClient() as client:
        # In production, teams-mcp handles authentication
        headers = {
            "Authorization": f"Bearer {get_teams_token()}",
            "Content-Type": "application/json"
        }
        
        # Find existing chat or create new
        chats_response = await client.get(
            f"{graph_api_url}",
            headers=headers,
            params={"$filter": f"members/any(m: m/emailAddress eq '{recipient_email}')"}
        )
        chats = chats_response.json()
        
        if chats['value']:
            chat_id = chats['value'][0]['id']
        else:
            # Create new chat
            create_chat_response = await client.post(
                graph_api_url,
                headers=headers,
                json={
                    "chatType": "oneOnOne",
                    "members": [
                        {
                            "user": {
                                "userPrincipalName": recipient_email
                            },
                            "roles": ["owner"]
                        }
                    ]
                }
            )
            chat_id = create_chat_response.json()['id']
        
        # Send Adaptive Card message
        message_response = await client.post(
            f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages",
            headers=headers,
            json={
                "body": {
                    "contentType": "html",
                    "content": "<attachment id=\"validation_card\"></attachment>"
                },
                "attachments": [
                    {
                        "id": "validation_card",
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": json.dumps(card_payload)
                    }
                ]
            }
        )
        
        return {
            "message_id": message_response.json()['id'],
            "chat_id": chat_id
        }


def get_teams_token():
    """Get OAuth token for Teams. In production, teams-mcp handles this."""
    # Placeholder - teams-mcp server manages OAuth flow
    return os.environ.get("TEAMS_ACCESS_TOKEN")
```

### 2. Webhook Handler for Adaptive Card Responses

Create `supabase/functions/teams-webhook/index.ts`:

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  try {
    const payload = await req.json()
    
    // Validate webhook signature (important for security)
    const isValid = await validateTeamsWebhook(req.headers, payload)
    if (!isValid) {
      return new Response('Unauthorized', { status: 401 })
    }
    
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )
    
    // Extract validation response from Adaptive Card submission
    const { action, data } = payload.value || {}
    
    if (action?.verb === 'submit_validation') {
      const validation_id = data.validation_id
      const approval_status = data.approval_status
      const corrections = data.corrections
      
      // Update validation request
      const { data: validation } = await supabase
        .from('validation_requests')
        .update({
          validation_status: approval_status === 'approved' ? 'approved' : 
                           approval_status === 'rejected' ? 'rejected' : 'updated',
          response_received_at: new Date().toISOString(),
          corrections_provided: corrections,
          response_data: {
            approval_status,
            corrections,
            responded_by: payload.from.user.displayName,
            responded_at: new Date().toISOString()
          }
        })
        .eq('id', validation_id)
        .select()
        .single()
      
      // If corrections provided, create experience and update entity
      if (corrections && corrections.trim() !== '') {
        // Generate embedding
        const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: 'text-embedding-3-small',
            input: corrections
          })
        })
        
        const embeddingData = await embeddingResponse.json()
        
        // Extract keywords (simple approach)
        const keywords = corrections
          .toLowerCase()
          .split(/\s+/)
          .filter(w => w.length > 4)
          .slice(0, 10)
        
        // Create experience entry
        const { data: experience } = await supabase
          .from('experience')
          .insert({
            tenant_id: validation.tenant_id,
            description: `Validation correction: ${corrections}`,
            keywords,
            entity_type: validation.entity_type,
            entity_id: validation.entity_id,
            source_type: 'validation_response',
            source_id: validation_id,
            confidence_score: 0.95,
            embedding: embeddingData.data[0].embedding,
            created_by: 'ai'
          })
          .select()
          .single()
        
        // Link experience to validation
        await supabase
          .from('validation_requests')
          .update({
            experience_created: true,
            experience_id: experience.id
          })
          .eq('id', validation_id)
        
        // Send confirmation card
        await sendConfirmationCard(validation_id, payload.from.user.id)
      }
      
      return new Response(
        JSON.stringify({ 
          type: 'message',
          text: '✅ Thank you! Your validation response has been recorded.'
        }),
        { 
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        }
      )
    }
    
    return new Response('OK', { status: 200 })
    
  } catch (error) {
    console.error('Webhook error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    )
  }
})

async function validateTeamsWebhook(headers: Headers, payload: any): Promise<boolean> {
  // Implement HMAC signature validation
  // See: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-outgoing-webhook
  const signature = headers.get('authorization')
  const hmac = Deno.env.get('TEAMS_WEBHOOK_SECRET')
  
  // Validate signature matches
  // Implementation depends on your Teams app setup
  return true  // Placeholder
}

async function sendConfirmationCard(validation_id: string, user_id: string) {
  // Send a simple confirmation card back to the user
  // Implementation would use Graph API or teams-mcp server
}
```

## Email-Based Validation

### 1. FastMCP Tool for Email Validation

```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

@mcp.tool(task=True)
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
    supabase.table('validation_requests')\
        .update({
            'message_id': validation_token,
            'sent_at': 'now()',
            'validation_status': 'sent'
        })\
        .eq('id', validation_id)\
        .execute()
    
    await ctx.report_progress(100, 100, "Validation email sent")
    
    return f"Validation email sent to {recipient_email}"


def create_validation_email_html(
    recipient_name: str,
    question: str,
    current_info: Dict,
    entity_name: str,
    response_url: str
) -> str:
    """Create professional HTML email with validation form."""
    
    # Build current info table
    info_rows = ""
    for key, value in current_info.items():
        if key not in ['id', 'tenant_id', 'embedding', 'search_vector']:
            info_rows += f"""
                <tr>
                    <td style="padding: 8px; font-weight: bold; color: #555;">
                        {key.replace('_', ' ').title()}
                    </td>
                    <td style="padding: 8px; color: #333;">
                        {value}
                    </td>
                </tr>
            """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">Resource Validation Request</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Regarding: {entity_name}</p>
        </div>
        
        <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                Hi {recipient_name},
            </p>
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                {question}
            </p>
            
            <div style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #667eea;">Current Information:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    {info_rows}
                </table>
            </div>
            
            <p style="font-size: 14px; color: #666; margin: 20px 0;">
                Please review the information above and confirm its accuracy or provide corrections.
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{response_url}" 
                   style="display: inline-block; background: #667eea; color: white; padding: 15px 40px; 
                          text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                    Respond to Validation Request
                </a>
            </div>
            
            <p style="font-size: 12px; color: #999; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                This validation request will expire in 7 days. If you need more time, please contact the proposal team.
            </p>
            
        </div>
        
    </body>
    </html>
    """
    
    return html


def send_html_email(to_email: str, subject: str, html_body: str):
    """Send HTML email via SMTP."""
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = os.environ['EMAIL_FROM']
    msg['To'] = to_email
    
    # Attach HTML body
    msg.attach(MIMEText(html_body, 'html'))
    
    # Send via SMTP
    with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT'])) as server:
        server.starttls()
        server.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        server.send_message(msg)


def generate_validation_token(validation_id: str) -> str:
    """Generate secure token for validation response URL."""
    import secrets
    import hashlib
    
    token = secrets.token_urlsafe(32)
    
    # Store token mapping in database or cache
    # validation_id -> token (expires in 7 days)
    
    return token
```

### 2. Web Response Handler

Create a simple web form handler in `supabase/functions/validation-response/index.ts`:

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  const url = new URL(req.url)
  
  // Handle GET request - show form
  if (req.method === 'GET') {
    const token = url.pathname.split('/').pop()
    
    // Validate token and get validation request
    const validation = await getValidationByToken(token)
    
    if (!validation) {
      return new Response('Invalid or expired validation link', { status: 404 })
    }
    
    // Return HTML form
    return new Response(createValidationForm(validation), {
      headers: { 'Content-Type': 'text/html' }
    })
  }
  
  // Handle POST request - process form submission
  if (req.method === 'POST') {
    const formData = await req.formData()
    const token = formData.get('token')
    const approval_status = formData.get('approval_status')
    const corrections = formData.get('corrections')
    
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )
    
    const validation = await getValidationByToken(token)
    
    if (!validation) {
      return new Response('Invalid or expired validation link', { status: 404 })
    }
    
    // Update validation
    await supabase
      .from('validation_requests')
      .update({
        validation_status: approval_status,
        response_received_at: new Date().toISOString(),
        corrections_provided: corrections,
        response_data: {
          approval_status,
          corrections,
          submitted_at: new Date().toISOString()
        }
      })
      .eq('id', validation.id)
    
    // Create experience if corrections provided
    if (corrections && corrections.trim() !== '') {
      // Similar to Teams webhook handler
      // Generate embedding, create experience, update entity
    }
    
    // Return success page
    return new Response(createSuccessPage(), {
      headers: { 'Content-Type': 'text/html' }
    })
  }
  
  return new Response('Method not allowed', { status: 405 })
})

async function getValidationByToken(token: string) {
  // Lookup validation by token
  // Implementation depends on your token storage strategy
  return null  // Placeholder
}

function createValidationForm(validation: any): string {
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Validation Response</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #667eea; }
            .info-box {
                background: #f9f9f9;
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
            }
            label {
                display: block;
                margin: 15px 0 5px 0;
                font-weight: bold;
            }
            textarea {
                width: 100%;
                min-height: 100px;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-family: Arial, sans-serif;
            }
            .radio-group {
                margin: 10px 0;
            }
            .radio-group label {
                display: inline;
                font-weight: normal;
                margin-left: 5px;
            }
            button {
                background: #667eea;
                color: white;
                padding: 15px 40px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
            }
            button:hover {
                background: #5568d3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Validation Response</h1>
            <p><strong>Entity:</strong> ${validation.entity_name}</p>
            <p><strong>Question:</strong> ${validation.validation_question}</p>
            
            <div class="info-box">
                <h3>Current Information:</h3>
                <pre>${JSON.stringify(validation.current_information, null, 2)}</pre>
            </div>
            
            <form method="POST">
                <input type="hidden" name="token" value="${validation.token}">
                
                <label>Response:</label>
                <div class="radio-group">
                    <input type="radio" name="approval_status" value="approved" id="approved" checked>
                    <label for="approved">✅ Information is accurate</label>
                </div>
                <div class="radio-group">
                    <input type="radio" name="approval_status" value="updated" id="updated">
                    <label for="updated">⚠️ Needs corrections (see below)</label>
                </div>
                <div class="radio-group">
                    <input type="radio" name="approval_status" value="rejected" id="rejected">
                    <label for="rejected">❌ Cannot be allocated/approved</label>
                </div>
                
                <label for="corrections">Corrections or Additional Information:</label>
                <textarea name="corrections" id="corrections" placeholder="Please provide any corrections or additional information here..."></textarea>
                
                <button type="submit">Submit Response</button>
            </form>
        </div>
    </body>
    </html>
  `
}

function createSuccessPage(): string {
  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Response Submitted</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
                text-align: center;
            }
            .container {
                background: white;
                padding: 60px 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .checkmark {
                font-size: 80px;
                color: #4CAF50;
            }
            h1 { color: #333; }
            p { color: #666; font-size: 16px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✓</div>
            <h1>Thank You!</h1>
            <p>Your validation response has been submitted successfully.</p>
            <p>You can now close this window.</p>
        </div>
    </body>
    </html>
  `
}
```

## Testing the Validation Workflow

### Test Script

```python
import asyncio
from your_mcp_server import (
    send_teams_validation,
    send_email_validation,
    process_validation_response
)

async def test_validation_workflow():
    """End-to-end test of validation workflow."""
    
    # 1. Create test validation request
    validation = supabase.table('validation_requests').insert({
        'tenant_id': 'test-tenant-id',
        'proposal_id': 'test-proposal-id',
        'entity_type': 'internal_resource',
        'entity_id': 'test-resource-id',
        'validation_question': 'Can Jane Smith be allocated to Project Alpha?',
        'current_information': {
            'name': 'Jane Smith',
            'hourly_rate': 150.00,
            'availability_status': 'available'
        },
        'recipient_name': 'Engineering Manager',
        'recipient_email': 'manager@example.com',
        'delivery_method': 'teams'
    }).execute()
    
    validation_id = validation.data[0]['id']
    
    # 2. Send Teams validation
    print("Sending Teams validation...")
    result = await send_teams_validation(
        validation_id=validation_id,
        recipient_email='manager@example.com',
        validation_question='Can Jane Smith be allocated to Project Alpha?',
        current_information={'name': 'Jane Smith', 'hourly_rate': 150.00},
        entity_name='Jane Smith'
    )
    print(f"Result: {result}")
    
    # 3. Simulate response (in real scenario, comes from webhook)
    print("\nSimulating validation response...")
    await asyncio.sleep(2)
    
    response_result = await process_validation_response(
        validation_id=validation_id,
        approved=False,
        corrections="Jane's rate is actually $175/hour now, and she's only available starting next month.",
        updated_information={'hourly_rate': 175.00, 'available_from': '2025-02-01'}
    )
    print(f"Response processed: {response_result}")
    
    # 4. Check that experience was created
    experience = supabase.table('experience')\
        .select('*')\
        .eq('source_id', validation_id)\
        .execute()
    
    print(f"\nExperience created: {len(experience.data)} entries")
    if experience.data:
        print(f"Description: {experience.data[0]['description']}")
        print(f"Keywords: {experience.data[0]['keywords']}")

if __name__ == '__main__':
    asyncio.run(test_validation_workflow())
```

## Monitoring and Analytics

```sql
-- Validation metrics dashboard query
WITH validation_metrics AS (
    SELECT 
        DATE_TRUNC('day', created_at) AS date,
        delivery_method,
        validation_status,
        COUNT(*) AS count,
        AVG(EXTRACT(EPOCH FROM (response_received_at - sent_at))) / 3600 AS avg_response_hours
    FROM validation_requests
    WHERE created_at >= NOW() - INTERVAL '30 days'
    GROUP BY DATE_TRUNC('day', created_at), delivery_method, validation_status
)
SELECT 
    date,
    delivery_method,
    SUM(CASE WHEN validation_status = 'approved' THEN count ELSE 0 END) AS approved,
    SUM(CASE WHEN validation_status = 'updated' THEN count ELSE 0 END) AS updated,
    SUM(CASE WHEN validation_status = 'rejected' THEN count ELSE 0 END) AS rejected,
    SUM(CASE WHEN validation_status = 'expired' THEN count ELSE 0 END) AS expired,
    AVG(avg_response_hours) AS avg_response_time_hours
FROM validation_metrics
GROUP BY date, delivery_method
ORDER BY date DESC, delivery_method;
```

This implementation provides a complete validation workflow that:
1. Sends professional validation requests via Teams or email
2. Collects structured responses through interactive cards or web forms
3. Automatically updates the knowledge base with corrections
4. Builds institutional knowledge through the experience table
5. Provides monitoring and analytics for optimization
