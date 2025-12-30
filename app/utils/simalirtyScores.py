from math import sin, cos, atan2, radians, sqrt
from typing import Any, Dict, Tuple
from rapidfuzz import fuzz
from datetime import datetime

WEIGHTS = {
    "rag": 0.80,
    "geo": 0.80,
    "name": 0.8,
    "aadhaar": 0.05,
    "mobile": 0.05,
    "account": 0.03,
    "date": 0.5
}
_SUM_WEIGHTS = sum(WEIGHTS.values())  # 3.03



def haversine(lat1, lon1, lat2, lon2):
    if not lat1 or not lat2 or not lon1 or not lon2:
        return 300
    R = 6371000  # meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))


def geo_score(d_meters):

    if not d_meters:
        return 0.0
    if d_meters <= 20:
        return 1.0
    elif d_meters <= 50:
        return 0.8
    elif d_meters <= 100:
        return 0.5
    elif d_meters <= 200:
        return 0.3
    return 0.0


def name_similarity(a, b):
    if not a or not b:
        return 0.0
    return fuzz.token_sort_ratio(a, b) / 100.0

def aadhaar_score(a1, a2):
    if not a1 or not a2:
        return 0.0
    if a1 == a2:
        return 1.0
    return 0.0
def mobile_score(m1, m2):
    if not m1 or not m2:
        return 0.0
    if m1 == m2:
        return 1.0
    return 0.0


def date_score(submit1, incident1):
    fmt = "%Y-%m-%d"  # adjust if timestamp has time part
    try:
        d1 = abs((datetime.strptime(submit1, fmt) - datetime.strptime(incident1, fmt)).days)
        if d1 <= 3:
            return 1.0
        elif d1 <= 7 :
            return 0.8
        elif d1 <= 15:
            return 0.5
        return 0.0
    except:
        return 0.0

def account_score(acc1, acc2, ifsc1, ifsc2):
    if acc1 and acc2 and acc1 == acc2:
        return 1.0
    if acc1 and acc2 and acc1[-4:] == acc2[-4:]:
        return 0.8
    if ifsc1 and ifsc2 and ifsc1 == ifsc2:
        return 0.5
    return 0.0

def compute_final_score(query_meta: Dict[str, Any], match_meta: Dict[str, Any], rag_score: float) -> Tuple[float, str, Dict[str, float]]:
    """
    Compute normalized final score (0..1) and return the field that contributed most.
    Returns: (score, top_field_name, contributions_dict)
    """
    try:
        # sanitize rag_score into [0,1]
        rag = 0.0
        try:
            rag = float(rag_score) if rag_score is not None else 0.0
        except Exception:
            rag = 0.0
        rag = max(0.0, min(1.0, rag))

        # safe lat/long parsing
        def _safe_float(x):
            try:
                return float(x) if x is not None and str(x) != "" else None
            except Exception:
                return None

        qlat = _safe_float(query_meta.get("lat") if query_meta else None)
        qlon = _safe_float(query_meta.get("longitude") if query_meta else None)
        mlat = _safe_float(match_meta.get("lat") if match_meta else None)
        mlon = _safe_float(match_meta.get("longitude") if match_meta else None)

        try:
            d = haversine(qlat, qlon, mlat, mlon) if (qlat is not None and qlon is not None and mlat is not None and mlon is not None) else None
        except Exception:
            d = None

        # compute sub-scores (each in 0..1)
        s_geo = geo_score(d)
        s_name = 0.6 * name_similarity(query_meta.get("ApplicantName"), match_meta.get("ApplicantName")) + \
                 0.4 * name_similarity(query_meta.get("FatherSpouseName"), match_meta.get("FatherSpouseName"))
        s_aadhaar = aadhaar_score(query_meta.get("AadhaarNumber"), match_meta.get("AadhaarNumber"))
        s_mobile = mobile_score(query_meta.get("Mobile"), match_meta.get("Mobile"))
        s_date = date_score(query_meta.get("IncidentDate"), match_meta.get("IncidentDate"))
        s_account = account_score(
            query_meta.get("AccountNumber"), match_meta.get("AccountNumber"),
            query_meta.get("IFSCCode"), match_meta.get("IFSCCode")
        )

        # contributions = weight * subscore
        contribs = {
            "rag":     WEIGHTS.get("rag", 0.0)     * rag,
            "geo":     WEIGHTS.get("geo", 0.0)     * s_geo,
            "name":    WEIGHTS.get("name", 0.0)    * s_name,
            "aadhaar": WEIGHTS.get("aadhaar", 0.0) * s_aadhaar,
            "mobile":  WEIGHTS.get("mobile", 0.0)  * s_mobile,
            "account": WEIGHTS.get("account", 0.0) * s_account,
            "date":    WEIGHTS.get("date", 0.0)    * s_date,
        }

        total = sum(contribs.values())

        # normalize by sum of weights to keep final in 0..1
        normalized = total / _SUM_WEIGHTS if _SUM_WEIGHTS else 0.0
        normalized = max(0.0, min(1.0, normalized))
        normalized = round(normalized, 4)

        # pick top contributor by absolute contribution; if tie -> choose rag first priority
        top_field = max(contribs.items(), key=lambda kv: (kv[1], 1 if kv[0] == "rag" else 0))[0]

        return normalized, top_field, {k: round(v, 6) for k, v in contribs.items()}

    except Exception as e:
        #logging.exception("compute_final_score failed: %s", e)
        return 0.0, "error", {}