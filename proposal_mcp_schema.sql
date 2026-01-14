-- ============================================================================
-- Proposal Generation MCP Server - Supabase Database Schema
-- ============================================================================
-- This schema supports a self-updating knowledge base for AI-powered proposal
-- generation with validation workflows. Single-tenant deployment model.
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================================
-- ENUMS AND TYPES
-- ============================================================================

CREATE TYPE approval_status AS ENUM (
    'approved_vendor',
    'high_quality',
    'low_quality',
    'unexplored',
    'prohibited'
);

CREATE TYPE validation_status AS ENUM (
    'pending',
    'sent',
    'approved',
    'rejected',
    'updated',
    'expired'
);

CREATE TYPE resource_type AS ENUM (
    'staff',
    'tool',
    'asset',
    'facility',
    'license'
);

CREATE TYPE proposal_status AS ENUM (
    'draft',
    'validating',
    'revision',
    'final',
    'submitted',
    'won',
    'lost'
);

-- ============================================================================
-- CORE TABLES (Admin-Managed, Read by AI)
-- ============================================================================

-- Internal Resources: Staff, tools, and assets owned by the company
CREATE TABLE internal_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Resource identification
    name TEXT NOT NULL,
    resource_type resource_type NOT NULL,
    description TEXT NOT NULL,
    
    -- Contact and approval
    approval_contact_name TEXT NOT NULL,
    approval_contact_email TEXT NOT NULL,
    approval_contact_role TEXT,  -- e.g., "Engineering Manager", "Facilities Director"
    
    -- Pricing
    hourly_rate DECIMAL(10,2),
    daily_rate DECIMAL(10,2),
    project_rate DECIMAL(10,2),
    currency TEXT DEFAULT 'USD',
    rate_notes TEXT,  -- Additional pricing context
    
    -- Availability and capacity
    availability_status TEXT,  -- e.g., "available", "limited", "unavailable"
    capacity_percentage INTEGER CHECK (capacity_percentage BETWEEN 0 AND 100),
    available_from DATE,
    available_until DATE,
    
    -- Skills and capabilities (for staff)
    skills JSONB,  -- Array of skills with proficiency levels
    certifications TEXT[],
    
    -- Technical specifications (for tools/assets)
    specifications JSONB,
    
    -- Full-text search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(rate_notes, '')), 'C')
    ) STORED,
    
    -- Semantic search
    embedding HALFVEC(1536),  -- OpenAI ada-002 or similar
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,  -- References auth.users
    is_active BOOLEAN DEFAULT true
);

-- External Resources: Vendors and contractors
CREATE TABLE external_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Vendor identification
    vendor_name TEXT NOT NULL,
    vendor_type TEXT NOT NULL,  -- e.g., "Consultant", "Contractor", "Supplier"
    description TEXT NOT NULL,
    website TEXT,
    
    -- Approval status
    approval_status approval_status NOT NULL DEFAULT 'unexplored',
    approval_notes TEXT,  -- Why approved/prohibited
    
    -- Legal agreements
    has_msa BOOLEAN DEFAULT false,
    msa_link TEXT,
    msa_expiry_date DATE,
    insurance_verified BOOLEAN DEFAULT false,
    
    -- Pricing
    typical_hourly_rate DECIMAL(10,2),
    typical_daily_rate DECIMAL(10,2),
    typical_project_rate DECIMAL(10,2),
    currency TEXT DEFAULT 'USD',
    pricing_notes TEXT,
    requires_rfq BOOLEAN DEFAULT false,  -- Requires quote for each project
    
    -- Capabilities
    service_areas TEXT[],
    specializations TEXT[],
    geographic_coverage TEXT[],
    
    -- Full-text search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(vendor_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(pricing_notes, '')), 'C')
    ) STORED,
    
    -- Semantic search
    embedding HALFVEC(1536),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    is_active BOOLEAN DEFAULT true
);

-- Account Managers: Contacts for external resources (many-to-many)
CREATE TABLE account_managers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_resource_id UUID NOT NULL REFERENCES external_resources(id) ON DELETE CASCADE,
    
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    role TEXT,  -- e.g., "Primary Contact", "Billing", "Technical Lead"
    is_primary BOOLEAN DEFAULT false,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Policies: Business rules and requirements for proposals
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Policy identification
    policy_name TEXT NOT NULL,
    policy_category TEXT NOT NULL,  -- e.g., "Pricing", "Legal", "Technical", "Quality"
    description TEXT NOT NULL,
    
    -- Policy details
    applies_to TEXT[],  -- e.g., ["all_proposals", "government", "private_sector"]
    requirements TEXT NOT NULL,  -- Detailed requirements
    exceptions TEXT,  -- When policy can be waived
    
    -- Ownership
    policy_owner_name TEXT NOT NULL,
    policy_owner_email TEXT NOT NULL,
    policy_owner_role TEXT,
    
    -- Tags for search
    tags TEXT[],
    priority INTEGER DEFAULT 1,  -- 1=critical, 2=important, 3=nice-to-have
    
    -- Full-text search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(policy_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(requirements, '')), 'C')
    ) STORED,
    
    -- Semantic search
    embedding HALFVEC(1536),
    
    -- Metadata
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_until DATE,
    version INTEGER DEFAULT 1,
    supersedes_policy_id UUID REFERENCES policies(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    is_active BOOLEAN DEFAULT true
);

-- ============================================================================
-- AI-MANAGED KNOWLEDGE TABLE
-- ============================================================================

-- Experience: AI-learned facts and knowledge updates
CREATE TABLE experience (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Experience content
    description TEXT NOT NULL,
    keywords TEXT[],  -- AI-extracted keywords (optional, AI can provide)
    
    -- Association with other entities
    entity_type TEXT CHECK (entity_type IN (
        'internal_resource',
        'external_resource', 
        'policy',
        'proposal',
        'general'
    )),
    entity_id UUID,  -- Foreign key to associated entity
    entity_name TEXT,  -- Denormalized for easy display
    
    -- Source tracking
    source_type TEXT NOT NULL,  -- e.g., "validation_response", "rfp_analysis", "manual_entry"
    source_id UUID,  -- Reference to validation request, proposal, etc.
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0 AND 1),
    
    -- Versioning
    version INTEGER DEFAULT 1,
    supersedes_experience_id UUID REFERENCES experience(id),
    
    -- Full-text search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(description, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(array_to_string(keywords, ' '), '')), 'B')
    ) STORED,
    
    -- Semantic search
    embedding HALFVEC(1536),
    
    -- Manual review gate
    is_validated BOOLEAN DEFAULT FALSE,  -- Only validated experiences appear in search
    reviewed_by TEXT,  -- User who reviewed (optional)
    reviewed_at TIMESTAMPTZ,  -- When reviewed
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'ai',  -- 'ai' or user UUID
    validation_notes TEXT
);

-- ============================================================================
-- PROPOSAL WORKFLOW TABLES
-- ============================================================================

-- RFPs: Parsed request for proposal documents
CREATE TABLE rfps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- RFP identification
    rfp_number TEXT,
    client_name TEXT NOT NULL,
    project_title TEXT NOT NULL,
    
    -- Parsed content
    raw_document_url TEXT,
    parsed_markdown TEXT,
    parsed_requirements JSONB,  -- Structured extraction
    
    -- Key dates
    rfp_received_date DATE,
    proposal_due_date DATE,
    project_start_date DATE,
    project_end_date DATE,
    
    -- Budget
    estimated_budget DECIMAL(12,2),
    budget_currency TEXT DEFAULT 'USD',
    
    -- Embedding for semantic search
    embedding HALFVEC(1536),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

-- Proposals: Generated proposal documents
CREATE TABLE proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfp_id UUID REFERENCES rfps(id),
    
    -- Proposal details
    proposal_title TEXT NOT NULL,
    proposal_status proposal_status DEFAULT 'draft',
    
    -- Generated content
    executive_summary TEXT,
    technical_approach TEXT,
    project_plan JSONB,  -- Structured plan with phases, tasks, timeline
    team_composition JSONB,  -- Resources assigned
    budget_breakdown JSONB,  -- Detailed pricing
    
    -- Totals
    total_cost DECIMAL(12,2),
    currency TEXT DEFAULT 'USD',
    
    -- Resources used
    internal_resources_used UUID[],  -- Array of internal_resources.id
    external_resources_used UUID[],  -- Array of external_resources.id
    
    -- Validation tracking
    validation_required BOOLEAN DEFAULT true,
    validation_completed BOOLEAN DEFAULT false,
    validations_sent INTEGER DEFAULT 0,
    validations_approved INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,  -- 'ai' or user UUID
    finalized_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ
);

-- Validation Requests: Track validation workflow
CREATE TABLE validation_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What's being validated
    proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,  -- 'internal_resource', 'external_resource', 'policy', 'experience'
    entity_id UUID NOT NULL,
    
    -- Validation details
    validation_question TEXT NOT NULL,
    current_information JSONB,  -- What we think we know
    
    -- Recipient
    recipient_name TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    
    -- Delivery
    delivery_method TEXT CHECK (delivery_method IN ('email', 'teams', 'slack')),
    message_id TEXT,  -- External message ID for tracking
    sent_at TIMESTAMPTZ,
    
    -- Response (stored raw, AI processes it)
    validation_status validation_status DEFAULT 'pending',
    response_received_at TIMESTAMPTZ,
    response_data JSONB,  -- Raw structured response from user
    corrections_provided TEXT,  -- Raw text corrections
    
    -- Experience generation
    experience_created BOOLEAN DEFAULT false,
    experience_id UUID REFERENCES experience(id),
    
    -- Expiry
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- AUDIT AND TRACKING
-- ============================================================================

-- Audit Log: Track all changes (especially AI updates)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What changed
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    
    -- Who made the change
    changed_by TEXT NOT NULL,  -- 'ai' or user UUID
    change_reason TEXT,
    
    -- Change details
    old_values JSONB,
    new_values JSONB,
    
    -- Metadata
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Full-text search indexes
CREATE INDEX idx_internal_resources_fts ON internal_resources USING gin(search_vector);
CREATE INDEX idx_external_resources_fts ON external_resources USING gin(search_vector);
CREATE INDEX idx_policies_fts ON policies USING gin(search_vector);
CREATE INDEX idx_experience_fts ON experience USING gin(search_vector);

-- Vector similarity search indexes (HNSW for fast ANN search)
CREATE INDEX idx_internal_resources_embedding ON internal_resources 
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_external_resources_embedding ON external_resources 
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_policies_embedding ON policies 
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_experience_embedding ON experience 
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_rfps_embedding ON rfps 
    USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Foreign key lookup indexes
CREATE INDEX idx_account_managers_external_resource ON account_managers(external_resource_id);
CREATE INDEX idx_proposals_rfp ON proposals(rfp_id);
CREATE INDEX idx_validation_requests_proposal ON validation_requests(proposal_id);
CREATE INDEX idx_experience_entity ON experience(entity_type, entity_id);

-- Status and workflow indexes
CREATE INDEX idx_validation_requests_status ON validation_requests(validation_status, expires_at);
CREATE INDEX idx_proposals_status ON proposals(proposal_status);
CREATE INDEX idx_experience_validated ON experience(is_validated) WHERE is_validated = TRUE;

-- Array search indexes (GIN for contains operations)
CREATE INDEX idx_internal_resources_skills ON internal_resources USING gin(skills jsonb_path_ops);
CREATE INDEX idx_external_resources_service_areas ON external_resources USING gin(service_areas);
CREATE INDEX idx_policies_tags ON policies USING gin(tags);
CREATE INDEX idx_experience_keywords ON experience USING gin(keywords);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Updated_at timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables
CREATE TRIGGER update_internal_resources_updated_at
    BEFORE UPDATE ON internal_resources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_external_resources_updated_at
    BEFORE UPDATE ON external_resources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_policies_updated_at
    BEFORE UPDATE ON policies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_experience_updated_at
    BEFORE UPDATE ON experience
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_proposals_updated_at
    BEFORE UPDATE ON proposals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_validation_requests_updated_at
    BEFORE UPDATE ON validation_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Audit log trigger for experience table
CREATE OR REPLACE FUNCTION log_experience_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, action, changed_by, new_values)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', NEW.created_by, to_jsonb(NEW));
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, action, changed_by, old_values, new_values)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', NEW.created_by, to_jsonb(OLD), to_jsonb(NEW));
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, action, changed_by, old_values)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', 'system', to_jsonb(OLD));
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_experience_changes
    AFTER INSERT OR UPDATE OR DELETE ON experience
    FOR EACH ROW EXECUTE FUNCTION log_experience_changes();

-- ============================================================================
-- FUNCTIONS FOR HYBRID SEARCH
-- ============================================================================

-- Hybrid search for internal resources
CREATE OR REPLACE FUNCTION search_internal_resources(
    query_text TEXT,
    query_embedding HALFVEC(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    resource_type resource_type,
    description TEXT,
    similarity FLOAT,
    rank FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic_search AS (
        SELECT 
            ir.id,
            ir.name,
            ir.resource_type,
            ir.description,
            1 - (ir.embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY ir.embedding <=> query_embedding) AS rank
        FROM internal_resources ir
        WHERE ir.is_active = true
            AND 1 - (ir.embedding <=> query_embedding) > match_threshold
    ),
    fulltext_search AS (
        SELECT 
            ir.id,
            ir.name,
            ir.resource_type,
            ir.description,
            ts_rank(ir.search_vector, websearch_to_tsquery('english', query_text)) AS similarity,
            ROW_NUMBER() OVER (ORDER BY ts_rank(ir.search_vector, websearch_to_tsquery('english', query_text)) DESC) AS rank
        FROM internal_resources ir
        WHERE ir.is_active = true
            AND ir.search_vector @@ websearch_to_tsquery('english', query_text)
    )
    SELECT 
        COALESCE(ss.id, fts.id) AS id,
        COALESCE(ss.name, fts.name) AS name,
        COALESCE(ss.resource_type, fts.resource_type) AS resource_type,
        COALESCE(ss.description, fts.description) AS description,
        COALESCE(ss.similarity, 0.0) + COALESCE(fts.similarity, 0.0) AS similarity,
        -- Reciprocal Rank Fusion
        COALESCE(1.0 / (60 + ss.rank), 0.0) + COALESCE(1.0 / (60 + fts.rank), 0.0) AS rank
    FROM semantic_search ss
    FULL OUTER JOIN fulltext_search fts ON ss.id = fts.id
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- Hybrid search for experience (most frequently used by AI)
-- Only returns validated experiences unless explicitly requested
CREATE OR REPLACE FUNCTION search_experience(
    query_text TEXT,
    query_embedding HALFVEC(1536),
    match_threshold FLOAT DEFAULT 0.6,
    match_count INT DEFAULT 20,
    p_entity_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    description TEXT,
    keywords TEXT[],
    entity_type TEXT,
    entity_id UUID,
    entity_name TEXT,
    confidence_score DECIMAL,
    created_at TIMESTAMPTZ,
    similarity FLOAT,
    rank FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic_search AS (
        SELECT 
            e.id,
            e.description,
            e.keywords,
            e.entity_type,
            e.entity_id,
            e.entity_name,
            e.confidence_score,
            e.created_at,
            1 - (e.embedding <=> query_embedding) AS similarity,
            ROW_NUMBER() OVER (ORDER BY e.embedding <=> query_embedding) AS rank
        FROM experience e
        WHERE e.is_validated = TRUE  -- Only validated experiences in search
            AND (p_entity_type IS NULL OR e.entity_type = p_entity_type)
            AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ),
    fulltext_search AS (
        SELECT 
            e.id,
            e.description,
            e.keywords,
            e.entity_type,
            e.entity_id,
            e.entity_name,
            e.confidence_score,
            e.created_at,
            ts_rank(e.search_vector, websearch_to_tsquery('english', query_text)) AS similarity,
            ROW_NUMBER() OVER (ORDER BY ts_rank(e.search_vector, websearch_to_tsquery('english', query_text)) DESC) AS rank
        FROM experience e
        WHERE e.is_validated = TRUE  -- Only validated experiences in search
            AND (p_entity_type IS NULL OR e.entity_type = p_entity_type)
            AND e.search_vector @@ websearch_to_tsquery('english', query_text)
    )
    SELECT 
        COALESCE(ss.id, fts.id) AS id,
        COALESCE(ss.description, fts.description) AS description,
        COALESCE(ss.keywords, fts.keywords) AS keywords,
        COALESCE(ss.entity_type, fts.entity_type) AS entity_type,
        COALESCE(ss.entity_id, fts.entity_id) AS entity_id,
        COALESCE(ss.entity_name, fts.entity_name) AS entity_name,
        COALESCE(ss.confidence_score, fts.confidence_score) AS confidence_score,
        COALESCE(ss.created_at, fts.created_at) AS created_at,
        COALESCE(ss.similarity, 0.0) + COALESCE(fts.similarity, 0.0) AS similarity,
        COALESCE(1.0 / (60 + ss.rank), 0.0) + COALESCE(1.0 / (60 + fts.rank), 0.0) AS rank
    FROM semantic_search ss
    FULL OUTER JOIN fulltext_search fts ON ss.id = fts.id
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- USEFUL VIEWS
-- ============================================================================

-- View: Active validation requests summary
CREATE VIEW active_validations AS
SELECT 
    vr.id,
    vr.proposal_id,
    p.proposal_title,
    vr.entity_type,
    vr.recipient_name,
    vr.recipient_email,
    vr.validation_status,
    vr.sent_at,
    vr.expires_at,
    CASE 
        WHEN vr.expires_at < NOW() THEN 'expired'
        WHEN vr.sent_at IS NULL THEN 'not_sent'
        ELSE 'active'
    END AS actual_status
FROM validation_requests vr
JOIN proposals p ON vr.proposal_id = p.id
WHERE vr.validation_status IN ('pending', 'sent')
ORDER BY vr.expires_at ASC;

-- View: Proposal resource summary
CREATE VIEW proposal_resources AS
SELECT 
    p.id AS proposal_id,
    p.proposal_title,
    p.proposal_status,
    jsonb_agg(
        DISTINCT jsonb_build_object(
            'type', 'internal',
            'id', ir.id,
            'name', ir.name,
            'resource_type', ir.resource_type,
            'hourly_rate', ir.hourly_rate
        )
    ) FILTER (WHERE ir.id IS NOT NULL) AS internal_resources,
    jsonb_agg(
        DISTINCT jsonb_build_object(
            'type', 'external',
            'id', er.id,
            'name', er.vendor_name,
            'vendor_type', er.vendor_type,
            'approval_status', er.approval_status
        )
    ) FILTER (WHERE er.id IS NOT NULL) AS external_resources
FROM proposals p
LEFT JOIN internal_resources ir ON ir.id = ANY(p.internal_resources_used)
LEFT JOIN external_resources er ON er.id = ANY(p.external_resources_used)
GROUP BY p.id, p.proposal_title, p.proposal_status;

-- View: Experience by entity (for quick lookups)
CREATE VIEW experience_by_entity AS
SELECT 
    e.entity_type,
    e.entity_id,
    e.entity_name,
    COUNT(*) AS experience_count,
    MAX(e.created_at) AS latest_experience_date,
    jsonb_agg(
        jsonb_build_object(
            'id', e.id,
            'description', e.description,
            'keywords', e.keywords,
            'confidence_score', e.confidence_score,
            'created_at', e.created_at
        ) ORDER BY e.created_at DESC
    ) AS experiences
FROM experience e
WHERE e.entity_type IS NOT NULL AND e.entity_id IS NOT NULL
GROUP BY e.entity_type, e.entity_id, e.entity_name;

-- View: Pending reviews (for admin review UI)
CREATE VIEW pending_reviews AS
SELECT 
    e.id,
    e.description,
    e.keywords,
    e.entity_type,
    e.entity_id,
    e.entity_name,
    e.confidence_score,
    e.source_type,
    e.source_id,
    e.created_at,
    e.created_by
FROM experience e
WHERE e.is_validated = FALSE
ORDER BY e.created_at DESC;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE internal_resources IS 'Staff, tools, assets, and facilities owned by the company. Admin-managed only.';
COMMENT ON TABLE external_resources IS 'External vendors and contractors with approval status. Admin-managed only.';
COMMENT ON TABLE policies IS 'Business rules and requirements for proposal generation. Admin-managed only.';
COMMENT ON TABLE experience IS 'AI-learned facts and knowledge updates. Primary AI-writable table. Only validated experiences appear in search.';
COMMENT ON TABLE validation_requests IS 'Tracks validation workflow via email/Teams. Stores raw responses for AI to process.';
COMMENT ON TABLE proposals IS 'Generated proposals with resource assignments and pricing.';
COMMENT ON TABLE audit_log IS 'Complete audit trail of all changes, especially AI updates to experience table.';

COMMENT ON COLUMN experience.confidence_score IS 'AI confidence in this knowledge (0.0-1.0). Lower scores may need human validation.';
COMMENT ON COLUMN experience.is_validated IS 'Only validated experiences appear in search results. Unvalidated entries go to review queue.';
COMMENT ON COLUMN experience.supersedes_experience_id IS 'Previous version of this experience if updated based on new information.';
COMMENT ON COLUMN validation_requests.expires_at IS 'Validation requests expire after 7 days by default.';
COMMENT ON COLUMN validation_requests.response_data IS 'Raw response data from user. AI processes this to create experience entries.';
