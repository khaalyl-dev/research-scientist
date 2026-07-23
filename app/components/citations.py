"""Citation helpers — turn Teacher [source_id] markers into markdown links."""

from __future__ import annotations

import html
import re
from typing import Any


def build_source_url_map(sources: list[Any]) -> dict[str, dict[str, str]]:
    """Map source id → {title, url}."""
    mapping: dict[str, dict[str, str]] = {}
    for src in sources or []:
        if isinstance(src, dict):
            sid = str(src.get("id") or "")
            title = str(src.get("title") or "Source")
            url = str(src.get("url") or "")
        else:
            sid = str(getattr(src, "id", "") or "")
            title = str(getattr(src, "title", "Source") or "Source")
            url = str(getattr(src, "url", "") or "")
        if sid:
            mapping[sid] = {"title": title, "url": url}
    return mapping


_CITATION_RE = re.compile(r"\[([^\]]+)\]")


def linkify_citations(markdown: str, sources: list[Any]) -> str:
    """Replace [source_id] with markdown links when a matching source URL exists.

    Leaves normal markdown links like [label](url) alone (skip match followed by '(').
    """
    if not markdown:
        return markdown
    mapping = build_source_url_map(sources)
    if not mapping:
        return markdown

    parts: list[str] = []
    i = 0
    while i < len(markdown):
        m = _CITATION_RE.search(markdown, i)
        if not m:
            parts.append(markdown[i:])
            break
        parts.append(markdown[i : m.start()])
        after = m.end()
        if after < len(markdown) and markdown[after] == "(":
            parts.append(m.group(0))
        else:
            sid = m.group(1)
            info = mapping.get(sid)
            if info and info.get("url"):
                parts.append(f"[{sid}]({info['url']})")
            else:
                parts.append(m.group(0))
        i = after
    return "".join(parts)


def render_contradiction_cards(contradictions: list[dict]) -> str:
    """HTML cards for claim A vs claim B (US-05 UI)."""
    if not contradictions:
        return ""
    cards: list[str] = []
    for i, item in enumerate(contradictions, 1):
        claim_a = html.escape(str(item.get("claim_a") or ""))
        claim_b = html.escape(str(item.get("claim_b") or ""))
        score = item.get("similarity_score", item.get("divergence_score", "?"))
        try:
            score_s = f"{float(score):.2f}"
        except (TypeError, ValueError):
            score_s = str(score)
        src_a = html.escape(str(item.get("source_a_id") or "?"))
        src_b = html.escape(str(item.get("source_b_id") or "?"))
        expl = html.escape(str(item.get("explanation") or ""))
        expl_html = (
            f"<p class='ars-muted' style='margin-top:0.5rem;'>{expl}</p>" if expl else ""
        )
        cards.append(
            f"""
<div class="ars-panel" style="margin-top:0.75rem;">
  <h3 class="ars-panel-title">Contradiction {i}</h3>
  <p class="ars-muted" style="margin-bottom:0.5rem;">
    Similarité cosine&nbsp;: <strong>{score_s}</strong>
    · sources <code>{src_a}</code> vs <code>{src_b}</code>
  </p>
  <p style="margin:0.35rem 0;"><strong>Claim A</strong> — {claim_a}</p>
  <p style="margin:0.35rem 0;"><strong>Claim B</strong> — {claim_b}</p>
  {expl_html}
</div>
"""
        )
    return "\n".join(cards)
