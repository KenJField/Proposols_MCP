"""Script to load test data into Supabase for testing and development."""

import os
import sys
import uuid
from datetime import date, timedelta
from supabase import create_client
from src.config import Config

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_test_data():
    """Load comprehensive test data for the proposal MCP server."""
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and OPENAI_API_KEY")
        return
    
    # Initialize Supabase client
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)
    
    print("Loading test data for single-tenant deployment...")
    
    # 1. Load Internal Resources
    print("\n📦 Loading internal resources...")
    internal_resources = [
        {
            "name": "Jane Smith",
            "resource_type": "staff",
            "description": "Senior software engineer specializing in Python, FastAPI, PostgreSQL, and cloud architecture. 10+ years experience.",
            "approval_contact_name": "Sarah Johnson",
            "approval_contact_email": "sarah.johnson@example.com",
            "approval_contact_role": "Engineering Manager",
            "hourly_rate": 150.00,
            "currency": "USD",
            "rate_notes": "Standard rate for senior engineers",
            "availability_status": "available",
            "capacity_percentage": 75,
            "available_from": date.today().isoformat(),
            "skills": {
                "Python": "expert",
                "PostgreSQL": "advanced",
                "FastAPI": "expert",
                "AWS": "intermediate",
                "Docker": "advanced"
            },
            "certifications": ["AWS Solutions Architect", "Python Professional"]
        },
        {
            "name": "Mike Chen",
            "resource_type": "staff",
            "description": "Full-stack developer with expertise in React, TypeScript, Node.js, and microservices architecture.",
            "approval_contact_name": "Sarah Johnson",
            "approval_contact_email": "sarah.johnson@example.com",
            "approval_contact_role": "Engineering Manager",
            "hourly_rate": 125.00,
            "currency": "USD",
            "availability_status": "available",
            "capacity_percentage": 60,
            "skills": {
                "React": "expert",
                "TypeScript": "expert",
                "Node.js": "advanced",
                "GraphQL": "intermediate"
            }
        },
        {
            "name": "AWS Production Cluster",
            "resource_type": "asset",
            "description": "High-availability AWS EKS cluster with auto-scaling, load balancing, and monitoring. Suitable for production workloads.",
            "approval_contact_name": "David Kim",
            "approval_contact_email": "david.kim@example.com",
            "approval_contact_role": "Infrastructure Director",
            "hourly_rate": 50.00,
            "currency": "USD",
            "rate_notes": "Infrastructure cost allocation",
            "availability_status": "available",
            "specifications": {
                "type": "Kubernetes Cluster",
                "nodes": 5,
                "region": "us-east-1",
                "instance_type": "m5.large"
            }
        }
    ]
    
    for resource in internal_resources:
        result = supabase.table('internal_resources').insert(resource).execute()
        print(f"  ✓ Created: {resource['name']} ({result.data[0]['id']})")
    
    # 2. Load External Resources
    print("\n🏢 Loading external resources...")
    external_resources = [
        {
            "vendor_name": "TechConsulting Inc",
            "vendor_type": "Consultant",
            "description": "Technology consulting firm specializing in cloud architecture, AI/ML, and data engineering. Proven track record with Fortune 500 companies.",
            "website": "https://techconsulting.example.com",
            "approval_status": "approved_vendor",
            "approval_notes": "Approved vendor with MSA in place",
            "has_msa": True,
            "insurance_verified": True,
            "typical_hourly_rate": 200.00,
            "currency": "USD",
            "pricing_notes": "Rates vary by project scope",
            "service_areas": ["Cloud Architecture", "AI/ML", "Data Engineering", "DevOps"],
            "specializations": ["AWS", "Azure", "Kubernetes", "Machine Learning"],
            "geographic_coverage": ["North America", "Europe"]
        },
        {
            "vendor_name": "DesignStudio Pro",
            "vendor_type": "Contractor",
            "description": "UI/UX design agency with expertise in enterprise applications and design systems.",
            "approval_status": "approved_vendor",
            "has_msa": True,
            "typical_daily_rate": 1200.00,
            "service_areas": ["UI/UX Design", "Design Systems", "User Research"]
        }
    ]
    
    for vendor in external_resources:
        result = supabase.table('external_resources').insert(vendor).execute()
        print(f"  ✓ Created: {vendor['vendor_name']} ({result.data[0]['id']})")
    
    # 3. Load Policies
    print("\n📋 Loading policies...")
    policies = [
        {
            "policy_name": "Minimum Profit Margin",
            "policy_category": "Pricing",
            "description": "All proposals must maintain minimum 15% profit margin",
            "requirements": "Calculate total costs and ensure final price achieves 15% margin after all expenses including overhead",
            "policy_owner_name": "CFO",
            "policy_owner_email": "cfo@example.com",
            "applies_to": ["all_proposals"],
            "tags": ["pricing", "profitability", "financial"],
            "priority": 1
        },
        {
            "policy_name": "Data Privacy Compliance",
            "policy_category": "Legal",
            "description": "All proposals must ensure GDPR and CCPA compliance",
            "requirements": "Include data protection measures, consent management, and privacy impact assessment in all proposals",
            "policy_owner_name": "Legal Counsel",
            "policy_owner_email": "legal@example.com",
            "applies_to": ["all_proposals"],
            "tags": ["privacy", "legal", "compliance", "GDPR", "CCPA"],
            "priority": 1
        },
        {
            "policy_name": "Security Review Required",
            "policy_category": "Technical",
            "description": "All proposals involving cloud infrastructure require security review",
            "requirements": "Security team must review and approve proposals before submission",
            "policy_owner_name": "CISO",
            "policy_owner_email": "ciso@example.com",
            "applies_to": ["cloud_projects", "infrastructure_projects"],
            "tags": ["security", "cloud", "infrastructure"],
            "priority": 2
        }
    ]
    
    for policy in policies:
        result = supabase.table('policies').insert(policy).execute()
        print(f"  ✓ Created: {policy['policy_name']} ({result.data[0]['id']})")
    
    # 4. Load Sample RFP
    print("\n📄 Loading sample RFP...")
    rfp = {
        "rfp_number": "RFP-2025-001",
        "client_name": "Acme Corporation",
        "project_title": "Cloud Migration and Modernization",
        "raw_document_url": "https://example.com/rfps/rfp-2025-001.pdf",
        "parsed_markdown": "# Cloud Migration Project\n\nAcme Corporation seeks proposals for migrating legacy systems to cloud infrastructure...",
        "parsed_requirements": {
            "summary": "Migration of legacy systems to cloud infrastructure with focus on scalability and security",
            "requirements": [
                "Python developers with cloud experience",
                "PostgreSQL database expertise",
                "Kubernetes orchestration",
                "Security compliance (SOC 2, ISO 27001)",
                "24/7 monitoring and support"
            ],
            "deadlines": {
                "proposal_due": "2025-02-15",
                "project_start": "2025-03-01",
                "project_end": "2025-12-31"
            },
            "budget": {
                "estimated": 500000,
                "currency": "USD"
            }
        },
        "rfp_received_date": date.today().isoformat(),
        "proposal_due_date": (date.today() + timedelta(days=30)).isoformat(),
        "project_start_date": (date.today() + timedelta(days=45)).isoformat(),
        "project_end_date": (date.today() + timedelta(days=365)).isoformat(),
        "estimated_budget": 500000.00,
        "budget_currency": "USD"
    }
    
    rfp_result = supabase.table('rfps').insert(rfp).execute()
    rfp_id = rfp_result.data[0]['id']
    print(f"  ✓ Created RFP: {rfp['project_title']} ({rfp_id})")
    
    # 5. Load Sample Experience Entries
    print("\n🧠 Loading sample experience entries...")
    experiences = [
        {
            "description": "Jane Smith's hourly rate was updated to $175/hour effective January 2025 based on validation feedback",
            "keywords": ["rate", "hourly", "update", "january", "validation"],
            "entity_type": "internal_resource",
            "entity_name": "Jane Smith",
            "source_type": "validation_response",
            "confidence_score": 0.95,
            "is_validated": True  # This one is validated (appears in search)
        },
        {
            "description": "TechConsulting Inc requires 2-week notice for project allocation and prefers fixed-price contracts",
            "keywords": ["vendor", "allocation", "notice", "contract", "fixed-price"],
            "entity_type": "external_resource",
            "entity_name": "TechConsulting Inc",
            "source_type": "validation_response",
            "confidence_score": 0.90,
            "is_validated": True
        },
        {
            "description": "AWS Production Cluster has 80% capacity utilization and should not be allocated to new projects without approval",
            "keywords": ["capacity", "utilization", "allocation", "approval"],
            "entity_type": "internal_resource",
            "entity_name": "AWS Production Cluster",
            "source_type": "ai_inference",
            "confidence_score": 0.85,
            "is_validated": False  # This one needs review (in pending_reviews view)
        }
    ]
    
    for exp in experiences:
        result = supabase.table('experience').insert(exp).execute()
        print(f"  ✓ Created experience: {exp['description'][:50]}... ({result.data[0]['id']})")
        print(f"    Validated: {exp.get('is_validated', False)}")
    
    print(f"\n✅ Test data loaded successfully!")
    print(f"\n💡 Next steps:")
    print(f"   1. Embeddings are generated synchronously when using record_experience() tool")
    print(f"   2. Check pending_reviews view for unvalidated experiences: SELECT * FROM pending_reviews;")
    print(f"   3. Test the MCP server tools")
    print(f"   4. Validate experiences via: UPDATE experience SET is_validated = true WHERE id = '...';")


if __name__ == "__main__":
    load_test_data()
