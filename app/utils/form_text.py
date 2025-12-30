# app/utils/form_text.py
import re
from typing import Dict

# Fields chosen because they contain natural language descriptions that matter semantically.
# Order matters: put the most descriptive fields first.
SEMANTIC_FIELDS = [
    "ApplicantName",            # may help if family names/prefixes useful
    "FatherSpouseName",
    "AdditionalDetails",        # free-text incident description
    "TemporaryInjuryDetails",
    "PermanentInjuryDetails",
    "FullHouseDamage",
    "PartialHouseDamage",
    "HouseDamageAmount",        # numeric — will be filtered to avoid noise (kept only if contains words)
    "CropType",
    "CerealCrop",
    "AnimalName",
    "CropDamageArea",
    "CropDamageAmount",         # numeric — filtered
    "TemporaryInjuryDetails",
    "propertyOwnerReport",
    "landOwnershipReport",
    "rorReport",
    "nocReport",
    "sarpanchReport",
    "pmReport",
    "AdditionalDetails",        # redundant-safe: will dedupe below
    "comments",
    "Address",
    "beat",
    "range_",
    "division",
    "subdivision",
    "IncidentDate",             # keep date text (can be normalized)
    "SubmissionDateTime"        # optional context
]

# Sensitive / identifying fields we must NOT include in semantic text:
SENSITIVE_FIELDS = {
    "AadhaarNumber", "AccountNumber", "PANNumber",
    "IFSCCode", "BankName", "AccountHolderName", "Mobile", "email"
}

# helper regex
_RE_PURE_NUMBER = re.compile(r"^[\d\.,\s\-]+$")  # strings that are only numbers/punctuation
_RE_WHITESPACE = re.compile(r"\s+")

def _clean_value(val: any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    # remove excessive whitespace/newlines
    s = _RE_WHITESPACE.sub(" ", s)
    # filter out pure numbers / currency-only values (they don't help semantic matching)
    if _RE_PURE_NUMBER.fullmatch(s):
        return ""
    # remove long strings of punctuation
    s = re.sub(r"[^\w\s\-\.,:()\/]", " ", s)
    s = _RE_WHITESPACE.sub(" ", s).strip()
    # limit length per field
    if len(s) > 1000:
        s = s[:1000] + "..."
    return s

def build_canonical_form_text(form: Dict[str, any]) -> str:
    """
    Build a canonical text for semantic embeddings:
    - only selected semantic fields
    - drop sensitive identifiers and pure numeric noise
    - normalize whitespace and truncate
    """
    parts = []
    seen = set()

    # prefer fields in SEMANTIC_FIELDS order
    for key in SEMANTIC_FIELDS:
        if key in SENSITIVE_FIELDS:
            continue
        val = form.get(key)
        cleaned = _clean_value(val)
        if not cleaned:
            continue
        # dedupe identical text blocks
        if cleaned in seen:
            continue
        seen.add(cleaned)
        parts.append(f"{key}: {cleaned}")

    # As a fallback, include 'ApplicantName' or 'AdditionalDetails' from any other keys
    # Iterate extra keys if nothing collected yet
    if not parts:
        for k, v in form.items():
            if k in SENSITIVE_FIELDS or k in SEMANTIC_FIELDS:
                continue
            cleaned = _clean_value(v)
            if cleaned:
                parts.append(f"{k}: {cleaned}")
                if len(parts) >= 6:
                    break

    # join with clear separator
    canonical = " ||| ".join(parts)
    # final truncation to avoid huge inputs to embedding model
    MAX_LEN = 3000
    if len(canonical) > MAX_LEN:
        canonical = canonical[:MAX_LEN] + "..."
    return canonical
