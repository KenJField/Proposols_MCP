# Prototype Launch Checklist

Use this checklist to ensure the Proposal MCP Server is ready for prototype use.

## Pre-Launch Setup

### 1. Database Setup
- [ ] Database schema deployed to Supabase
- [ ] All migrations applied successfully
- [ ] Extensions enabled (vector, pg_trgm, etc.)
- [ ] All tables created and accessible
- [ ] Indexes created (HNSW, GIN, etc.)
- [ ] RLS policies enabled on all tables
- [ ] Search functions (`search_internal_resources`, `search_experience`) exist
- [ ] Views created (`active_validations`, `proposal_resources`, etc.)

### 2. Authentication Setup
- [ ] `user_tenants` table created
- [ ] Auth Hook function `custom_access_token_hook` created
- [ ] Auth Hook enabled in Supabase Dashboard
- [ ] Test user created in Supabase Auth
- [ ] Test user added to `user_tenants` table
- [ ] JWT contains `tenant_id` claim (verify with test token)

### 3. Edge Functions
- [ ] `process-embeddings` function deployed
- [ ] `validation-webhook` function deployed
- [ ] `validation-response` function deployed
- [ ] Edge Function secrets configured:
  - [ ] `OPENAI_API_KEY`
  - [ ] `TEAMS_WEBHOOK_SECRET` (if using Teams)
- [ ] Edge Functions are ACTIVE status

### 4. Cron Job
- [ ] `pg_cron` extension enabled
- [ ] `http` extension enabled (if needed)
- [ ] Cron job scheduled for embedding processing
- [ ] Cron job URL points to correct Edge Function
- [ ] Service role key accessible to cron job

### 5. Configuration
- [ ] Environment variables set:
  - [ ] `SUPABASE_URL`
  - [ ] `SUPABASE_SERVICE_ROLE_KEY`
  - [ ] `OPENAI_API_KEY`
  - [ ] `OPENAI_EMBEDDING_MODEL` (optional, defaults to text-embedding-3-small)
  - [ ] `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` (if using email validation)
  - [ ] `TEAMS_ACCESS_TOKEN`, `TEAMS_WEBHOOK_SECRET` (if using Teams)
- [ ] Configuration validation passes: `python -c "from src.config import Config; Config.validate()"`

## Testing

### 6. Unit Tests
- [ ] All unit tests pass: `pytest tests/unit/ -v`
- [ ] No import errors
- [ ] Mocked dependencies work correctly

### 7. Integration Tests
- [ ] Database connection test passes
- [ ] Table existence test passes
- [ ] Function existence test passes
- [ ] Integration tests: `pytest tests/integration/ -v -m integration`

### 8. Deployment Validation
- [ ] Run: `python scripts/validate_deployment.py`
- [ ] All checks pass
- [ ] No missing tables or functions
- [ ] Embedding queue is operational

### 9. Test Data
- [ ] Load test data: `python scripts/load_test_data.py`
- [ ] Test data loads without errors
- [ ] Wait 1-2 minutes for embeddings to generate
- [ ] Verify embeddings are populated:
  ```sql
  SELECT COUNT(*) FROM internal_resources WHERE embedding IS NOT NULL;
  SELECT COUNT(*) FROM experience WHERE embedding IS NOT NULL;
  ```

### 10. Functional Tests
- [ ] Search tools work: `python scripts/test_mcp_tools.py`
- [ ] `search_internal_resources` returns results
- [ ] `search_experience` returns results
- [ ] `record_experience` creates entries
- [ ] Embeddings are generated for new entries

## MCP Server

### 11. Server Startup
- [ ] Server starts without errors: `python -m src.server`
- [ ] No configuration errors
- [ ] All tools are registered
- [ ] Authentication provider initialized

### 12. MCP Client Connection
- [ ] Configure MCP client (Claude Desktop, Cursor, etc.)
- [ ] Server connects successfully
- [ ] Tools are discoverable
- [ ] Can call tools without errors

### 13. Tool Functionality
- [ ] `search_internal_resources_tool` works
- [ ] `search_experience_tool` works
- [ ] `record_experience_tool` works
- [ ] `parse_rfp_tool` works
- [ ] `generate_proposal_tool` works (with test data)
- [ ] `send_email_validation_tool` works (if SMTP configured)
- [ ] `process_validation_response_tool` works

## Validation Workflow

### 14. Validation Flow
- [ ] Can create validation requests
- [ ] Email validation sends successfully (if configured)
- [ ] Teams validation sends successfully (if configured)
- [ ] Validation response form accessible
- [ ] Responses are processed correctly
- [ ] Experience entries created from corrections
- [ ] Knowledge base updates automatically

### 15. Self-Updating Loop
- [ ] Validation response creates experience entry
- [ ] Experience entry gets embedding
- [ ] Updated knowledge appears in future searches
- [ ] Audit log records changes

## Performance

### 16. Performance Checks
- [ ] Search queries complete in < 500ms
- [ ] Embedding generation processes within 30 seconds
- [ ] No database connection timeouts
- [ ] Edge Functions respond in < 5 seconds

## Security

### 17. Security Validation
- [ ] RLS policies prevent cross-tenant access
- [ ] JWT validation works correctly
- [ ] Service role key not exposed to clients
- [ ] Webhook validation in place (if using Teams)

## Documentation

### 18. Documentation
- [ ] README.md is up to date
- [ ] TEST_PLAN.md is complete
- [ ] README_TESTING.md is available
- [ ] DEPLOYMENT.md has correct instructions
- [ ] Environment variables documented

## Known Issues

Document any known issues or limitations:

- [ ] Issue 1: _________________
- [ ] Issue 2: _________________
- [ ] Issue 3: _________________

## Sign-Off

**Ready for Prototype Use:**
- [ ] All critical items (1-13) completed
- [ ] All important items (14-17) completed or documented
- [ ] Known issues documented
- [ ] Team notified

**Completed by:** _________________  
**Date:** _________________  
**Approved by:** _________________

## Next Steps After Prototype

1. Monitor system performance
2. Collect user feedback
3. Address known issues
4. Plan production improvements
5. Scale infrastructure as needed
