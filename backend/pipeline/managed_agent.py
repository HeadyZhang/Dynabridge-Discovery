"""Claude Managed Agents integration for competitor discovery.

Uses the Managed Agents API (beta) to run an autonomous research agent
with web_search tool — replacing fragile Playwright scraping.

The agent and environment are created once and reused across sessions.
Each competitor discovery request creates a new session.

Requires: anthropic SDK 0.40+ (for API key), httpx (for raw API calls).
Beta header: managed-agents-2026-04-01
"""
import json
import re
import asyncio
import httpx
from config import ANTHROPIC_API_KEY

API_BASE = "https://api.anthropic.com/v1"
BETA_HEADER = "managed-agents-2026-04-01"

# Cached agent/environment IDs (created once per process)
_agent_id: str | None = None
_environment_id: str | None = None


def _headers() -> dict:
    return {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": BETA_HEADER,
        "content-type": "application/json",
    }


def _ensure_agent_sync() -> tuple[str, str]:
    """Create or return cached agent + environment IDs (blocking)."""
    global _agent_id, _environment_id
    if _agent_id and _environment_id:
        return _agent_id, _environment_id

    with httpx.Client(timeout=30) as client:
        # Create the competitor research agent
        resp = client.post(
            f"{API_BASE}/agents",
            headers=_headers(),
            json={
                "name": "DynaBridge Competitor Researcher",
                "model": "claude-sonnet-4-6",
                "system": (
                    "You are a competitive intelligence researcher for a brand consulting firm. "
                    "Your job is to identify and research competitors for a given brand.\n\n"
                    "When given a brand name and context:\n"
                    "1. Use web_search to find competitors in the same category\n"
                    "2. Search for '[brand] competitors', '[category] brands', and marketplace listings\n"
                    "3. For each competitor found, determine their market role and relevance\n"
                    "4. Return a structured JSON result\n\n"
                    "Always return your final answer as a JSON code block with this structure:\n"
                    "```json\n"
                    '{"competitors": [{"name": "Brand", "category_role": "direct|aspirational|adjacent", '
                    '"reason": "why they compete", "confidence": 0.9}]}\n'
                    "```\n"
                    "Find 6-10 competitors. Be specific about names (official capitalization)."
                ),
                "tools": [{"type": "web_search_20250305"}],
            },
        )
        resp.raise_for_status()
        _agent_id = resp.json()["id"]

        # Create environment
        resp = client.post(
            f"{API_BASE}/environments",
            headers=_headers(),
            json={
                "name": "competitor-research-env",
                "config": {
                    "type": "cloud",
                    "networking": {"type": "unrestricted"},
                },
            },
        )
        resp.raise_for_status()
        _environment_id = resp.json()["id"]

    return _agent_id, _environment_id


async def discover_competitors_managed(
    brand_name: str,
    brand_url: str = "",
    category_context: str = "",
    max_competitors: int = 8,
) -> list[dict]:
    """Run a Managed Agent session to discover competitors.

    Returns:
        [{"name": str, "source": "managed_agent", "confidence": float,
          "category_role": str, "reason": str}]
    """
    if not ANTHROPIC_API_KEY:
        return []

    # Ensure agent + environment exist (blocking, but cached after first call)
    agent_id, env_id = await asyncio.to_thread(_ensure_agent_sync)

    # Build the research prompt
    prompt = (
        f"Research competitors for the brand '{brand_name}'.\n"
        f"Website: {brand_url}\n"
    )
    if category_context:
        prompt += f"Category context: {category_context}\n"
    prompt += (
        f"\nFind {max_competitors} real competitors. Search for:\n"
        f"- '{brand_name} competitors'\n"
        f"- The product category this brand operates in\n"
        f"- Amazon and e-commerce listings in the same category\n"
        f"- Industry analysis or comparison articles\n\n"
        "Return the JSON result with the competitors array."
    )

    # Create session + send message + collect response
    result_text = await asyncio.to_thread(
        _run_session_sync, agent_id, env_id, brand_name, prompt
    )

    return _parse_competitor_result(result_text, max_competitors)


def _run_session_sync(
    agent_id: str, env_id: str, brand_name: str, prompt: str
) -> str:
    """Create a session, send message, and collect streamed text (blocking)."""
    headers = _headers()

    with httpx.Client(timeout=300) as client:
        # Create session
        resp = client.post(
            f"{API_BASE}/sessions",
            headers=headers,
            json={
                "agent": agent_id,
                "environment_id": env_id,
                "title": f"Competitor research: {brand_name}",
            },
        )
        resp.raise_for_status()
        session_id = resp.json()["id"]

        # Send user message
        client.post(
            f"{API_BASE}/sessions/{session_id}/events",
            headers=headers,
            json={
                "events": [
                    {
                        "type": "user.message",
                        "content": [{"type": "text", "text": prompt}],
                    },
                ],
            },
        )

    # Stream response via SSE
    collected_text = []
    sse_headers = {**headers, "Accept": "text/event-stream"}
    del sse_headers["content-type"]

    with httpx.Client(timeout=300) as client:
        with client.stream(
            "GET",
            f"{API_BASE}/sessions/{session_id}/stream",
            headers=sse_headers,
        ) as response:
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                    evt_type = event.get("type", "")

                    if evt_type == "agent.message":
                        for block in event.get("content", []):
                            if block.get("type") == "text":
                                collected_text.append(block.get("text", ""))

                    elif evt_type == "session.status_idle":
                        break
                except json.JSONDecodeError:
                    continue

    return "".join(collected_text)


def _parse_competitor_result(text: str, max_count: int) -> list[dict]:
    """Extract competitor list from agent's JSON response."""
    # Look for ```json ... ``` block first
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        raw = json_match.group(1)
    else:
        # Try to find raw JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            raw = text[start:end]
        else:
            return []

    try:
        data = json.loads(raw)
        competitors = data.get("competitors", [])
        result = []
        for c in competitors[:max_count]:
            result.append({
                "name": c.get("name", "Unknown"),
                "source": "managed_agent",
                "confidence": float(c.get("confidence", 0.8)),
                "url": c.get("url"),
                "category_role": c.get("category_role", "direct"),
                "reason": c.get("reason", ""),
            })
        return result
    except (json.JSONDecodeError, ValueError, AttributeError):
        return []
