"""Tests for citation linkify helpers."""

from app.components.citations import linkify_citations, render_contradiction_cards


def test_linkify_known_source_id():
    sources = [{"id": "abc", "title": "Paper", "url": "https://example.com/a"}]
    out = linkify_citations("RAG helps [abc].", sources)
    assert out == "RAG helps [abc](https://example.com/a)."


def test_linkify_skips_existing_markdown_links():
    sources = [{"id": "abc", "title": "Paper", "url": "https://example.com/a"}]
    text = "See [abc](https://keep.me/x) please"
    assert linkify_citations(text, sources) == text


def test_linkify_unknown_id_unchanged():
    assert linkify_citations("Hi [missing].", []) == "Hi [missing]."


def test_contradiction_cards_html():
    html = render_contradiction_cards(
        [
            {
                "claim_a": "A says X",
                "claim_b": "B says Y",
                "similarity_score": 0.91,
                "source_a_id": "s1",
                "source_b_id": "s2",
                "explanation": "differs",
            }
        ]
    )
    assert "Claim A" in html
    assert "0.91" in html
    assert "A says X" in html
