"""Script to test MCP tools directly without MCP client."""

import os
import sys
import asyncio
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.tools.search import search_internal_resources, search_experience
from src.tools.experience import record_experience
from src.tools.proposals import parse_rfp, generate_proposal


async def test_search_tools():
    """Test search tools."""
    print("🔍 Testing search tools...")
    
    try:
        # Test search internal resources
        print("\n1. Testing search_internal_resources...")
        results = await search_internal_resources(
            query="Python developer",
            max_results=5
        )
        print(f"   ✓ Found {len(results)} results")
        if results:
            print(f"   Sample: {results[0].get('name', 'N/A')}")
        
        # Test search experience (only returns validated experiences)
        print("\n2. Testing search_experience...")
        results = await search_experience(
            query="rate update",
            max_results=5
        )
        print(f"   ✓ Found {len(results)} results (validated experiences only)")
        if results:
            print(f"   Sample: {results[0].get('description', 'N/A')[:50]}...")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


async def test_experience_tools():
    """Test experience recording."""
    print("\n🧠 Testing experience tools...")
    
    try:
        result = await record_experience(
            description="Test experience entry for validation - embeddings generated synchronously",
            entity_type="internal_resource",
            source_type="test",
            confidence=0.8,
            requires_review=True  # Goes to review queue
        )
        
        print(f"   ✓ Created experience: {result.get('experience_id')}")
        print(f"   ⚠️  This experience is unvalidated (check pending_reviews view)")
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_proposal_tools():
    """Test proposal generation tools."""
    print("\n📄 Testing proposal tools...")
    
    try:
        # Test RFP parsing
        print("\n1. Testing parse_rfp...")
        result = await parse_rfp(
            document_url="https://example.com/rfp.pdf",
            client_name="Test Client",
            project_title="Test Project"
        )
        print(f"   ✓ Parsed RFP: {result.get('rfp_id')}")
        
        # Note: generate_proposal requires actual RFP and resources
        print("\n2. Skipping generate_proposal (requires real data)")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tool tests."""
    print("🚀 Testing MCP Tools\n")
    print("="*50)
    
    # Validate configuration
    try:
        Config.validate()
        print("✓ Configuration valid\n")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        print("\nPlease set required environment variables:")
        print("  - SUPABASE_URL")
        print("  - SUPABASE_SERVICE_ROLE_KEY")
        print("  - OPENAI_API_KEY")
        return False
    
    tests = [
        ("Search Tools", test_search_tools),
        ("Experience Tools", test_experience_tools),
        ("Proposal Tools", test_proposal_tools),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")
            results.append((name, False))
    
    print("\n" + "="*50)
    print("📊 Test Summary:")
    print("="*50)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✅ All tool tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
