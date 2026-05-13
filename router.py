"""
router.py

This module handles the routing logic for claims.
Based on the extracted fields and routing rules from the brief, it decides
where each claim should go and explains why.

Routing rules (from the assessment brief):
1. estimated_damage < 25000      → Fast-track
2. any mandatory field missing   → Manual Review
3. "fraud", "inconsistent", 
   "staged" in description       → Investigation Flag
4. claim_type == "injury"        → Specialist Queue

Note: If multiple rules match, we follow a priority order.
Investigation Flag > Specialist Queue > Manual Review > Fast-track
"""

# keywords that raise a red flag for fraud
FRAUD_KEYWORDS = ["fraud", "inconsistent", "staged", "suspicious", "fabricated"]

# the damage threshold for fast-tracking (from the brief)
FAST_TRACK_THRESHOLD = 25000


def _parse_damage_amount(damage_value) -> float | None:
    """
    Tries to parse the estimated damage into a float so we can compare it.
    Handles cases like "$8,500", "8500", "8500.00", etc.
    Returns None if it can't parse.
    """
    if damage_value is None:
        return None
    
    # if it's already a number, just return it
    if isinstance(damage_value, (int, float)):
        return float(damage_value)

    # clean up string — remove $, commas, spaces
    cleaned = str(damage_value).replace("$", "").replace(",", "").strip()
    
    # sometimes it might say "$8,500 (vehicle + medical)" — grab just the number
    # take everything before any space or parenthesis
    cleaned = cleaned.split()[0] if cleaned else cleaned
    cleaned = cleaned.split("(")[0].strip()

    try:
        return float(cleaned)
    except ValueError:
        return None


def _check_fraud_keywords(description: str) -> list:
    """
    Scans the description for any fraud-related keywords.
    Returns a list of matching keywords found.
    """
    if not description:
        return []
    
    desc_lower = description.lower()
    found = [kw for kw in FRAUD_KEYWORDS if kw in desc_lower]
    return found


def determine_route(extracted_fields: dict, missing_fields: list) -> dict:
    """
    Main routing function. Takes extracted fields + list of missing fields
    and returns a dict with recommendedRoute and reasoning.
    
    Returns:
    {
        "recommendedRoute": "Fast-track" | "Manual Review" | "Investigation Flag" | "Specialist Queue",
        "reasoning": "human readable explanation"
    }
    """
    
    reasoning_parts = []
    flags = []

    # --- Rule 3: Check description for fraud keywords (highest priority) ---
    description = extracted_fields.get("incident_information", {}).get("description", "") or ""
    fraud_hits = _check_fraud_keywords(description)
    if fraud_hits:
        flags.append("investigation")
        reasoning_parts.append(
            f"Fraud indicators detected in incident description — keywords found: {', '.join(fraud_hits)}."
        )

    # --- Rule 4: Check if claim type is injury ---
    claim_type = extracted_fields.get("claim_details", {}).get("claim_type", "") or ""
    if claim_type.strip().lower() == "injury":
        flags.append("specialist")
        reasoning_parts.append(
            "Claim type is 'Injury', which requires specialist handling for medical and liability assessment."
        )

    # --- Rule 2: Check for missing mandatory fields ---
    if missing_fields:
        flags.append("manual")
        reasoning_parts.append(
            f"The following mandatory fields are missing or incomplete: {', '.join(missing_fields)}. "
            "Manual review is required to collect this information before processing can continue."
        )

    # --- Rule 1: Check damage threshold for fast-track ---
    damage_raw = extracted_fields.get("asset_details", {}).get("estimated_damage")
    damage_amount = _parse_damage_amount(damage_raw)

    if damage_amount is not None and damage_amount < FAST_TRACK_THRESHOLD and not flags:
        flags.append("fast-track")
        reasoning_parts.append(
            f"Estimated damage of ${damage_amount:,.0f} is below the ${FAST_TRACK_THRESHOLD:,} threshold. "
            "No missing fields or flags detected. Eligible for fast-track processing."
        )
    elif damage_amount is not None and damage_amount >= FAST_TRACK_THRESHOLD and not flags:
        # above threshold but no other flags — still goes to standard review
        flags.append("manual")
        reasoning_parts.append(
            f"Estimated damage of ${damage_amount:,.0f} exceeds the ${FAST_TRACK_THRESHOLD:,} fast-track threshold. "
            "Routed to manual review for standard processing."
        )
    elif damage_amount is None and not flags:
        flags.append("manual")
        reasoning_parts.append(
            "Estimated damage value could not be determined. Manual review needed to validate the claim amount."
        )

    # --- Determine final route based on priority ---
    # Priority: Investigation > Specialist > Manual > Fast-track
    if "investigation" in flags:
        route = "Investigation Flag"
    elif "specialist" in flags:
        route = "Specialist Queue"
    elif "manual" in flags:
        route = "Manual Review"
    else:
        route = "Fast-track"

    # if multiple flags, mention that too
    if len(flags) > 1:
        reasoning_parts.append(
            f"Note: Multiple routing conditions were triggered ({', '.join(flags)}). "
            "The highest priority route has been selected."
        )

    return {
        "recommendedRoute": route,
        "reasoning": " ".join(reasoning_parts)
    }
