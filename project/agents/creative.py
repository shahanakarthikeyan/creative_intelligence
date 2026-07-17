"""Creative Agent — generates ad copy two ways:

1. run(brief) — the ORIGINAL automatic flow: template-based variants
   generated from the Strategist's top messaging gap. Used by the batch
   pipeline (orchestrator/pipeline.py) when fatigue is detected. Unchanged,
   no LLM key required.

2. generate_custom(inputs) — NEW on-demand flow: takes real inputs typed
   by the user (product, audience, offer, tone, CTA preference) and
   generates a professional, unique ad. Uses Groq (Llama) if GROQ_API_KEY
   is set for genuinely AI-written copy; otherwise falls back to a
   template-based generator that still personalizes using the user's
   actual inputs (not just brand/product like the old fallback).
"""
import json
import urllib.parse
import requests
from config import BRAND_NAME, BRAND_PRODUCT, GROQ_API_KEY, GROQ_MODEL
from utils.logger import get_logger

log = get_logger("creative")

# ============================================================
# ORIGINAL: automatic, fatigue-triggered generation (unchanged)
# ============================================================

TEMPLATES = {
    "social proof": [
        {"headline": "Join thousands who switched to {brand}",
         "body": "Real customers, real results. See why {brand} is the top-rated choice for {product}.",
         "cta": "See Reviews"},
        {"headline": "{brand}: rated by people just like you",
         "body": "Thousands of five-star reviews can't be wrong. Try {brand} risk-free today.",
         "cta": "Shop Now"},
        {"headline": "Everyone's asking about {brand}",
         "body": "Your friends already know. Find out what the buzz around {brand} is about.",
         "cta": "Get Yours"},
    ],
    "urgency": [
        {"headline": "{brand}: this week only",
         "body": "Stock is moving fast on our {product}. Don't wait until it's gone.",
         "cta": "Shop Now"},
        {"headline": "Last chance to grab {brand}",
         "body": "Limited units remaining at this price. Act before it sells out.",
         "cta": "Claim Offer"},
        {"headline": "Hours left on this {brand} deal",
         "body": "This offer disappears soon. Get yours before then.",
         "cta": "Get Yours"},
    ],
    "free_shipping": [
        {"headline": "{brand} ships free, every time",
         "body": "No minimums, no fine print. Just fast, free delivery on every order of {product}.",
         "cta": "Shop Now"},
        {"headline": "Free shipping, on us",
         "body": "{brand} covers the cost so you don't have to. Order today.",
         "cta": "Learn More"},
        {"headline": "Zero shipping fees at {brand}",
         "body": "What you see is what you pay. Free shipping, always included.",
         "cta": "Shop Now"},
    ],
    "convenience": [
        {"headline": "{brand}: {product}, delivered fast",
         "body": "Skip the hassle. Order {product} from {brand} and have it at your door in days.",
         "cta": "Shop Now"},
        {"headline": "The easy way to get {product}",
         "body": "{brand} makes it simple — a few taps and you're done.",
         "cta": "Get Yours"},
        {"headline": "{brand}: less hassle, more {product}",
         "body": "We handle the hard part so you don't have to.",
         "cta": "Learn More"},
    ],
}

FALLBACK = [
    {"headline": "{brand}: built different",
     "body": "See what makes {brand} the {product} choice people stick with.",
     "cta": "Learn More"},
    {"headline": "Why {brand} wins",
     "body": "We took the angle competitors are winning with and made it ours.",
     "cta": "Shop Now"},
    {"headline": "{brand} — try it for yourself",
     "body": "The angle competitors use most, now working for you.",
     "cta": "Get Yours"},
]


def run(brief: dict) -> list:
    """Original automatic flow — unchanged. Triggered by the batch
    pipeline when Fatigue Monitor detects a real problem."""
    if not brief.get("gaps"):
        log.info("Creative: no gaps found, nothing to generate")
        return []

    angle = brief["gaps"][0]["angle"]
    templates = TEMPLATES.get(angle, FALLBACK)

    variants = []
    for t in templates:
        variants.append({
            "headline": t["headline"].format(brand=BRAND_NAME, product=BRAND_PRODUCT),
            "body": t["body"].format(brand=BRAND_NAME, product=BRAND_PRODUCT),
            "cta": t["cta"],
            "angle": angle,
        })

    log.info("Creative: %d variant(s) generated for angle '%s' (rule-based)", len(variants), angle)
    return variants


# ============================================================
# NEW: on-demand generation from real user inputs
# ============================================================

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _build_prompt(inputs: dict) -> str:
    product = inputs.get("product", "").strip()
    audience = inputs.get("audience", "").strip()
    offer = inputs.get("offer", "").strip()
    tone = inputs.get("tone", "professional").strip()
    cta_pref = inputs.get("cta_preference", "").strip()

    return f"""You are a senior advertising copywriter. Write ONE unique, professional,
high-converting ad based on these real inputs:

Product/Service: {product}
Target Audience: {audience}
Key Offer / USP: {offer or "not specified — infer something reasonable from the product"}
Tone: {tone}
Preferred CTA style: {cta_pref or "choose the most effective option"}

Requirements:
- The headline must be under 10 words, punchy, and specific to this product — not generic.
- The body must be 2-3 sentences, written in the specified tone, and speak directly to the target audience.
- The CTA must be 2-4 words.
- Do NOT use placeholder brackets like [Product Name] — write it as a finished, ready-to-publish ad.
- Output ONLY valid JSON, no markdown, no commentary, in exactly this shape:
{{"headline": "...", "body": "...", "cta": "..."}}"""


def generate_with_groq(inputs: dict) -> dict:
    """Calls Groq's chat completions API (Llama model) for genuinely
    AI-written, unique ad copy grounded in the user's real inputs.
    Returns None on any failure so the caller can fall back to templates."""
    if not GROQ_API_KEY:
        return None

    prompt = _build_prompt(inputs)

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 400,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"].strip()

        # Strip accidental markdown code fences if the model adds them
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:].strip()

        ad = json.loads(raw_text)
        ad["source"] = "groq"
        log.info("Creative: Groq-generated ad for product '%s'", inputs.get("product"))
        return ad

    except Exception as e:
        log.warning("Groq generation failed, will fall back to template: %s", e)
        return None


def generate_from_template(inputs: dict) -> dict:
    """Fallback when Groq isn't configured or fails. Still personalizes
    using the user's real typed inputs rather than generic placeholders."""
    product = inputs.get("product", "your product").strip() or "your product"
    audience = inputs.get("audience", "").strip()
    offer = inputs.get("offer", "").strip()
    tone = inputs.get("tone", "professional").strip().lower()
    cta_pref = inputs.get("cta_preference", "").strip()

    audience_phrase = f" for {audience}" if audience else ""
    offer_phrase = f" {offer}." if offer else " Built to deliver real results."

    tone_openers = {
        "bold": f"{product.capitalize()} isn't for everyone{audience_phrase} — and that's the point.",
        "friendly": f"Meet your new favorite {product}{audience_phrase}.",
        "professional": f"Introducing {product}, designed{audience_phrase}.",
        "playful": f"Say hello to {product} — the one{audience_phrase} you'll actually love using.",
        "luxury": f"{product.capitalize()}, refined{audience_phrase}.",
    }
    headline = tone_openers.get(tone, tone_openers["professional"])

    cta = cta_pref if cta_pref else "Shop Now"

    return {
        "headline": headline[:70],
        "body": f"{product.capitalize()}{offer_phrase} Made with {audience or 'you'} in mind, from first use to every day after.",
        "cta": cta,
        "source": "template",
    }


def generate_ad_image_url(inputs: dict, ad: dict) -> str:
    """
    Builds a real generated ad image via Pollinations.ai — a free,
    no-API-key text-to-image service. Returns a direct image URL that
    can be used straight in an <img src="..."> tag; the image itself
    is generated on Pollinations' servers when that URL is requested.

    Style is chosen from the selected tone so the visual matches the
    copy (e.g. "luxury" -> premium studio photography look).
    """
    product = inputs.get("product", "product").strip() or "product"
    tone = inputs.get("tone", "professional").strip().lower()

    style_map = {
        "luxury": "elegant premium high-end product photography, soft studio lighting, minimalist background",
        "playful": "vibrant colorful fun illustration style, playful composition",
        "bold": "dramatic high-contrast dynamic advertising photography, bold colors",
        "friendly": "warm inviting lifestyle photography, natural light",
        "professional": "clean modern professional product photography, studio lighting, minimalist background",
    }
    style = style_map.get(tone, style_map["professional"])

    prompt = f"advertisement hero image for {product}, {style}, marketing creative, no text, no watermark, high quality"
    encoded_prompt = urllib.parse.quote(prompt)

    # A seed keeps the same product+tone combo visually consistent across
    # re-renders while still varying between different products/tones.
    seed = abs(hash(product + tone)) % 100000

    return (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=800&height=450&seed={seed}&nologo=true"
    )


def generate_custom(inputs: dict) -> dict:
    """
    Main entry point for the dashboard's on-demand Creative agent.
    Tries Groq first (real AI-generated copy); falls back to the
    personalized template generator on any failure. Always attaches
    a real generated ad image (Pollinations.ai) to the result.
    """
    result = generate_with_groq(inputs)
    if not result:
        result = generate_from_template(inputs)

    try:
        result["image_url"] = generate_ad_image_url(inputs, result)
    except Exception as e:
        log.warning("Image generation URL build failed: %s", e)
        result["image_url"] = None

    return result