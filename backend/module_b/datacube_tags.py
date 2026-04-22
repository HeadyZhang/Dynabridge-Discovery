"""Three-dimensional tagging framework for Datacube.

Audience x Content x Context — predefined values ensure consistency
across all campaigns and brands.
"""

AUDIENCE_TAGS: dict[str, list[str]] = {
    "segment": [
        "self_disciplined_achiever", "tech_driven_upgrader", "trend_seeker",
        "budget_conscious", "premium_buyer", "first_time_buyer",
        "loyal_customer", "competitor_switcher",
    ],
    "motivation": [
        "health_wellness", "aesthetics", "social_status", "convenience",
        "value_for_money", "innovation", "self_expression", "safety",
    ],
    "need_state": [
        "functional", "emotional", "social", "aspirational",
    ],
    "geo_market": [
        "us", "us_northeast", "us_west", "europe", "uk", "germany",
        "japan", "southeast_asia", "australia", "global",
    ],
}

CONTENT_TAGS: dict[str, list[str]] = {
    "theme": [
        "professional_review", "lifestyle", "tutorial_howto", "comparison",
        "testimonial", "behind_the_scenes", "unboxing", "promotion_deal",
        "brand_story", "user_generated", "educational", "entertainment",
    ],
    "format": [
        "video_short_15s", "video_short_30s", "video_long_60s_plus",
        "image_single", "image_carousel", "article_blog",
        "infographic", "email", "story_24h", "live_stream",
    ],
    "message_type": [
        "educational", "emotional", "promotional", "social_proof",
        "urgency_scarcity", "aspirational", "problem_solution",
    ],
    "creative_approach": [
        "comparison_vs_competitor", "before_after", "expert_endorsement",
        "influencer_collab", "ugc_repost", "data_driven", "humor",
        "minimalist", "premium_cinematic",
    ],
}

CONTEXT_TAGS: dict[str, list[str]] = {
    "channel": [
        "youtube", "instagram", "tiktok", "facebook", "google_ads",
        "amazon_ads", "pinterest", "twitter_x", "email", "sms",
        "influencer", "podcast", "blog_seo", "reddit",
    ],
    "placement": [
        "feed", "stories", "reels", "search", "display", "shopping",
        "pre_roll", "mid_roll", "sidebar", "header",
    ],
    "funnel_stage": [
        "awareness", "consideration", "conversion", "retention", "advocacy",
    ],
}


def validate_tags(
    audience: dict[str, str],
    content: dict[str, str],
    context: dict[str, str],
) -> list[str]:
    """Validate tag values against predefined lists. Returns list of errors."""
    errors: list[str] = []
    for key, val in audience.items():
        if key in AUDIENCE_TAGS and val not in AUDIENCE_TAGS[key]:
            errors.append(f"Invalid audience.{key}: {val}")
    for key, val in content.items():
        if key in CONTENT_TAGS and val not in CONTENT_TAGS[key]:
            errors.append(f"Invalid content.{key}: {val}")
    for key, val in context.items():
        if key in CONTEXT_TAGS and val not in CONTEXT_TAGS[key]:
            errors.append(f"Invalid context.{key}: {val}")
    return errors
