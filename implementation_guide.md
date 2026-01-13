# Supabase Schema Implementation Guide

## Overview

This guide explains how to implement and use the proposal generation MCP server database schema. The schema is designed for multi-tenant isolation, AI-driven knowledge updates, and seamless FastMCP integration.

## Quick Start: Schema Deployment

### 1. Apply the Schema to Supabase

```bash
# Using Supabase CLI
supabase db reset --db-url "postgresql://..."

# Or apply directly
psql -h db.your-project.supabase.co -U postgres -d postgres -f proposal_mcp_schema.sql
```

### 2. Set Up Supabase Auth Hooks for Tenant Claims

Create an Auth Hook to inject `tenant_id` into JWTs:

```sql
-- In Supabase Dashboard: Authentication > Hooks > Create Hook
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    claims jsonb;
    user_tenant_id uuid;
BEGIN
    -- Get user's tenant_id from your user_tenants table or metadata
    SELECT tenant_id INTO user_tenant_id
    FROM user_tenants
    WHERE user_id = (event->>'user_id')::uuid;
    
    claims := event->'claims';
    
    IF user_tenant_id IS NOT NULL THEN
        claims := jsonb_set(claims, '{tenant_id}', to_jsonb(user_tenant_id));
    END IF;
    
    event := jsonb_set(event, '{claims}', claims);
    
    RETURN event;
END;
$$;
```

### 3. Create User-Tenant Mapping Table

```sql
CREATE TABLE user_tenants (
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    role TEXT DEFAULT 'member',
    PRIMARY KEY (user_id, tenant_id)
);

-- Enable RLS
ALTER TABLE user_tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own tenants" ON user_tenants
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());
```

## FastMCP Integration Patterns

### Basic Server Setup with Authentication

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.supabase import SupabaseProvider
from supabase import create_client
import os

# Initialize Supabase client
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

# Set up FastMCP with Supabase auth
auth = SupabaseProvider(
    project_url=os.environ["SUPABASE_URL"],
    algorithm="RS256",
    required_scopes=["read", "write"]
)

mcp = FastMCP(
    name="ProposalKnowledgeBase",
    auth=auth,
    stateless_http=True  # For production multi-client support
)
```

### Tool: Search Internal Resources (with Hybrid Search)

```python
from typing import List, Dict, Optional
import openai

# Initialize OpenAI for embeddings
openai_client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

async def generate_embedding(text: str) -> List[float]:
    """Generate embedding for semantic search."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

@mcp.tool
async def search_internal_resources(
    query: str,
    resource_type: Optional[str] = None,
    max_results: int = 10
) -> List[Dict]:
    """
    Search internal company resources using hybrid semantic + keyword search.
    
    Args:
        query: Natural language search query
        resource_type: Filter by type (staff, tool, asset, facility, license)
        max_results: Maximum number of results to return
    """
    # Generate embedding for semantic search
    query_embedding = await generate_embedding(query)
    
    # Call hybrid search function
    result = supabase.rpc(
        'search_internal_resources',
        {
            'query_text': query,
            'query_embedding': query_embedding,
            'match_threshold': 0.7,
            'match_count': max_results
        }
    ).execute()
    
    resources = result.data
    
    # Filter by resource_type if specified
    if resource_type:
        resources = [r for r in resources if r['resource_type'] == resource_type]
    
    return resources
```

### Tool: Create AI Experience Entry

```python
from fastmcp import Context

@mcp.tool
async def record_experience(
    description: str,
    keywords: List[str],
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    source_type: str = "ai_inference",
    confidence_score: float = 0.8,
    ctx: Optional[Context] = None
) -> Dict:
    """
    Record a learned fact or knowledge update in the experience table.
    This is the primary way the AI builds institutional knowledge.
    
    Args:
        description: Detailed description of the learned fact
        keywords: Keywords for search and categorization
        entity_type: Type of entity (internal_resource, external_resource, policy)
        entity_id: ID of the associated entity
        entity_name: Name of the associated entity for display
        source_type: How this knowledge was obtained
        confidence_score: AI confidence in this fact (0.0-1.0)
    """
    # Get tenant_id from context (automatically from JWT)
    tenant_id = ctx.request_context.get("tenant_id") if ctx else None
    
    # Generate embedding
    embedding = await generate_embedding(description)
    
    # Insert experience
    result = supabase.table('experience').insert({
        'tenant_id': tenant_id,
        'description': description,
        'keywords': keywords,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'entity_name': entity_name,
        'source_type': source_type,
        'confidence_score': confidence_score,
        'embedding': embedding,
        'created_by': 'ai'
    }).execute()
    
    return {
        "success": True,
        "experience_id": result.data[0]['id'],
        "message": f"Recorded experience about {entity_name or 'general topic'}"
    }
```

### Tool: Generate Proposal with Validation

```python
@mcp.tool(task=True)  # Enable background task
async def generate_proposal(
    rfp_id: str,
    ctx: Context
) -> str:
    """
    Generate a complete proposal for an RFP, including resource allocation,
    pricing, and validation workflow initiation.
    """
    await ctx.report_progress(0, 100, "Loading RFP")
    
    # Get RFP details
    rfp = supabase.table('rfps').select('*').eq('id', rfp_id).single().execute()
    rfp_data = rfp.data
    
    await ctx.report_progress(10, 100, "Searching for relevant resources")
    
    # Search for relevant internal resources
    resources = await search_internal_resources(
        rfp_data['parsed_requirements']['summary']
    )
    
    # Search experience table for relevant past learnings
    await ctx.report_progress(30, 100, "Consulting institutional knowledge")
    
    experience_embedding = await generate_embedding(
        rfp_data['parsed_requirements']['summary']
    )
    experience_results = supabase.rpc(
        'search_experience',
        {
            'query_text': rfp_data['parsed_requirements']['summary'],
            'query_embedding': experience_embedding,
            'match_threshold': 0.6,
            'match_count': 20
        }
    ).execute()
    
    # Generate proposal content (simplified)
    await ctx.report_progress(50, 100, "Drafting proposal")
    
    proposal_data = {
        'tenant_id': ctx.request_context.get('tenant_id'),
        'rfp_id': rfp_id,
        'proposal_title': f"Proposal for {rfp_data['project_title']}",
        'proposal_status': 'draft',
        'internal_resources_used': [r['id'] for r in resources],
        'total_cost': sum(r.get('hourly_rate', 0) * 160 for r in resources),  # Simplified
        'created_by': 'ai'
    }
    
    proposal = supabase.table('proposals').insert(proposal_data).execute()
    proposal_id = proposal.data[0]['id']
    
    # Create validation requests
    await ctx.report_progress(70, 100, "Creating validation requests")
    
    for resource in resources:
        validation = {
            'tenant_id': ctx.request_context.get('tenant_id'),
            'proposal_id': proposal_id,
            'entity_type': 'internal_resource',
            'entity_id': resource['id'],
            'validation_question': f"Can {resource['name']} be allocated to project '{rfp_data['project_title']}' starting {rfp_data['project_start_date']}?",
            'current_information': resource,
            'recipient_name': resource['approval_contact_name'],
            'recipient_email': resource['approval_contact_email'],
            'delivery_method': 'email'
        }
        supabase.table('validation_requests').insert(validation).execute()
    
    await ctx.report_progress(100, 100, "Proposal draft complete")
    
    return f"Created proposal {proposal_id} with {len(resources)} resources requiring validation"
```

### Tool: Process Validation Response (Called by Webhook)

```python
@mcp.tool
async def process_validation_response(
    validation_id: str,
    approved: bool,
    corrections: Optional[str] = None,
    updated_information: Optional[Dict] = None
) -> Dict:
    """
    Process a validation response and update knowledge base if corrections provided.
    This tool would typically be called by a webhook handler.
    
    Args:
        validation_id: ID of the validation request
        approved: Whether the information was approved
        corrections: Text description of corrections
        updated_information: Structured updated data
    """
    # Update validation request
    validation_update = {
        'validation_status': 'approved' if approved else 'rejected',
        'response_received_at': 'now()',
        'corrections_provided': corrections
    }
    
    if updated_information:
        validation_update['response_data'] = updated_information
    
    validation = supabase.table('validation_requests')\
        .update(validation_update)\
        .eq('id', validation_id)\
        .execute()
    
    val_data = validation.data[0]
    
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
            source_type='validation_response',
            confidence_score=0.95  # High confidence from human validation
        )
        
        # Link experience to validation
        supabase.table('validation_requests')\
            .update({
                'experience_created': True,
                'experience_id': experience['experience_id']
            })\
            .eq('id', validation_id)\
            .execute()
        
        # Update the source entity if structured data provided
        if updated_information and val_data['entity_type'] == 'internal_resource':
            supabase.table('internal_resources')\
                .update(updated_information)\
                .eq('id', val_data['entity_id'])\
                .execute()
    
    return {
        "success": True,
        "validation_id": validation_id,
        "knowledge_updated": bool(corrections or updated_information)
    }

def extract_keywords(text: str) -> List[str]:
    """Simple keyword extraction - use NLP library for production."""
    # Placeholder - implement with spaCy, RAKE, or LLM extraction
    words = text.lower().split()
    return [w for w in words if len(w) > 4][:10]
```

## Supabase Edge Function for Webhook Processing

Create `supabase/functions/validation-webhook/index.ts`:

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  try {
    const { validation_id, approved, corrections, updated_information } = await req.json()
    
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )
    
    // Update validation request
    const { data: validation } = await supabase
      .from('validation_requests')
      .update({
        validation_status: approved ? 'approved' : 'rejected',
        response_received_at: new Date().toISOString(),
        corrections_provided: corrections,
        response_data: updated_information
      })
      .eq('id', validation_id)
      .select()
      .single()
    
    // If corrections provided, create experience entry
    if (corrections || updated_information) {
      // Generate embedding for the correction
      const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'text-embedding-3-small',
          input: corrections || JSON.stringify(updated_information)
        })
      })
      
      const embeddingData = await embeddingResponse.json()
      const embedding = embeddingData.data[0].embedding
      
      // Insert experience
      const { data: experience } = await supabase
        .from('experience')
        .insert({
          tenant_id: validation.tenant_id,
          description: corrections || 'Updated information from validation',
          keywords: extractKeywords(corrections || ''),
          entity_type: validation.entity_type,
          entity_id: validation.entity_id,
          source_type: 'validation_response',
          confidence_score: 0.95,
          embedding,
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
      
      // Update source entity if needed
      if (updated_information && validation.entity_type === 'internal_resource') {
        await supabase
          .from('internal_resources')
          .update(updated_information)
          .eq('id', validation.entity_id)
      }
    }
    
    return new Response(
      JSON.stringify({ success: true, validation_id }),
      { headers: { 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})

function extractKeywords(text: string): string[] {
  // Simple keyword extraction
  return text
    .toLowerCase()
    .split(/\s+/)
    .filter(w => w.length > 4)
    .slice(0, 10)
}
```

## Background Embedding Generation

Create `supabase/functions/process-embeddings/index.ts`:

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )
  
  // Get pending embedding jobs
  const { data: jobs } = await supabase
    .from('embedding_queue')
    .select('*')
    .eq('status', 'pending')
    .order('priority', { ascending: true })
    .limit(10)
  
  for (const job of jobs || []) {
    try {
      // Mark as processing
      await supabase
        .from('embedding_queue')
        .update({ status: 'processing' })
        .eq('id', job.id)
      
      // Get record content
      const { data: record } = await supabase
        .from(job.table_name)
        .select('description, name, requirements, content')
        .eq('id', job.record_id)
        .single()
      
      // Combine relevant text fields
      const text = [
        record.name,
        record.description,
        record.requirements,
        record.content
      ].filter(Boolean).join(' ')
      
      // Generate embedding
      const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'text-embedding-3-small',
          input: text
        })
      })
      
      const embeddingData = await embeddingResponse.json()
      const embedding = embeddingData.data[0].embedding
      
      // Update record with embedding
      await supabase
        .from(job.table_name)
        .update({ embedding })
        .eq('id', job.record_id)
      
      // Mark job as completed
      await supabase
        .from('embedding_queue')
        .update({ 
          status: 'completed',
          processed_at: new Date().toISOString()
        })
        .eq('id', job.id)
      
    } catch (error) {
      // Mark job as failed
      await supabase
        .from('embedding_queue')
        .update({ 
          status: 'failed',
          error_message: error.message,
          retry_count: job.retry_count + 1
        })
        .eq('id', job.id)
    }
  }
  
  return new Response(
    JSON.stringify({ processed: jobs?.length || 0 }),
    { headers: { 'Content-Type': 'application/json' } }
  )
})
```

## Cron Job Setup for Embedding Processing

In Supabase Dashboard: Database > Extensions > Enable pg_cron

```sql
-- Run embedding processor every 30 seconds
SELECT cron.schedule(
    'process-embeddings',
    '*/30 * * * * *',  -- Every 30 seconds
    $$
    SELECT net.http_post(
        url := 'https://your-project.supabase.co/functions/v1/process-embeddings',
        headers := jsonb_build_object(
            'Authorization', 'Bearer ' || current_setting('app.service_role_key')
        )
    );
    $$
);
```

## Testing the Schema

### 1. Insert Test Data

```sql
-- Insert test internal resource
INSERT INTO internal_resources (
    tenant_id, name, resource_type, description,
    approval_contact_name, approval_contact_email,
    hourly_rate, skills
) VALUES (
    'your-tenant-id'::uuid,
    'Jane Smith',
    'staff',
    'Senior software engineer specializing in Python, FastAPI, and PostgreSQL',
    'Engineering Manager',
    'manager@example.com',
    150.00,
    '{"Python": "expert", "PostgreSQL": "advanced", "FastAPI": "expert"}'::jsonb
);

-- Insert test external resource
INSERT INTO external_resources (
    tenant_id, vendor_name, vendor_type, description,
    approval_status, service_areas
) VALUES (
    'your-tenant-id'::uuid,
    'TechConsulting Inc',
    'Consultant',
    'Technology consulting firm specializing in cloud architecture and AI',
    'approved_vendor',
    ARRAY['Cloud Architecture', 'AI/ML', 'Data Engineering']
);

-- Insert test policy
INSERT INTO policies (
    tenant_id, policy_name, policy_category, description,
    requirements, policy_owner_name, policy_owner_email, tags
) VALUES (
    'your-tenant-id'::uuid,
    'Data Privacy Compliance',
    'Legal',
    'All proposals must ensure GDPR and CCPA compliance',
    'Include data protection measures, consent management, and privacy impact assessment',
    'Legal Counsel',
    'legal@example.com',
    ARRAY['privacy', 'legal', 'compliance', 'GDPR']
);
```

### 2. Test Hybrid Search

```sql
-- Test internal resources search (requires embedding)
SELECT * FROM search_internal_resources(
    'Python developer with database skills',
    '[0.1, 0.2, ...]'::halfvec(1536),  -- Replace with actual embedding
    0.7,
    10,
    'your-tenant-id'::uuid
);
```

## Migration Strategy for Existing Systems

### Phase 1: Schema Deployment (Week 1)
1. Deploy schema to Supabase
2. Set up Auth Hooks for tenant claims
3. Create initial admin users and tenant mappings

### Phase 2: Data Migration (Week 2)
1. Export existing resource data
2. Transform to new schema format
3. Import with batch INSERT statements
4. Generate embeddings for all records

### Phase 3: FastMCP Server (Week 3)
1. Build core search and retrieval tools
2. Implement proposal generation tool
3. Test with Claude Desktop

### Phase 4: Validation Workflow (Week 4)
1. Implement validation request creation
2. Set up email/Teams integration
3. Create webhook handlers
4. Test feedback loop

### Phase 5: Production Rollout (Week 5)
1. Set up monitoring and alerts
2. Enable production authentication
3. Train users on validation workflows
4. Monitor AI learning and audit logs

## Security Checklist

- [ ] RLS policies enabled on all tables
- [ ] Service role key secured (never in client code)
- [ ] Auth Hook deployed for tenant claims
- [ ] API rate limiting configured
- [ ] Audit logging enabled
- [ ] Webhook endpoints authenticated
- [ ] SSL/TLS for all connections
- [ ] Backup strategy configured

## Performance Optimization

### Recommended Indexes Created by Schema
✅ HNSW indexes for vector similarity
✅ GIN indexes for full-text search
✅ B-tree indexes for foreign keys
✅ Composite indexes for common queries

### Query Optimization Tips
- Use `select('column1, column2')` instead of `select('*')`
- Leverage materialized views for complex aggregations
- Use batch operations for bulk inserts
- Enable connection pooling in production

## Monitoring Queries

```sql
-- Check embedding queue backlog
SELECT status, COUNT(*) 
FROM embedding_queue 
GROUP BY status;

-- Active validation requests
SELECT * FROM active_validations;

-- Recent AI experience entries
SELECT * FROM experience 
WHERE created_by = 'ai' 
ORDER BY created_at DESC 
LIMIT 20;

-- Audit trail for specific entity
SELECT * FROM audit_log 
WHERE table_name = 'experience' 
AND record_id = 'specific-id'::uuid
ORDER BY changed_at DESC;
```

## Next Steps

1. **Test the schema** with sample data
2. **Build the FastMCP server** using the integration patterns
3. **Set up webhook handlers** for validation responses
4. **Configure cron jobs** for embedding generation
5. **Deploy to production** following the migration strategy

This schema provides a solid foundation for a self-improving AI knowledge base that genuinely learns from validation cycles while maintaining security, multi-tenancy, and performance.
