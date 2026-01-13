"""Keyword extraction utilities."""

import re
from typing import List


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract keywords from text using simple heuristics.
    
    For production, consider using spaCy, RAKE, or LLM-based extraction.
    
    Args:
        text: Input text to extract keywords from
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of extracted keywords
    """
    if not text:
        return []
    
    # Convert to lowercase and split into words
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    
    # Common stop words to filter out
    stop_words = {
        'that', 'this', 'with', 'from', 'have', 'been', 'will', 'would',
        'could', 'should', 'about', 'their', 'there', 'these', 'those',
        'which', 'where', 'when', 'what', 'them', 'they', 'than', 'then'
    }
    
    # Filter out stop words and get unique keywords
    keywords = list(set([w for w in words if w not in stop_words]))
    
    # Sort by length (longer words are often more specific) and return top N
    keywords.sort(key=len, reverse=True)
    
    return keywords[:max_keywords]
