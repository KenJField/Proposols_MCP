# Proposal MCP Server - Test Plan

## Overview

This document outlines the comprehensive test plan for validating the Proposal MCP Server deployment and ensuring all components work correctly in a single-tenant architecture.

## Test Categories

### 1. Unit Tests

Run unit tests to validate individual components:

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_config.py -v
pytest tests/unit/test_keywords.py -v
pytest tests/unit/test_embeddings.py -v
pytest tests/unit/test_email.py -v
```

**Expected Results:**
- All unit tests should pass
- No import errors
- Mocked dependencies work correctly

### 2. Integration Tests

Run integration tests (requires Supabase connection):

```bash
# Set environment variables first
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-key"
export OPENAI_API_KEY="your-key"

# Run integration tests
pytest tests/integration/ -v -m integration
```

**Expected Results:**
- Database connection successful
- Tables accessible
- Functions exist and are callable
- Views exist (pending_reviews)

### 3. Deployment Validation

Run the deployment validation script:

```bash
python scripts/validate_deployment.py
```

**Checklist:**
- [ ] All required tables exist
- [ ] Database functions are available
- [ ] Edge Functions are deployed (validation-webhook, validation-response)
- [ ] Views exist (pending_reviews, active_validations)
- [ ] Experience validation status can be checked

### 4. Test Data Loading

Load test data for manual testing:

```bash
python scripts/load_test_data.py
```

**What it creates:**
- 3 internal resources (2 staff, 1 asset)
- 2 external resources (vendors)
- 3 policies (pricing, legal, technical)
- 1 sample RFP
- 3 experience entries (mix of validated/unvalidated)

**After loading:**
1. Embeddings are generated synchronously when using `record_experience()` tool
2. Check `pending_reviews` view for unvalidated experiences
3. Validate experiences manually: `UPDATE experience SET is_validated = true WHERE id = '...';`

### 5. Manual Testing Checklist

#### 5.1 Database Schema Validation

**Test: Verify all tables exist**
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

**Expected:** 9 tables listed (no embedding_queue, no user_tenants)

**Test: Verify RLS is disabled (single-tenant)**
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('internal_resources', 'experience', 'proposals');
```

**Expected:** `rowsecurity = false` for all tables

**Test: Verify indexes exist**
```sql
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND indexname LIKE 'idx_%';
```

**Expected:** Multiple indexes for search, embeddings, etc. (no tenant indexes)

#### 5.2 Hybrid Search Functions

**Test: Search internal resources**
```sql
SELECT * FROM search_internal_resources(
    'Python developer',
    '[0.1, 0.2, ...]'::halfvec(1536),  -- Use actual embedding
    0.7,
    10
);
```

**Expected:** Returns matching resources (if data exists)

**Test: Search experience (only validated)**
```sql
SELECT * FROM search_experience(
    'rate update',
    '[0.1, 0.2, ...]'::halfvec(1536),
    0.6,
    20
);
```

**Expected:** Returns only validated experience entries (`is_validated = true`)

#### 5.3 Embedding Generation

**Test: Verify embeddings are generated synchronously**
- Use `record_experience()` tool via MCP
- Embedding should be generated immediately (<1 second)
- Check `embedding` column is populated

**Test: Verify embeddings exist**
```sql
SELECT 
    COUNT(*) as total,
    COUNT(embedding) as with_embeddings
FROM experience;
```

**Expected:** All experiences should have embeddings (generated synchronously)

#### 5.4 Edge Functions

**Test: Validation response function**
```bash
# Get a validation token from validation_requests table
curl https://your-project.supabase.co/functions/v1/validation-response/TOKEN
```

**Expected:** Returns HTML form

**Test: Validation webhook**
- Submit validation response via Teams or email
- Verify response is stored in `validation_requests.response_data`
- AI should then process it and call `record_experience()`

**Note:** `process-embeddings` function is no longer needed (embeddings are synchronous)

#### 5.5 MCP Server Tools

**Test: Start MCP server**
```bash
python -m src.server
```

**Expected:** Server starts without errors (no auth required)

**Test: Search tools via MCP client**
- Connect Claude Desktop or Cursor with MCP configuration
- Try: `search_internal_resources("Python developer")`
- Try: `search_experience("rate update")` (only returns validated)

**Expected:** Returns relevant results

**Test: Record experience**
- Try: `record_experience(description="Test learning", confidence=0.9, requires_review=True)`

**Expected:** 
- Creates experience entry
- Embedding generated synchronously
- `is_validated = false` (goes to review queue)

**Test: Generate proposal**
- First create an RFP using `parse_rfp`
- Then: `generate_proposal(rfp_id="...")`

**Expected:** Creates proposal with validation requests

#### 5.6 Validation Workflow (AI-First)

**Test: Create validation request**
```python
# Via MCP tool or direct database insert
validation = {
    "proposal_id": "...",
    "entity_type": "internal_resource",
    "entity_id": "...",
    "validation_question": "Can this resource be allocated?",
    "current_information": {...},
    "recipient_email": "test@example.com",
    "delivery_method": "email"
}
```

**Test: Send email validation**
- Use `send_email_validation` tool
- Check email inbox for validation request

**Test: Process validation response**
- Submit response via email form or webhook
- Verify response stored in `validation_requests.response_data` (raw)
- AI should read response and call `record_experience()` with:
  - Clear description
  - Confidence score
  - `requires_review=True` (goes to review queue)

**Test: Review queue**
```sql
SELECT * FROM pending_reviews;
```

**Expected:** Shows all unvalidated experiences

**Test: Approve experience**
```sql
UPDATE experience 
SET is_validated = true, 
    reviewed_by = 'admin',
    reviewed_at = NOW()
WHERE id = '...';
```

**Expected:** Experience now appears in search results

#### 5.7 Single-Tenant Architecture

**Test: Verify no tenant_id columns**
```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND column_name = 'tenant_id';
```

**Expected:** No results (tenant_id columns removed)

**Test: Verify no RLS policies**
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
```

**Expected:** All tables have `rowsecurity = false`

**Test: Verify no embedding_queue**
```sql
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'embedding_queue'
);
```

**Expected:** Returns `false` (table doesn't exist)

### 6. Performance Tests

**Test: Search performance**
- Measure query time for hybrid search
- Test with various query lengths
- Test with different match thresholds

**Expected:** Queries complete in < 500ms for typical datasets

**Test: Embedding generation**
- Measure time to generate embedding in `record_experience()`
- Should be synchronous (<1 second)

**Expected:** Embeddings generated immediately during tool call

### 7. Error Handling Tests

**Test: Invalid configuration**
- Remove required env vars
- Verify clear error messages

**Test: Database connection failure**
- Disconnect from Supabase
- Verify graceful error handling

**Test: OpenAI API failure**
- Use invalid API key
- Verify error handling in `record_experience()`

### 8. Security Tests

**Test: Service role key protection**
- Verify service role key is never exposed to clients
- Check Edge Functions use service role correctly

**Test: Data isolation**
- Verify each client has separate Supabase project
- No cross-client data access possible (physical isolation)

## Test Data Requirements

### Minimum Test Dataset

1. **Internal Resources:** 3-5 entries
   - Mix of staff, tools, assets
   - Various skills and availability

2. **External Resources:** 2-3 entries
   - Different vendor types
   - Various approval statuses

3. **Policies:** 3-5 entries
   - Different categories
   - Various priorities

4. **Experience Entries:** 5-10 entries
   - Mix of validated and unvalidated
   - Different entity types
   - Various confidence scores

5. **RFPs:** 1-2 entries
   - With parsed requirements
   - Various project types

## Success Criteria

### Must Pass (Critical)
- [ ] All unit tests pass
- [ ] Database schema is complete (no tenant_id, no embedding_queue)
- [ ] RLS is disabled (single-tenant)
- [ ] Search functions work (only validated experiences in search)
- [ ] Embedding generation works synchronously
- [ ] Edge Functions are deployed (validation-webhook, validation-response)
- [ ] MCP server starts without errors (no auth)
- [ ] pending_reviews view works

### Should Pass (Important)
- [ ] Integration tests pass
- [ ] Test data loads successfully
- [ ] Validation workflow works end-to-end (AI processes responses)
- [ ] Performance is acceptable
- [ ] Review queue accessible

### Nice to Have (Optional)
- [ ] All edge cases handled
- [ ] Comprehensive error messages
- [ ] Performance optimizations

## Troubleshooting

### Common Issues

**Issue: Embeddings not generating**
- Embeddings are generated synchronously in `record_experience()`
- Check OpenAI API key is set correctly
- Verify network connectivity
- Review error messages in tool responses

**Issue: Search returns no results**
- Verify experiences exist and are validated (`is_validated = true`)
- Check that embeddings were generated (should be automatic)
- Lower `match_threshold` parameter if needed
- Use `pending_reviews` view to see unvalidated experiences

**Issue: Edge Functions not working**
- Check function deployment status
- Verify environment variables/secrets
- Review function logs in Supabase Dashboard
- Note: `process-embeddings` function is no longer needed

**Issue: Validation responses not processed**
- Verify response stored in `validation_requests.response_data`
- AI should read response and call `record_experience()`
- Check that experience entries are created
- Verify experiences go to review queue (`is_validated = false`)

## Next Steps After Testing

1. **Fix any failing tests**
2. **Address performance issues**
3. **Update documentation based on findings**
4. **Create production deployment checklist**
5. **Set up monitoring and alerts**

## Test Execution Log

Document test execution:

| Test Category | Date | Status | Notes |
|--------------|------|--------|-------|
| Unit Tests | | | |
| Integration Tests | | | |
| Deployment Validation | | | |
| Manual Testing | | | |
| Performance Tests | | | |

## Sign-off

- [ ] All critical tests passed
- [ ] System is ready for prototype use
- [ ] Documentation is complete
- [ ] Known issues documented

**Tester:** _________________  
**Date:** _________________  
**Approved by:** _________________
