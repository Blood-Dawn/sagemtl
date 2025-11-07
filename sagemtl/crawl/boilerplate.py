"""Boilerplate removal and content extraction utilities."""

from __future__ import annotations

from typing import List, Optional, Sequence

from bs4 import BeautifulSoup


def extract_main_content(
    html: str,
    allow_selectors: Optional[Sequence[str]] = None,
    block_selectors: Optional[Sequence[str]] = None,
) -> str:
    """
    Extract main content from HTML, removing boilerplate elements.

    Args:
        html: Raw HTML content
        allow_selectors: CSS selectors for content to include (e.g., ['article', 'main'])
        block_selectors: CSS selectors for elements to remove (e.g., ['.sidebar', 'nav'])

    Returns:
        Extracted text content
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove blocked elements
    if block_selectors:
        for selector in block_selectors:
            for element in soup.select(selector):
                element.decompose()

    # Find allowed content
    if allow_selectors:
        content_parts: List[str] = []
        for selector in allow_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(separator="\n", strip=True)
                if text:
                    content_parts.append(text)

        if content_parts:
            return "\n\n".join(content_parts)

    # Fallback: get all text from body
    body = soup.find("body")
    if body:
        return body.get_text(separator="\n", strip=True)

    return soup.get_text(separator="\n", strip=True)
