# Deployment Guide

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

1. **Apply Schema**
   ```bash
   psql -h db.your-project.supabase.co -U postgres -d postgres -f proposal_mcp_schema.sql
   ```

2. **Create User-Tenant Mapping Table**
   ```sql
   CREATE TABLE user_tenants (
       user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
       tenant_id UUID NOT NULL,
       role TEXT DEFAULT 'member',
       PRIMARY KEY (user_id, tenant_id)
   );
   
   ALTER TABLE user_tenants ENABLE ROW LEVEL SECURITY;
   
   CREATE POLICY "Users can view their own tenants" ON user_tenants
       FOR SELECT TO authenticated
       USING (user_id = auth.uid());
   ```

3. **Set Up Auth Hook**
   - Go to Supabase Dashboard > Authentication > Hooks
   - Create a new hook with the function from `implementation_guide.md`

## Edge Functions Deployment

1. **Install Supabase CLI**
   ```bash
   npm install -g supabase
   ```

2. **Login and Link Project**
   ```bash
   supabase login
   supabase link --project-ref your-project-ref
   ```

3. **Deploy Functions**
   ```bash
   supabase functions deploy validation-webhook
   supabase functions deploy validation-response
   supabase functions deploy process-embeddings
   ```

4. **Set Environment Variables for Functions**
   ```bash
   supabase secrets set OPENAI_API_KEY=your-key
   supabase secrets set TEAMS_WEBHOOK_SECRET=your-secret
   ```

## Cron Job Setup

Enable `pg_cron` extension and schedule embedding processing:

```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;

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

## Testing

1. **Test Database Connection**
   ```python
   from src.config import Config
   from supabase import create_client
   
   Config.validate()
   supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
   print("Connected successfully!")
   ```

2. **Test Search Function**
   ```sql
   -- Insert test data first, then:
   SELECT * FROM search_internal_resources(
       'Python developer',
       '[0.1, 0.2, ...]'::halfvec(1536),
       0.7,
       10
   );
   ```

3. **Test MCP Server**
   ```bash
   python -m src.server
   ```

## Production Checklist

- [ ] All environment variables configured
- [ ] Database schema applied
- [ ] RLS policies enabled and tested
- [ ] Auth hooks configured
- [ ] Edge functions deployed
- [ ] Cron job scheduled
- [ ] MCP client configured (Claude Desktop, Cursor, etc.)
- [ ] SMTP/Teams credentials verified
- [ ] Monitoring queries tested
- [ ] Backup strategy configured
