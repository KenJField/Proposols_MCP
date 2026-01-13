"""Microsoft Teams integration for validation requests."""

from typing import Dict, Optional
import httpx
import json
from src.config import Config


def create_validation_adaptive_card(
    validation_id: str,
    question: str,
    current_info: Dict,
    entity_name: str
) -> Dict:
    """
    Create an Adaptive Card with validation question and current information.
    Uses Universal Actions for interactive responses.
    
    Args:
        validation_id: ID of the validation request
        question: Validation question
        current_info: Current information about the entity
        entity_name: Name of the entity being validated
        
    Returns:
        Adaptive Card JSON payload
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
    Send message via Teams Graph API.
    
    In production, this would use MCP client to call the teams-mcp server.
    For now, this shows the direct Graph API call pattern.
    
    Args:
        recipient_email: Email of the recipient
        card_payload: Adaptive Card JSON payload
        
    Returns:
        Dictionary with message_id and chat_id
    """
    if not Config.TEAMS_ACCESS_TOKEN:
        raise ValueError("Teams access token not configured")
    
    graph_api_url = "https://graph.microsoft.com/v1.0/users/me/chats"
    
    headers = {
        "Authorization": f"Bearer {Config.TEAMS_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # Find existing chat or create new
        chats_response = await client.get(
            f"{graph_api_url}",
            headers=headers,
            params={"$filter": f"members/any(m: m/emailAddress eq '{recipient_email}')"}
        )
        chats = chats_response.json()
        
        if chats.get('value'):
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
