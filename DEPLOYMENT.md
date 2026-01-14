# Deployment Guide

## Deployment Model

This system uses a **single-tenant deployment model**: each client gets their own Supabase project and MCP server instance. This eliminates multi-tenant complexity while providing complete data isolation.

## Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Email Configuration (for email-based validation)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
EMAIL_FROM=proposals@yourcompany.com

# Teams Configuration (optional, for Teams-based validation)
TEAMS_ACCESS_TOKEN=your-teams-access-token
TEAMS_WEBHOOK_SECRET=your-teams-webhook-secret

# Server Configuration
STATELESS_HTTP=true
```

## Database Deployment Steps

### 1. Create Supabase Project

For each client, create a new Supabase project:
- Go to https://supabase.com
- Create new project
- Note the project URL and service role key

### 2. Apply Schema

Apply the schema to your Supabase project:

```bash
# Using Supabase CLI
supabase db reset --db-url "postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres"

# Or apply directly via psql
psql -h db.your-project.supabase.co -U postgres -d postgres -f proposal_mcp_schema.sql
```

**Important**: This schema is single-tenant. No RLS policies, no tenant_id columns, no auth hooks needed.

### 3. Verify Schema

Check that tables were created:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

You should see:
- `internal_resources`
- `external_resources`
- `policies`
- `experience`
- `validation_requests`
- `proposals`
- `rfps`
- `audit_log`

**Note**: `embedding_queue` table is NOT created (removed in simplified architecture).

## Edge Functions Deployment

### 1. Install Supabase CLI

```bash
npm install -g supabase
```

### 2. Login and Link Project

```bash
supabase login
supabase link --project-ref your-project-ref
```

### 3. Deploy Functions

```bash
# Deploy validation webhook (for Teams)
supabase functions deploy validation-webhook

# Deploy validation response handler (for email)
supabase functions deploy validation-response
```

**Note**: `process-embeddings` function is no longer needed - embeddings are generated synchronously in `record_experience()`.

### 4. Set Environment Variables for Functions

```bash
supabase secrets set TEAMS_WEBHOOK_SECRET=your-secret
```

## Per-Client Deployment

For each new client:

1. **Create Supabase Project**
   ```bash
   # Create project via Supabase dashboard or CLI
   supabase projects create client-name
   ```

2. **Apply Schema**
   ```bash
   psql -h db.[client-project].supabase.co -U postgres -d postgres -f proposal_mcp_schema.sql
   ```

3. **Deploy Edge Functions**
   ```bash
   supabase link --project-ref [client-project-ref]
   supabase functions deploy validation-webhook
   supabase functions deploy validation-response
   ```

4. **Create Client-Specific .env**
   ```bash
   # client-acme/.env
   SUPABASE_URL=https://acme-proposals.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=acme_key_here
   OPENAI_API_KEY=shared_or_dedicated
   ```

5. **Deploy MCP Server**
   ```bash
   # Deploy to your hosting platform (Fly.io, Railway, etc.)
   # Or run locally with client-specific .env
   python -m src.server
   ```

## Testing

### 1. Test Database Connection

```python
from src.config import Config
from supabase import create_client

Config.validate()
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
print("Connected successfully!")
```

### 2. Test Search Function

```sql
-- Insert test data first, then:
SELECT * FROM search_internal_resources(
    'Python developer',
    '[0.1, 0.2, ...]'::halfvec(1536),
    0.7,
    10
);
```

### 3. Test MCP Server

```bash
python -m src.server
```

### 4. Test Experience Recording

Use the MCP tool `record_experience`:

```python
# Via MCP client
await record_experience(
    description="Test learning",
    entity_id="test-id",
    confidence=0.9,
    requires_review=True
)
```

Check that:
- Experience was created
- Embedding was generated (check `embedding` column is not null)
- `is_validated` is `false` (goes to review queue)

### 5. Test Validation Workflow

1. Create a validation request
2. Send via Teams or email
3. Submit response via webhook
4. Verify response stored in `validation_requests.response_data`
5. AI should read response and call `record_experience()`

## Production Checklist

- [ ] All environment variables configured
- [ ] Database schema applied
- [ ] Edge functions deployed
- [ ] MCP client configured (Claude Desktop, Cursor, etc.)
- [ ] SMTP/Teams credentials verified
- [ ] Test data loaded
- [ ] Search functions tested
- [ ] Validation workflow tested end-to-end
- [ ] Review queue accessible (via `pending_reviews` view)
- [ ] Backup strategy configured (Supabase automatic backups)
- [ ] Monitoring queries tested

## Monitoring

### Check Active Validations

```sql
SELECT * FROM active_validations;
```

### Check Pending Reviews

```sql
SELECT * FROM pending_reviews;
```

### Check Recent AI Learnings

```sql
SELECT * FROM experience 
WHERE created_by = 'ai' 
ORDER BY created_at DESC 
LIMIT 20;
```

### Check Validation Response Status

```sql
SELECT 
    id,
    validation_status,
    response_received_at,
    corrections_provided IS NOT NULL as has_corrections
FROM validation_requests
WHERE validation_status IN ('sent', 'updated', 'approved')
ORDER BY response_received_at DESC;
```

## Troubleshooting

### Embeddings Not Generating

Embeddings are generated synchronously in `record_experience()`. If they fail:
1. Check OpenAI API key is correct
2. Verify network connectivity
3. Check OpenAI API status
4. Review error messages in tool responses

### Validation Webhooks Not Working

1. Check Edge Function logs in Supabase Dashboard
2. Verify `TEAMS_WEBHOOK_SECRET` is set correctly
3. Test webhook endpoint directly
4. Check `validation_requests` table for stored responses

### Search Returns No Results

1. Verify experiences exist: `SELECT COUNT(*) FROM experience;`
2. Check if experiences are validated: `SELECT COUNT(*) FROM experience WHERE is_validated = true;`
3. Verify embeddings exist: `SELECT COUNT(*) FROM experience WHERE embedding IS NOT NULL;`
4. Lower `match_threshold` in search calls
5. Check `pending_reviews` view for unvalidated experiences

## Migration from Multi-Tenant (If Applicable)

If you have existing multi-tenant data:

1. **Export per-tenant data** from old database
2. **Create new Supabase project** for each tenant
3. **Apply simplified schema** to each project
4. **Import tenant data** (without tenant_id columns)
5. **Regenerate embeddings** via `record_experience()` calls
6. **Deploy client-specific MCP servers**

## Backup and Recovery

Supabase provides automatic backups. For additional safety:

1. **Database Backups**: Supabase daily backups (configurable)
2. **Manual Exports**: Use `pg_dump` for client-specific backups
3. **Data Exports**: Export critical tables (experience, validation_requests) periodically

```bash
# Export experience table
pg_dump -h db.your-project.supabase.co -U postgres -d postgres \
  -t experience --data-only > experience_backup.sql
```
