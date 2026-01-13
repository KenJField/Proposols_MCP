# Proposal Generation MCP Server

A self-updating MCP server that combines FastMCP with Supabase to create an AI-powered proposal generation system with validation workflows and automatic knowledge updates.

## Features

- **Hybrid Search**: Combines semantic (pgvector) and keyword (full-text) search for 30-40% better recall
- **Self-Updating Knowledge Base**: Learns from validation feedback and automatically updates embeddings
- **Multi-Tenant Isolation**: Row Level Security (RLS) ensures data isolation per tenant
- **Validation Workflows**: Teams Adaptive Cards and email-based validation with automatic knowledge updates
- **Background Tasks**: Long-running proposal generation with progress reporting
- **Audit Trail**: Complete tracking of all AI updates and changes

## Architecture

```
AI Clients (Claude, Cursor, ChatGPT)
    ↓ MCP Protocol
FastMCP Server (Python)
    ↓ Authenticated Queries
Supabase (PostgreSQL + pgvector)
    ↓ Webhooks
Edge Functions (TypeScript)
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Supabase project with PostgreSQL
- OpenAI API key
- (Optional) SMTP server for email validation
- (Optional) Microsoft Teams app for Teams validation

### 2. Database Setup

Apply the schema to your Supabase project:

```bash
# Using Supabase CLI
supabase db reset --db-url "postgresql://..."

# Or apply directly via psql
psql -h db.your-project.supabase.co -U postgres -d postgres -f proposal_mcp_schema.sql
```

### 3. Set Up Auth Hooks

Create an Auth Hook in Supabase Dashboard (Authentication > Hooks) to inject `tenant_id` into JWTs:

```sql
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    claims jsonb;
    user_tenant_id uuid;
BEGIN
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

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values.

### 6. Deploy Edge Functions

Deploy the Supabase Edge Functions:

```bash
# Install Supabase CLI if not already installed
npm install -g supabase

# Login to Supabase
supabase login

# Link your project
supabase link --project-ref your-project-ref

# Deploy functions
supabase functions deploy validation-webhook
supabase functions deploy validation-response
supabase functions deploy process-embeddings
```

### 7. Set Up Cron Job for Embeddings

In Supabase Dashboard, enable `pg_cron` extension and create a cron job:

```sql
-- Enable pg_cron
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule embedding processing every 30 seconds
SELECT cron.schedule(
    'process-embeddings',
    '*/30 * * * * *',
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

### 8. Run the Server

```bash
python -m src.server
```

Or for development:

```bash
fastmcp dev src.server:app
```

## MCP Client Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "proposal-knowledge-base": {
      "command": "python",
      "args": ["-m", "src.server"],
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "your-key",
        "OPENAI_API_KEY": "your-key"
      }
    }
  }
}
```

### Cursor IDE

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "proposal-knowledge-base": {
      "command": "python",
      "args": ["-m", "src.server"],
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "your-key",
        "OPENAI_API_KEY": "your-key"
      }
    }
  }
}
```

## Available Tools

### Search Tools

- `search_internal_resources` - Search company resources (staff, tools, assets)
- `search_experience` - Search AI knowledge base for past learnings

### Knowledge Management

- `record_experience` - Record learned facts and knowledge updates

### Proposal Generation

- `parse_rfp` - Parse RFP documents and extract requirements
- `generate_proposal` - Generate complete proposals with resource allocation

### Validation

- `send_teams_validation` - Send validation requests via Teams Adaptive Cards
- `send_email_validation` - Send validation requests via email
- `process_validation_response` - Process validation responses and update knowledge

## Validation Workflow

1. **Proposal Generation**: AI generates proposal and identifies resources needed
2. **Validation Request**: System sends validation requests via Teams or email
3. **Response Collection**: Recipients respond with approvals or corrections
4. **Knowledge Update**: Corrections automatically create experience entries with embeddings
5. **Future Improvement**: Updated knowledge improves future proposal generation

## Security

- **Row Level Security (RLS)**: All tables enforce tenant isolation
- **JWT Authentication**: FastMCP validates Supabase JWTs
- **Service Role Keys**: Never exposed to clients, only used server-side
- **Webhook Validation**: Teams webhooks validate signatures

## Performance

- **HNSW Indexes**: Fast approximate nearest neighbor search for embeddings
- **GIN Indexes**: Efficient full-text search
- **Hybrid Search**: Combines semantic and keyword search for best results
- **Background Processing**: Embeddings generated asynchronously

## Monitoring

Query active validations:

```sql
SELECT * FROM active_validations;
```

Check embedding queue status:

```sql
SELECT status, COUNT(*) 
FROM embedding_queue 
GROUP BY status;
```

View recent AI learnings:

```sql
SELECT * FROM experience 
WHERE created_by = 'ai' 
ORDER BY created_at DESC 
LIMIT 20;
```

## Troubleshooting

### Embeddings Not Generating

1. Check `embedding_queue` table for failed jobs
2. Verify OpenAI API key is set correctly
3. Check Edge Function logs in Supabase Dashboard

### Validation Not Working

1. Verify SMTP/Teams credentials in `.env`
2. Check Edge Function logs for webhook errors
3. Ensure validation tokens are stored correctly

### Search Returns No Results

1. Verify embeddings have been generated for your data
2. Check that `tenant_id` is correctly set in JWT claims
3. Lower `match_threshold` parameter if needed

## License

MIT
