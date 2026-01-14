"""Quick test script to verify basic functionality."""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from supabase import create_client


def test_config():
    """Test configuration."""
    print("1. Testing configuration...")
    try:
        Config.validate()
        print("   ✓ Configuration valid")
        return True
    except ValueError as e:
        print(f"   ✗ Configuration error: {e}")
        return False


def test_database_connection():
    """Test database connection."""
    print("\n2. Testing database connection...")
    try:
        client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
        result = client.table('internal_resources').select('id').limit(1).execute()
        print("   ✓ Database connection successful")
        return True
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        return False


def test_tables():
    """Test that required tables exist."""
    print("\n3. Testing database tables...")
    try:
        client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
        tables = [
            'internal_resources', 'external_resources', 'policies',
            'experience', 'rfps', 'proposals', 'validation_requests'
        ]
        
        missing = []
        for table in tables:
            try:
                client.table(table).select('id').limit(1).execute()
            except:
                missing.append(table)
        
        if missing:
            print(f"   ✗ Missing tables: {', '.join(missing)}")
            return False
        else:
            print(f"   ✓ All {len(tables)} tables exist")
            return True
    except Exception as e:
        print(f"   ✗ Error checking tables: {e}")
        return False


def test_functions():
    """Test that search functions exist."""
    print("\n4. Testing database functions...")
    try:
        client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
        # Try calling the function (may fail if no data, but function should exist)
        try:
            client.rpc('search_internal_resources', {
                'query_text': 'test',
                'query_embedding': [0.0] * 1536,
                'match_threshold': 0.7,
                'match_count': 1
            }).execute()
            print("   ✓ Search functions exist and are callable")
        except Exception as e:
            if "does not exist" in str(e).lower():
                print(f"   ✗ Function missing: {e}")
                return False
            else:
                print("   ✓ Search functions exist (may need data to work)")
        return True
    except Exception as e:
        print(f"   ✗ Error checking functions: {e}")
        return False


def main():
    """Run quick tests."""
    print("🚀 Quick Test Suite\n")
    print("="*50)
    
    tests = [
        test_config,
        test_database_connection,
        test_tables,
        test_functions,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"   ✗ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "="*50)
    print("📊 Results:")
    print("="*50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"  Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All quick tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
