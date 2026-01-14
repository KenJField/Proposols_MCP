"""Unit tests for keyword extraction."""

import pytest
from src.utils.keywords import extract_keywords


class TestKeywordExtraction:
    """Test keyword extraction functionality."""
    
    def test_extract_keywords_basic(self):
        """Test basic keyword extraction."""
        text = "Python developer with PostgreSQL database experience and FastAPI framework knowledge"
        keywords = extract_keywords(text)
        
        assert len(keywords) > 0
        assert "python" in [k.lower() for k in keywords]
        assert "postgresql" in [k.lower() for k in keywords]
        assert "fastapi" in [k.lower() for k in keywords]
    
    def test_extract_keywords_filters_stop_words(self):
        """Test that stop words are filtered out."""
        text = "This is a test with that and those words"
        keywords = extract_keywords(text)
        
        stop_words = ["this", "that", "those", "with", "and"]
        keyword_lower = [k.lower() for k in keywords]
        assert not any(word in keyword_lower for word in stop_words)
    
    def test_extract_keywords_max_limit(self):
        """Test that keyword extraction respects max limit."""
        text = " ".join([f"keyword{i}" for i in range(20)])
        keywords = extract_keywords(text, max_keywords=5)
        
        assert len(keywords) <= 5
    
    def test_extract_keywords_empty_text(self):
        """Test that empty text returns empty list."""
        keywords = extract_keywords("")
        assert keywords == []
    
    def test_extract_keywords_short_words_filtered(self):
        """Test that very short words are filtered out."""
        text = "a an the it is be"
        keywords = extract_keywords(text)
        
        # Should filter out words shorter than 4 characters
        assert all(len(k) >= 4 for k in keywords)
    
    def test_extract_keywords_sorts_by_length(self):
        """Test that keywords are sorted by length (longest first)."""
        text = "short word longerword longestkeyword"
        keywords = extract_keywords(text)
        
        # Should be sorted by length descending
        lengths = [len(k) for k in keywords]
        assert lengths == sorted(lengths, reverse=True)
