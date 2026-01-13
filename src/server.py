"""Main FastMCP server for Proposal Generation."""

import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.supabase import SupabaseProvider
from src.config import Config

# Import all tools
from src.tools.search import search_internal_resources, search_experience
from src.tools.experience import record_experience
from src.tools.proposals import parse_rfp, generate_proposal
from src.tools.validation import (
    send_teams_validation,
    send_email_validation,
    process_validation_response
)


def create_server() -> FastMCP:
    """Create and configure the FastMCP server."""
    
    # Validate configuration
    Config.validate()
    
    # Set up FastMCP with Supabase auth
    auth = SupabaseProvider(
        project_url=Config.SUPABASE_URL,
        algorithm="RS256",
        required_scopes=["read", "write"]
    )
    
    mcp = FastMCP(
        name="ProposalKnowledgeBase",
        auth=auth,
        stateless_http=Config.STATELESS_HTTP
    )
    
    # Register search tools
    @mcp.tool
    async def search_internal_resources_tool(
        query: str,
        resource_type: str | None = None,
        max_results: int = 10,
        match_threshold: float = 0.7
    ) -> list[dict]:
        """
        Search internal company resources using hybrid semantic + keyword search.
        
        Args:
            query: Natural language search query
            resource_type: Filter by type (staff, tool, asset, facility, license)
            max_results: Maximum number of results to return
            match_threshold: Minimum similarity threshold (0.0-1.0)
        """
        return await search_internal_resources(
            query=query,
            resource_type=resource_type,
            max_results=max_results,
            match_threshold=match_threshold
        )
    
    @mcp.tool
    async def search_experience_tool(
        query: str,
        entity_type: str | None = None,
        max_results: int = 20,
        match_threshold: float = 0.6
    ) -> list[dict]:
        """
        Search the AI knowledge base (experience table) for relevant learnings.
        
        Args:
            query: Natural language search query
            entity_type: Filter by entity type (internal_resource, external_resource, policy, etc.)
            max_results: Maximum number of results to return
            match_threshold: Minimum similarity threshold (0.0-1.0)
        """
        return await search_experience(
            query=query,
            entity_type=entity_type,
            max_results=max_results,
            match_threshold=match_threshold
        )
    
    # Register experience tools
    @mcp.tool
    async def record_experience_tool(
        description: str,
        keywords: list[str] | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        entity_name: str | None = None,
        source_type: str = "ai_inference",
        confidence_score: float = 0.8,
        source_id: str | None = None,
        ctx = None
    ) -> dict:
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
        """
        return await record_experience(
            description=description,
            keywords=keywords,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            source_type=source_type,
            confidence_score=confidence_score,
            source_id=source_id,
            ctx=ctx
        )
    
    # Register proposal tools
    @mcp.tool
    async def parse_rfp_tool(
        document_url: str,
        rfp_number: str | None = None,
        client_name: str = "",
        project_title: str = "",
        ctx = None
    ) -> dict:
        """
        Parse RFP document and extract structured requirements.
        
        Args:
            document_url: URL or path to the RFP document
            rfp_number: Optional RFP number
            client_name: Name of the client
            project_title: Title of the project
        """
        return await parse_rfp(
            document_url=document_url,
            rfp_number=rfp_number,
            client_name=client_name,
            project_title=project_title,
            ctx=ctx
        )
    
    @mcp.tool(task=True)  # Enable background task
    async def generate_proposal_tool(
        rfp_id: str,
        ctx
    ) -> str:
        """
        Generate a complete proposal for an RFP, including resource allocation,
        pricing, and validation workflow initiation.
        
        Args:
            rfp_id: ID of the RFP to generate proposal for
        """
        return await generate_proposal(rfp_id=rfp_id, ctx=ctx)
    
    # Register validation tools
    @mcp.tool(task=True)  # Enable background task
    async def send_teams_validation_tool(
        validation_id: str,
        recipient_email: str,
        validation_question: str,
        current_information: dict,
        entity_name: str,
        ctx
    ) -> str:
        """
        Send a validation request via Microsoft Teams using Adaptive Card.
        
        Args:
            validation_id: ID of the validation request in database
            recipient_email: Email of the person to validate
            validation_question: Question to ask
            current_information: Current data we have about the entity
            entity_name: Name of entity being validated
        """
        return await send_teams_validation(
            validation_id=validation_id,
            recipient_email=recipient_email,
            validation_question=validation_question,
            current_information=current_information,
            entity_name=entity_name,
            ctx=ctx
        )
    
    @mcp.tool(task=True)  # Enable background task
    async def send_email_validation_tool(
        validation_id: str,
        recipient_email: str,
        recipient_name: str,
        validation_question: str,
        current_information: dict,
        entity_name: str,
        ctx
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
        """
        return await send_email_validation(
            validation_id=validation_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            validation_question=validation_question,
            current_information=current_information,
            entity_name=entity_name,
            ctx=ctx
        )
    
    @mcp.tool
    async def process_validation_response_tool(
        validation_id: str,
        approved: bool,
        corrections: str | None = None,
        updated_information: dict | None = None
    ) -> dict:
        """
        Process a validation response and update knowledge base if corrections provided.
        This tool would typically be called by a webhook handler.
        
        Args:
            validation_id: ID of the validation request
            approved: Whether the information was approved
            corrections: Text description of corrections
            updated_information: Structured updated data
        """
        return await process_validation_response(
            validation_id=validation_id,
            approved=approved,
            corrections=corrections,
            updated_information=updated_information
        )
    
    return mcp


# Create server instance
app = create_server()


if __name__ == "__main__":
    # Run the server
    app.run()
