# Proposal Generation MCP Server

A self-updating MCP server that combines FastMCP with Supabase to create an AI-powered proposal generation system with validation workflows and automatic knowledge updates.

## Features

- **Hybrid Search**: Combines semantic (pgvector) and keyword (full-text) search for 30-40% better recall
- **Self-Updating Knowledge Base**: AI learns from validation feedback and records learnings directly
- **Single-Tenant Deployment**: One Supabase project per client for complete data isolation
- **Validation Workflows**: Teams Adaptive Cards and email-based validation with AI processing
- **Background Tasks**: Long-running proposal generation with progress reporting
- **Audit Trail**: Complete tracking of all AI updates and changes
- **Manual Review Gate**: Unvalidated experiences go to review queue before appearing in search

## Architecture

```
AI Clients (Claude, Cursor, ChatGPT)
    ↓ MCP Protocol
FastMCP Server (Python)
    ↓ Direct Queries
Supabase (PostgreSQL + pgvector)
    ↓ Webhooks
Edge Functions (TypeScript) - Simple response storage
```

**Key Simplifications:**
- No multi-tenant complexity - each client gets their own Supabase project
- No embedding queue - embeddings generated synchronously (<1 second)
- AI-first processing - AI reads validation responses and calls `record_experience()` directly
- Simple webhooks - just store raw responses, AI does the semantic work

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Supabase project with PostgreSQL (one per client)
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

**Note**: This is a single-tenant schema. Each client should get their own Supabase project.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file with your credentials:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Email Configuration (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
EMAIL_FROM=proposals@yourcompany.com

# Teams Configuration (optional)
TEAMS_ACCESS_TOKEN=your-teams-access-token
TEAMS_WEBHOOK_SECRET=your-teams-webhook-secret

# Server Configuration
STATELESS_HTTP=true
```

### 5. Deploy Edge Functions

Deploy the Supabase Edge Functions (simplified - just store responses):

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
```

**Note**: The `process-embeddings` function is no longer needed - embeddings are generated synchronously.

### 6. Set Environment Variables for Functions

```bash
supabase secrets set TEAMS_WEBHOOK_SECRET=your-secret
```

### 7. Run the Server

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
- `search_experience` - Search AI knowledge base for past learnings (only validated experiences)

### Knowledge Management

- `record_experience` - Record learned facts and knowledge updates. AI provides description, embeddings generated synchronously.

### Proposal Generation

- `parse_rfp` - Parse RFP documents and extract requirements
- `generate_proposal` - Generate complete proposals with resource allocation

### Validation

- `send_teams_validation` - Send validation requests via Teams Adaptive Cards
- `send_email_validation` - Send validation requests via email
- `process_validation_response` - Store raw validation responses (AI processes them)

## Validation Workflow (AI-First)

1. **Proposal Generation**: AI generates proposal and identifies resources needed
2. **Validation Request**: System sends validation requests via Teams or email
3. **Response Collection**: Recipients respond with approvals or corrections
4. **Webhook Storage**: Edge functions store raw response data in `validation_requests` table
5. **AI Processing**: AI reads the response and calls `record_experience()` with:
   - Clear description of what changed
   - Confidence score
   - Entity associations
   - Embedding generated synchronously
6. **Review Queue**: New experiences go to review queue (`is_validated = false`)
7. **Manual Approval**: Admin reviews and approves experiences
8. **Search Integration**: Approved experiences appear in search results

## Deployment Model

**Single-Tenant Per Client:**

Each client gets:
- Their own Supabase project
- Their own database instance
- Their own MCP server deployment
- Complete data isolation at infrastructure level

**Benefits:**
- Zero tenant-related bugs
- Client-specific customization possible
- Simple backups (one database per client)
- Clear cost per client
- No RLS complexity needed

## Security

- **Physical Isolation**: Each client has separate Supabase project
- **Service Role Keys**: Never exposed to clients, only used server-side
- **Webhook Validation**: Teams webhooks validate signatures
- **Manual Review Gate**: Unvalidated experiences don't appear in search

## Performance

- **HNSW Indexes**: Fast approximate nearest neighbor search for embeddings
- **GIN Indexes**: Efficient full-text search
- **Hybrid Search**: Combines semantic and keyword search for best results
- **Synchronous Embeddings**: Generated in <1 second during `record_experience()` call

## Monitoring

Query active validations:

```sql
SELECT * FROM active_validations;
```

View pending reviews:

```sql
SELECT * FROM pending_reviews;
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

Embeddings are generated synchronously in `record_experience()`. If they fail:
1. Verify OpenAI API key is set correctly
2. Check network connectivity to OpenAI API
3. Review error messages in tool responses

### Validation Not Working

1. Verify SMTP/Teams credentials in `.env`
2. Check Edge Function logs for webhook errors
3. Ensure validation tokens are stored correctly

### Search Returns No Results

1. Verify experiences have been created and validated (`is_validated = true`)
2. Check that embeddings were generated (should be automatic)
3. Lower `match_threshold` parameter if needed
4. Use `pending_reviews` view to see unvalidated experiences

## License

MIT
