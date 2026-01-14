"""Unit tests for email service."""

import pytest
from unittest.mock import patch, Mock
from src.services.email import (
    create_validation_email_html,
    send_html_email,
    generate_validation_token
)


class TestEmailService:
    """Test email validation service."""
    
    def test_create_validation_email_html(self):
        """Test HTML email creation."""
        html = create_validation_email_html(
            recipient_name="John Doe",
            question="Can this resource be allocated?",
            current_info={"name": "Jane Smith", "rate": "$150/hour"},
            entity_name="Jane Smith",
            response_url="https://example.com/validate/token123"
        )
        
        assert "John Doe" in html
        assert "Can this resource be allocated?" in html
        assert "Jane Smith" in html
        assert "token123" in html
        assert "<!DOCTYPE html>" in html
        assert "https://example.com/validate/token123" in html
    
    def test_create_validation_email_html_filters_sensitive_fields(self):
        """Test that sensitive fields are filtered from email."""
        html = create_validation_email_html(
            recipient_name="John",
            question="Test",
            current_info={
                "name": "Resource",
                "id": "secret-id",
                "embedding": [0.1] * 1536,
                "search_vector": "tsvector"
            },
            entity_name="Resource",
            response_url="https://example.com/validate/token"
        )
        
        assert "secret-id" not in html
        assert "embedding" not in html
        assert "search_vector" not in html
    
    def test_generate_validation_token(self):
        """Test validation token generation."""
        token = generate_validation_token("validation-id-123")
        
        assert isinstance(token, str)
        assert len(token) > 20  # Should be a substantial token
    
    @patch('src.services.email.smtplib.SMTP')
    def test_send_html_email_success(self, mock_smtp):
        """Test successful email sending."""
        from src.services import email
        
        # Patch Config attributes in the email module
        with patch.object(email.Config, 'SMTP_HOST', 'smtp.example.com'), \
             patch.object(email.Config, 'SMTP_PORT', 587), \
             patch.object(email.Config, 'SMTP_USER', 'user'), \
             patch.object(email.Config, 'SMTP_PASSWORD', 'pass'), \
             patch.object(email.Config, 'EMAIL_FROM', 'from@example.com'):
            
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            send_html_email(
                to_email="test@example.com",
                subject="Test Subject",
                html_body="<html><body>Test</body></html>"
            )
            
            mock_smtp.assert_called_once()
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
    
    def test_send_html_email_no_smtp_config(self, monkeypatch):
        """Test that missing SMTP config raises error."""
        monkeypatch.delenv("SMTP_HOST", raising=False)
        
        with pytest.raises(ValueError, match="SMTP configuration not available"):
            send_html_email(
                to_email="test@example.com",
                subject="Test",
                html_body="<html>Test</html>"
            )
