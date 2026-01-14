# Testing Guide for Proposal MCP Server

## Quick Start

### 1. Install Test Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file or export variables:

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
export OPENAI_API_KEY="your-openai-key"
```

### 3. Run Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run all integration tests (requires Supabase)
pytest tests/integration/ -v -m integration

# Run all tests
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── unit/              # Unit tests (no external dependencies)
│   ├── test_config.py
│   ├── test_keywords.py
│   ├── test_embeddings.py
│   └── test_email.py
├── integration/       # Integration tests (require Supabase)
│   ├── test_database.py
│   └── test_tools.py
└── conftest.py        # Shared fixtures
```

## Loading Test Data

Load test data for manual testing:

```bash
python scripts/load_test_data.py
```

This creates:
- Sample internal resources
- External vendors
- Policies
- RFPs
- Experience entries (mix of validated/unvalidated)

**Note:** Embeddings are generated synchronously when using `record_experience()` tool. No waiting needed!

## Validation Scripts

### Deployment Validation

Check that deployment is correct:

```bash
python scripts/validate_deployment.py
```

This validates:
- Database schema (no tenant_id, no embedding_queue)
- Edge Functions (validation-webhook, validation-response)
- Indexes
- Experience validation status
- Views (pending_reviews)

### Tool Testing

Test MCP tools directly:

```bash
python scripts/test_mcp_tools.py
```

## Manual Testing Checklist

See [TEST_PLAN.md](TEST_PLAN.md) for comprehensive manual testing checklist.

### Quick Manual Tests

1. **Database Connection**
   ```python
   from supabase import create_client
   from src.config import Config
   
   client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
   result = client.table('internal_resources').select('*').limit(1).execute()
   print(result.data)
   ```

2. **Search Function**
   ```sql
   SELECT * FROM search_internal_resources(
       'Python developer',
       '[0.1, 0.2, ...]'::halfvec(1536),
       0.7,
       10
   );
   ```

3. **Pending Reviews**
   ```sql
   SELECT * FROM pending_reviews;
   ```

4. **MCP Server**
   ```bash
   python -m src.server
   # Then connect with Claude Desktop or Cursor
   ```

## Test Data

Test data is loaded via `scripts/load_test_data.py`. It creates:

- **3 Internal Resources:** Staff and assets
- **2 External Resources:** Vendors
- **3 Policies:** Pricing, legal, technical
- **1 RFP:** Sample cloud migration project
- **3 Experience Entries:** Mix of validated and unvalidated

**Key Points:**
- No tenant_id needed (single-tenant deployment)
- Embeddings generated synchronously
- Some experiences are validated, some need review

## Troubleshooting Tests

### Unit Tests Fail

- Check that all dependencies are installed
- Verify Python version (3.10+)
- Check for import errors

### Integration Tests Fail

- Verify Supabase credentials are set
- Check network connectivity
- Ensure database schema is deployed
- Verify tables exist (no embedding_queue, no user_tenants)

### Embeddings Not Generated

- Embeddings are generated synchronously in `record_experience()`
- Check OpenAI API key is correct
- Verify network connectivity
- Review error messages in tool responses

### Search Returns No Results

- Verify experiences exist: `SELECT COUNT(*) FROM experience;`
- Check if experiences are validated: `SELECT COUNT(*) FROM experience WHERE is_validated = true;`
- Verify embeddings exist: `SELECT COUNT(*) FROM experience WHERE embedding IS NOT NULL;`
- Lower `match_threshold` parameter if needed
- Check `pending_reviews` view for unvalidated experiences

### Validation Not Working

- Verify response stored in `validation_requests.response_data`
- AI should read response and call `record_experience()`
- Check that experiences are created with `is_validated = false`
- Use `pending_reviews` view to see unvalidated experiences

## Continuous Testing

For CI/CD, use:

```bash
# Run tests with coverage
pytest --cov=src --cov-report=xml --cov-report=term

# Run only fast unit tests
pytest tests/unit/ -v

# Run with specific markers
pytest -m "not integration" -v
```

## Test Coverage Goals

- **Unit Tests:** >80% coverage
- **Integration Tests:** Critical paths covered
- **Manual Tests:** All user workflows validated

## Architecture Notes

**Single-Tenant Deployment:**
- Each client gets their own Supabase project
- No RLS policies needed
- No tenant_id columns
- Physical data isolation

**AI-First Processing:**
- AI reads validation responses
- AI calls `record_experience()` directly
- Embeddings generated synchronously (<1 second)
- No embedding queue needed

**Manual Review Gate:**
- New experiences go to review queue (`is_validated = false`)
- Only validated experiences appear in search
- Use `pending_reviews` view for admin review

## Next Steps

1. Run all tests: `pytest -v`
2. Load test data: `python scripts/load_test_data.py`
3. Validate deployment: `python scripts/validate_deployment.py`
4. Test MCP tools: `python scripts/test_mcp_tools.py`
5. Follow manual testing checklist in TEST_PLAN.md
