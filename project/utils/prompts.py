"""utils/prompts.py — centralized prompt templates.

Kept separate from agent logic (analyst.py / creative.py) so prompts can be
tuned/versioned independently without touching the calling code.
"""

ANALYST_PROMPT = """You are an advertising analyst. Analyze this competitor ad and extract structured intelligence.

Ad headline: {headline}
Ad body: {body}
Ad format/platform: {format}

Return ONLY a JSON object with these exact keys:
- "angle": the core messaging angle in 1-3 words (e.g. "discount", "social proof", "urgency", "quality", "convenience")
- "hook": the specific hook or opening line used to grab attention
- "offer": the concrete offer being made (discount %, free trial, etc.) or "none" if there isn't one
- "cta": the call to action (e.g. "Shop Now", "Sign Up")

Respond with JSON only, no other text, no markdown fences."""


CREATIVE_PROMPT = """You are a senior direct-response copywriter for {brand}, a brand that sells {product}.

Competitor research shows ads using the "{angle}" messaging angle run significantly longer than average
(a strong signal of real performance), and {brand} has not tried this angle yet.

Generate 3 new ad variants for {brand} that use the "{angle}" angle. Give each variant a distinct hook.

Return ONLY a JSON object with this exact shape, no other text, no markdown fences:
{{
  "variants": [
    {{"headline": "...", "body": "...", "cta": "..."}},
    {{"headline": "...", "body": "...", "cta": "..."}},
    {{"headline": "...", "body": "...", "cta": "..."}}
  ]
}}"""
