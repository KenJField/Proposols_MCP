"""Pytest configuration and fixtures."""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any
import uuid


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    client = Mock()
    client.table = Mock(return_value=client)
    client.rpc = Mock(return_value=client)
    client.select = Mock(return_value=client)
    client.insert = Mock(return_value=client)
    client.update = Mock(return_value=client)
    client.eq = Mock(return_value=client)
    client.single = Mock(return_value=client)
    client.execute = Mock(return_value=Mock(data=[]))
    return client


@pytest.fixture
def test_internal_resource():
    """Sample internal resource data."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Jane Smith",
        "resource_type": "staff",
        "description": "Senior software engineer specializing in Python, FastAPI, and PostgreSQL",
        "approval_contact_name": "Engineering Manager",
        "approval_contact_email": "manager@example.com",
        "approval_contact_role": "Engineering Manager",
        "hourly_rate": 150.00,
        "currency": "USD",
        "availability_status": "available",
        "skills": {
            "Python": "expert",
            "PostgreSQL": "advanced",
            "FastAPI": "expert"
        },
        "is_active": True
    }


@pytest.fixture
def test_experience_entry():
    """Sample experience entry data."""
    return {
        "id": str(uuid.uuid4()),
        "description": "Jane's hourly rate was updated to $175/hour in January 2025",
        "keywords": ["rate", "hourly", "update", "january"],
        "entity_type": "internal_resource",
        "entity_id": str(uuid.uuid4()),
        "entity_name": "Jane Smith",
        "source_type": "validation_response",
        "confidence_score": 0.95,
        "is_validated": False,  # Goes to review queue
        "created_by": "ai"
    }


@pytest.fixture
def test_rfp_data():
    """Sample RFP data."""
    return {
        "id": str(uuid.uuid4()),
        "rfp_number": "RFP-2025-001",
        "client_name": "Acme Corporation",
        "project_title": "Cloud Migration Project",
        "parsed_requirements": {
            "summary": "Migration of legacy systems to cloud infrastructure",
            "requirements": ["Python developers", "PostgreSQL expertise", "Cloud architecture"],
            "deadlines": {"proposal_due": "2025-02-15", "project_start": "2025-03-01"},
            "budget": {"estimated": 500000, "currency": "USD"}
        }
    }


@pytest.fixture
def mock_openai_embedding():
    """Mock OpenAI embedding response."""
    return {
        "data": [{
            "embedding": [0.1] * 1536  # Mock 1536-dimensional embedding
        }]
    }


@pytest.fixture
def mock_context():
    """Mock FastMCP context."""
    context = Mock()
    context.report_progress = AsyncMock()
    return context


@pytest.fixture
def env_vars(monkeypatch):
    """Set up test environment variables."""
    test_vars = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        "OPENAI_API_KEY": "test-openai-key",
        "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
        "STATELESS_HTTP": "true"
    }
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    return test_vars
