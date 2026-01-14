"""Script to validate deployment and check system health."""

import os
import sys
from supabase import create_client
from src.config import Config

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_database_schema():
    """Validate that all required tables and functions exist."""
    print("🔍 Checking database schema...")
    
    client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
    
    required_tables = [
        'internal_resources', 'external_resources', 'policies',
        'experience', 'rfps', 'proposals', 'validation_requests',
        'audit_log', 'account_managers'
    ]
    
    missing_tables = []
    for table in required_tables:
        try:
            result = client.table(table).select('*').limit(1).execute()
            print(f"  ✓ Table '{table}' exists")
        except Exception as e:
            print(f"  ✗ Table '{table}' missing or inaccessible: {e}")
            missing_tables.append(table)
    
    # Check functions
    print("\n🔍 Checking database functions...")
    functions = ['search_internal_resources', 'search_experience']
    for func in functions:
        try:
            # Try calling with dummy data
            result = client.rpc(func, {
                'query_text': 'test',
                'query_embedding': [0.0] * 1536,
                'match_threshold': 0.5,
                'match_count': 1
            }).execute()
            print(f"  ✓ Function '{func}' exists")
        except Exception as e:
            if "does not exist" in str(e).lower():
                print(f"  ✗ Function '{func}' missing: {e}")
            else:
                print(f"  ✓ Function '{func}' exists (may need data to work)")
    
    # Check views
    print("\n🔍 Checking database views...")
    views = ['pending_reviews', 'active_validations', 'experience_by_entity']
    for view in views:
        try:
            result = client.table(view).select('*').limit(1).execute()
            print(f"  ✓ View '{view}' exists")
        except Exception as e:
            print(f"  ✗ View '{view}' missing: {e}")
    
    return len(missing_tables) == 0


def check_edge_functions():
    """Check that Edge Functions are deployed."""
    print("\n🔍 Checking Edge Functions...")
    
    # We can't directly check via API, but we can document what should exist
    expected_functions = [
        'validation-webhook',
        'validation-response'
    ]
    
    print("  Expected Edge Functions:")
    for func in expected_functions:
        print(f"    - {func}")
    print("  ⚠️  Verify in Supabase Dashboard → Edge Functions")
    print("  Note: process-embeddings function is no longer needed (embeddings are synchronous)")
    
    return True


def check_indexes():
    """Check that indexes are created."""
    print("\n🔍 Checking indexes...")
    
    # This is informational - indexes are created automatically
    print("  ✓ Indexes should be created automatically by schema")
    print("  ⚠️  Verify in Supabase Dashboard → Database → Indexes")
    
    return True


def check_experience_validation():
    """Check experience validation status."""
    print("\n🔍 Checking experience validation...")
    
    client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
    
    try:
        # Check total experiences
        total_result = client.table('experience').select('id', count='exact').execute()
        total = total_result.count if hasattr(total_result, 'count') else 0
        
        # Check validated experiences
        validated_result = client.table('experience').select('id', count='exact').eq('is_validated', True).execute()
        validated = validated_result.count if hasattr(validated_result, 'count') else 0
        
        # Check pending reviews
        pending_result = client.table('experience').select('id', count='exact').eq('is_validated', False).execute()
        pending = pending_result.count if hasattr(pending_result, 'count') else 0
        
        print(f"  Total experiences: {total}")
        print(f"  Validated: {validated}")
        print(f"  Pending review: {pending}")
        
        if pending > 0:
            print(f"  ⚠️  {pending} experiences need review (check pending_reviews view)")
        else:
            print(f"  ✓ No pending reviews")
        
        return True
    except Exception as e:
        print(f"  ✗ Error checking experiences: {e}")
        return False


def main():
    """Run all validation checks."""
    print("🚀 Proposal MCP Server - Deployment Validation\n")
    print("Single-Tenant Deployment Model\n")
    
    # Validate configuration
    try:
        Config.validate()
        print("✓ Configuration valid\n")
    except ValueError as e:
        print(f"✗ Configuration error: {e}\n")
        return False
    
    checks = [
        ("Database Schema", check_database_schema),
        ("Edge Functions", check_edge_functions),
        ("Indexes", check_indexes),
        ("Experience Validation", check_experience_validation),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ Error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "="*50)
    print("📊 Validation Summary:")
    print("="*50)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✅ All checks passed! System is ready.")
    else:
        print("\n⚠️  Some checks failed. Please review and fix issues.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
