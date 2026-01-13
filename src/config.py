"""Configuration management for the Proposal MCP Server."""

import os
from typing import Optional


class Config:
    """Application configuration from environment variables."""
    
    # Supabase configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # OpenAI configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Email configuration
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM: Optional[str] = os.getenv("EMAIL_FROM")
    
    # Teams configuration (optional)
    TEAMS_ACCESS_TOKEN: Optional[str] = os.getenv("TEAMS_ACCESS_TOKEN")
    TEAMS_WEBHOOK_SECRET: Optional[str] = os.getenv("TEAMS_WEBHOOK_SECRET")
    
    # Server configuration
    STATELESS_HTTP: bool = os.getenv("STATELESS_HTTP", "true").lower() == "true"
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration is present."""
        required = [
            ("SUPABASE_URL", cls.SUPABASE_URL),
            ("SUPABASE_SERVICE_ROLE_KEY", cls.SUPABASE_SERVICE_ROLE_KEY),
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
