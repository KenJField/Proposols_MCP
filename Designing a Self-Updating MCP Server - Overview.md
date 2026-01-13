# Designing a Self-Updating MCP Server for Proposal Generation

A properly architected MCP server combining **FastMCP with Supabase** can create a self-improving knowledge base that learns from validation feedback loops. The key insight: FastMCP 2.14's native Supabase authentication, background tasks, and elicitation features align directly with the validation workflow requirements, while Supabase's real-time subscriptions and database triggers enable the automatic knowledge updating loop. This architecture transforms static company capability databases into living knowledge systems that improve with each proposal generated.

## Native FastMCP + Supabase integration enables seamless database access

FastMCP provides **first-party Supabase support** through its `SupabaseProvider` authentication class, eliminating custom integration work. The provider handles JWT verification via Supabase's JWKS endpoint, enabling Row Level Security (RLS) policies to automatically filter data by tenant.

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.supabase import SupabaseProvider

auth = SupabaseProvider(
    project_url="https://your-project.supabase.co",
    algorithm="RS256",  # Recommended for production
    required_scopes=["read", "write"]
)

mcp = FastMCP(name="ProposalKnowledgeBase", auth=auth)
```

For multi-tenant isolation, Supabase's Auth Hooks can inject custom JWT claims containing `tenant_id` and role information. RLS policies then reference these claims directly:

```sql
CREATE POLICY "Tenant isolation" ON company_resources
FOR ALL TO authenticated
USING (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);
```

FastMCP's **pluggable storage backends** (introduced in 2.13) handle persistent state across requests using Redis, DynamoDB, or filesystem storage. This enables workflow state tracking without custom database tables—critical for multi-step validation processes spanning hours or days.

## Hybrid search architecture powers intelligent capability matching

For proposal generation requiring semantic understanding of company capabilities, implement Supabase's **hybrid search pattern** combining full-text search with pgvector embeddings. This approach yields **30-40% better recall** than either method alone for capability-matching queries.

```sql
CREATE TABLE capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  content TEXT NOT NULL,
  fts TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  embedding HALFVEC(1536),  -- 16-bit precision saves 50% storage
  validation_status TEXT DEFAULT 'pending',
  last_validated_at TIMESTAMPTZ
);

CREATE INDEX idx_capabilities_embedding ON capabilities 
  USING hnsw (embedding halfvec_cosine_ops);
CREATE INDEX idx_capabilities_fts ON capabilities USING gin(fts);
```

The hybrid search function uses Reciprocal Rank Fusion (RRF) to blend keyword and semantic results, callable directly from FastMCP tools via Supabase's RPC interface.

## Background tasks with elicitation handle multi-step validation workflows

FastMCP 2.14's **Background Tasks (SEP-1686)** enable long-running validation processes that report progress without blocking the AI assistant. Combined with **Elicitation (SEP-1330)** for human-in-the-loop approval, the server can orchestrate complete validation cycles:

```python
@mcp.tool(task=True)  # Enables background execution
async def validate_capability(
    capability_id: str, 
    validation_method: str,
    ctx: Context
) -> str:
    """Trigger validation workflow for a capability."""
    
    await ctx.report_progress(0, 100, "Initiating validation")
    capability = await db.get_capability(capability_id)
    
    # Stage 1: Send validation request
    await ctx.report_progress(25, 100, "Sending validation request")
    if validation_method == "teams":
        await send_teams_adaptive_card(capability)
    else:
        await send_email_validation(capability)
    
    # Stage 2: Request confirmation from user
    await ctx.report_progress(50, 100, "Awaiting confirmation")
    result = await ctx.elicit(
        "Confirm validation was sent to the correct person",
        response_type={"confirmed": bool, "corrections": str}
    )
    
    if result.action == "accept" and result.data.get("corrections"):
        await queue_capability_update(capability_id, result.data["corrections"])
    
    return f"Validation workflow initiated for {capability_id}"
```

For webhook-based validation responses (email replies, Teams card actions), Supabase Database Webhooks trigger Edge Functions that update the knowledge base:

```typescript
// supabase/functions/process-validation-response/index.ts
Deno.serve(async (req) => {
  const { capability_id, validated, corrections } = await req.json()
  
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )
  
  if (corrections) {
    // AI processes corrections and updates capability
    const updated_content = await processCorrections(corrections)
    await supabase.from('capabilities')
      .update({ content: updated_content, validation_status: 'updated' })
      .eq('id', capability_id)
  }
  
  return new Response(JSON.stringify({ success: true }))
})
```

## The self-updating feedback loop requires automatic embedding regeneration

The knowledge base must regenerate embeddings automatically when capabilities are updated. Supabase's **pgmq + pg_cron pattern** queues embedding jobs for background processing every 10 seconds:

```sql
-- Trigger to queue embedding regeneration on updates
CREATE OR REPLACE FUNCTION queue_embedding_job()
RETURNS TRIGGER AS $$
BEGIN
  PERFORM pgmq.send(
    'embedding_jobs',
    jsonb_build_object('id', NEW.id, 'table', TG_TABLE_NAME)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_capability_update
AFTER INSERT OR UPDATE OF content ON capabilities
FOR EACH ROW EXECUTE FUNCTION queue_embedding_job();
```

FastMCP's **notification system** automatically informs connected clients when resources change—the AI assistant receives `notifications/resources/list_changed` when capabilities are updated, enabling it to refetch current data for subsequent proposals.

## Existing MCP servers accelerate Teams and email integration

Several production-ready MCP servers eliminate custom integration work:

- **@floriscornel/teams-mcp**: Full Microsoft Graph API integration with OAuth 2.0, rich message formatting, and Adaptive Cards support—ideal for sending structured validation requests
- **mcp-email-server**: IMAP/SMTP integration supporting multiple accounts and attachment handling for email-based validation
- **dbhub**: Zero-dependency database connector supporting PostgreSQL, MySQL, and SQLite with token-efficient queries

For Adaptive Cards-based validation in Teams, the pattern uses `Action.Execute` with user-specific views:

```json
{
  "type": "AdaptiveCard",
  "version": "1.4",
  "refresh": {
    "action": { "type": "Action.Execute", "verb": "validateCapability" },
    "userIds": ["<reviewer-id>"]
  },
  "body": [
    { "type": "TextBlock", "text": "Capability Validation Request" },
    { "type": "ActionSet", "actions": [
      { "type": "Action.Execute", "title": "Confirm Accurate", "verb": "approve" },
      { "type": "Action.Execute", "title": "Submit Corrections", "verb": "correct" }
    ]}
  ]
}
```

## RFP parsing with LlamaParse extracts structured requirements

For processing incoming RFPs, **LlamaParse** provides superior table extraction and custom parsing instructions compared to alternatives. A dedicated FastMCP tool handles document ingestion:

```python
from llama_cloud_services import LlamaParse

@mcp.tool
async def parse_rfp(document_url: str, ctx: Context) -> dict:
    """Parse RFP document and extract structured requirements."""
    parser = LlamaParse(
        api_key=os.environ["LLAMAPARSE_API_KEY"],
        result_type="markdown",
        parsing_instruction="Extract requirements, deadlines, and budget constraints"
    )
    
    result = await parser.aparse(document_url)
    
    # Store parsed requirements for proposal generation
    await ctx.report_progress(80, 100, "Storing parsed requirements")
    rfp_id = await db.store_parsed_rfp(result.text, result.metadata)
    
    return {"rfp_id": rfp_id, "requirements": extract_requirements(result)}
```

## Multi-assistant deployment requires stateless HTTP transport

For production deployments serving Claude, ChatGPT, Cursor, and other clients, **stateless HTTP mode** ensures horizontal scaling works correctly:

```python
mcp = FastMCP("ProposalServer", stateless_http=True)

# Production authentication with Redis storage
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

auth = SupabaseProvider(
    project_url=os.environ["SUPABASE_URL"],
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    client_storage=FernetEncryptionWrapper(
        key_value=RedisStore(host="redis.internal"),
        fernet=Fernet(os.environ["ENCRYPTION_KEY"])
    )
)
```

Each AI assistant connects via different configuration patterns:

| Assistant | Configuration | Transport |
|-----------|--------------|-----------|
| Claude Desktop | `claude_desktop_config.json` | STDIO or HTTP |
| ChatGPT | Custom GPT Actions | Remote HTTP |
| Cursor | `.cursor/mcp.json` | STDIO/HTTP |
| VSCode Copilot | `.vscode/mcp.json` | HTTP |

## Recommended architecture combines all components

The complete system architecture layers FastMCP, Supabase, and workflow orchestration:

```
┌─────────────────────────────────────────────────────────────┐
│              AI Assistants (Claude, ChatGPT, Cursor)        │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol (Streamable HTTP)
┌────────────────────────▼────────────────────────────────────┐
│                   FastMCP Server                            │
│  Tools: search_capabilities, generate_proposal,             │
│         validate_capability, update_from_validation         │
│  Middleware: Auth (Supabase), Caching, Rate Limiting       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      Supabase                               │
│  PostgreSQL + pgvector (capabilities, skills, rates)        │
│  RLS (multi-tenant isolation)                               │
│  Realtime (change notifications)                            │
│  Edge Functions (validation processing)                     │
│  Database Webhooks (external triggers)                      │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
    ┌─────────▼─────────┐          ┌──────────▼──────────┐
    │   Teams MCP       │          │    Email Server     │
    │  (Adaptive Cards) │          │   (SMTP/Webhooks)   │
    └───────────────────┘          └─────────────────────┘
```

## Implementation priorities for maximum impact

Start with these high-value components in order:

1. **Supabase schema with RLS** for multi-tenant capability storage—this foundation enables everything else
2. **Hybrid search function** combining pgvector embeddings with full-text search for capability matching
3. **Core FastMCP tools** for searching capabilities and generating proposal drafts
4. **Validation workflow** using background tasks and Teams/email integration
5. **Automatic embedding regeneration** via database triggers to keep knowledge current

The feedback loop closes when validation responses flow back through Supabase webhooks, triggering Edge Functions that update capabilities and regenerate embeddings. The AI assistant receives change notifications and incorporates improved knowledge into subsequent proposals—creating a system that genuinely improves with each use cycle.