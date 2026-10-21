"""Read explicit numeric constraints without inferring bounds from a center point."""

import re


BOUNDING_BOX_FIELDS = ("swlat", "swlng", "nelat", "nelng")
_NUMBER = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
_DATE = r"\d{4}-\d{2}-\d{2}"


def requires_bounding_box(request: str) -> bool:
    return bool(re.search(
        r"\b(?:bounding[\s_-]*box|boundary[\s_-]*box|bbox|swlat|swlng|nelat|nelng)\b",
        request, re.IGNORECASE,
    ))


def explicit_search_constraints(request: str) -> dict:
    """Extract only labelled coordinates and explicit date intervals for validation."""
    constraints = {}
    for field in BOUNDING_BOX_FIELDS:
        match = re.search(
            rf"\b{field}\b\s*[=:]\s*({_NUMBER})(?![\d.])",
            request, re.IGNORECASE,
        )
        if match:
            constraints[field] = float(match[1])

    for label, lower, upper in (
        (r"(?:decimalLatitude|latitude)", "swlat", "nelat"),
        (r"(?:decimalLongitude|longitude)", "swlng", "nelng"),
    ):
        match = re.search(
            rf"\b{label}\b\s*(?:(?:from|between)\s+)?[=:]?\s*"
            rf"({_NUMBER})\s*(?:to|through|and|–|—)\s*({_NUMBER})(?![\d.])",
            request, re.IGNORECASE,
        )
        if match:
            # Explicit API field names take precedence over descriptive ranges.
            constraints.setdefault(lower, float(match[1]))
            constraints.setdefault(upper, float(match[2]))

    for field in ("d1", "d2"):
        match = re.search(rf"\b{field}\b\s*[=:]\s*({_DATE})\b", request)
        if match:
            constraints[field] = match[1]
    interval = re.search(
        rf"\b({_DATE})\s*(?:to|through|until|–|—)\s*({_DATE})\b",
        request, re.IGNORECASE,
    )
    if interval:
        constraints.setdefault("d1", interval[1])
        constraints.setdefault("d2", interval[2])
    if "d1" not in constraints and "d2" not in constraints:
        year = re.search(
            r"\b(?:for|during|in)\s+(?:the\s+)?(?:(?:full|entire|whole)\s+)?"
            r"(?:year\s+)?((?:19|20)\d{2})\b",
            request, re.IGNORECASE,
        )
        if year:
            constraints.update(d1=f"{year[1]}-01-01", d2=f"{year[1]}-12-31")
    return constraints
