# ANUGRAHA — Wildlife Compensation & Grievance Management System

**A statutory compensation backend for human–wildlife conflict in Chhattisgarh — a two-stage AI duplicate-and-fraud detection engine that catches the same incident filed twice under different spellings, and a six-level role-gated approval ladder that mirrors the Forest Department's real chain of command.**

---

## Table of Contents
- [The Problem](#the-problem)
- [Our Solution](#our-solution)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [The AI System — Duplicate & Fraud Detection](#the-ai-system--duplicate--fraud-detection)
- [Advanced Architectural Patterns](#advanced-architectural-patterns)
- [API Surface](#api-surface)
- [Getting Started](#getting-started)

---

## The Problem

When wildlife kills or injures a person, destroys a crop, or levels a house in and around Chhattisgarh's forest belt, the state pays **statutory compensation** from public funds. Elephant herds, tigers, leopards, sloth bears and wild boar make this a routine occurrence, not an exceptional one. Before this system, the process ran on paper.

A single claim means tracking, simultaneously:

- **Six levels of official review** — Forest Guard → Deputy Ranger → Ranger → SDO → DFO → accepted, each of which must happen in order and by the right officer.
- **Five distinct damage categories** — crop, house, cattle, human injury, human death — each with its own sub-amount, summing to one payable total.
- **A full jurisdiction path per claim** — Circle → division → subdivision → range → circle1 → beat — determining which officers may see it at all.
- **Citizen-supplied evidence** — photos, e-signatures, land records, sarpanch reports, bank and KYC details.

Four failures follow from doing this on paper, and they compound:

1. **Duplicate claims are financial leakage.** One elephant tramples one farm, and the incident gets filed three times — by the same person with a changed spelling, by a relative, by a different forest guard. Names transliterate inconsistently between Hindi and English; a fraudster alters one digit of a bank account; dates drift by a day. **Exact-match SQL cannot catch any of this**, and every miss is public money paid twice.
2. **The approval chain is unenforced.** A claim legally must climb a strict hierarchy of forest officers. On paper, files sat on desks, skipped levels, or vanished — and no record showed which.
3. **There is no defensible audit trail.** "Who approved this, at what rank, on what date, and with what comment?" had no answer that survived scrutiny years later, which is precisely when a public-funds disbursement gets questioned.
4. **A black-box fraud score is unusable in government.** Even a perfectly accurate flag is worthless if the reviewing officer cannot see *why* two claims were linked. An unexplainable model cannot be defended in an audit.

The hard part is not storing the claims. It is deciding **whether two claims that look different are secretly the same claim** — and making that judgment **explainable enough to defend in an audit**.

---

## Our Solution

ANUGRAHA is a **Flask + MySQL backend** serving two very different audiences: citizens who file without an account, and forest officers who act within a strict hierarchy. It treats every submitted claim as a **candidate duplicate requiring scoring**, and every status change as an **append-only audit event**.

- **Citizens file without logging in.** A complaint needs only a mobile number; the citizen tracks it later with `complaint_id + mobile` and downloads a government-formatted PDF.
- **Duplicate detection runs before money moves.** At submission, the claim is embedded, matched against prior claims by vector similarity, then re-ranked by a weighted blend of fuzzy names, GPS proximity and date proximity — surfacing likely duplicates to a human reviewer.
- **Every score is decomposed.** The engine returns the top contributing field and the full per-signal breakdown, so an officer sees "flagged on location + name," never just a number.
- **The hierarchy is enforced in code, not UI.** A form's `status` *is* the role level currently responsible for it. An officer may act only when `form.status == their_role_level` — a Ranger physically cannot touch a form sitting at the SDO's level.
- **Nothing is overwritten.** Every transition appends to an immutable `statusHistory` JSON log with actor, timestamp, new status and comment.
- **PII is kept out of the vector space deliberately.** Aadhaar, bank account, PAN, IFSC, mobile and email are excluded from the embedded text — a privacy decision *and* a correctness one.

The design principle throughout: **trust the signals that are hard to fake over the ones that are easy to fake.**

---

## Tech Stack

### Backend
- **Python 3.10 / Flask 3.1** — REST API, blueprint-per-domain routing
- **MySQL** (`mysql-connector-python`) — system of record, ~5 tables, parameterized queries throughout
- **PyJWT (HS256) / bcrypt** — token auth with expiry and refresh; salted password hashing
- **Flask-Limiter + Redis** — distributed rate limiting shared across Gunicorn workers

### AI Layer
- **ONNX Runtime** — CPU inference, no PyTorch dependency
- **`all-MiniLM-L6-v2`** sentence-transformer exported to ONNX — 384-dimensional embeddings, mean-pooled
- **Pinecone** (serverless, cosine) — vector index for semantic nearest-neighbour recall
- **`rapidfuzz`** — token-sort fuzzy string matching for transliterated names
- **NumPy + Haversine** — geodesic distance between incident coordinates

### Storage & Infrastructure
- **Firebase Storage** — uploaded documents, photos, and cached generated PDFs
- **ReportLab** — government-formatted A4 PDF generation
- **Resend** — transactional email to claimants
- **Docker** (`python:3.10-slim`) + **Gunicorn** — model files baked into the image; no runtime download
- **Railway** — app service, MySQL and Redis; secrets injected as environment variables

### Client Surfaces *(separate repos)*
- **React + Vite** — officer web portal and analytics dashboards, deployed on Vercel; CORS locked to known origins with `supports_credentials=True`
- **Android field app** — for Forest Guards and Deputy Rangers; **offline draft forms** with local storage, and **GPS boundary tracing** that walks a damaged field's perimeter to compute its area in sq-m and derive the crop damage amount

---

## Architecture

### Domain Blueprints

The API is split by domain, each mounted as a Flask blueprint in `backend.py`:

| Blueprint | Prefix | Responsibility |
|---|---|---|
| `registeration` | `/` | Registration, login, JWT issuance, refresh, password change |
| `complaints` | `/complaints` | Citizen grievance intake and lookup |
| `compensation` | `/compensationform` | Formal compensation forms, role/jurisdiction-scoped reads |
| `update_status` | `/update_form_status` | The approval state machine |
| `edit_payment` | `/edit` | Level-gated payment amount edits |
| `update_form` | `/update` | Form field corrections |
| `analytics` | `/` | Aggregated dashboards, damage/animal breakdowns, geo points |
| `admin` | `/admin` | Employee master records and role management |
| `guards` | `/guard` | Guard records and lookup |
| `verification` | `/verify` | Officer identity verification |
| `pdf` | `/` | Government-formatted PDF generation, cached to Firebase |
| `email` | `/email` | Transactional claimant email |

### Request Flow — a compensation form submission

```
Citizen / Officer client
  │
  ▼
[CORS]  origin allowlist, supports_credentials for the HttpOnly cookie
  │
  ▼
[@limiter]  Redis-backed rate limit
  │   └─ keyed per authenticated emp_id when logged in, per IP when anonymous
  │
  ▼
[@token_required]  Authorization: Bearer header → falls back to HttpOnly cookie
  │   └─ ownership check: token emp_id must match the target emp_id / forestGuardID
  │
  ▼
[Business logic]  parameterized SQL → MySQL
  │
  ├─► [form_text]  build canonical semantic text
  │        ├─ whitelist descriptive fields (incident details, crop, animal, address)
  │        └─ EXCLUDE Aadhaar / account / PAN / IFSC / mobile / email
  │
  ├─► [embeddings]  ONNX Runtime → mean-pool → 384-dim vector
  │
  ├─► [pinecone_store]  upsert by FormID, then top-K nearest neighbours
  │
  └─► [simalirtyScores]  weighted re-rank → score + per-field contribution
                │
                ▼
        duplicates surfaced to the reviewing officer BEFORE payment
```

### Approval Ladder

```
status  1   Forest Guard      (beat)
status  2   Deputy Ranger     (circle1)
status  3   Ranger            (range)
status  4   SDO               (subdivision)
status  5   DFO               (division)
status  6   ACCEPTED — terminal
status -1   REJECTED — terminal

gate:  an officer may act only when  form.status == their role level

accept     → status + 1      (escalate)
send_back  → status - 1      (floored at 2, bounce for corrections)
reject     → status = -1     (terminal)

every transition appends to statusHistory and mirrors onto the linked complaint
```

---

## The AI System — Duplicate & Fraud Detection

A **two-stage hybrid retrieval-and-scoring pipeline**. Stage 1 is semantic recall — fast, fuzzy, high-coverage. Stage 2 is precision re-ranking on structured signals. Neither alone is sufficient, and the reason why is the core design insight.

### Stage 0 — Canonical semantic text

**File:** `app/utils/form_text.py`

The raw form is never embedded. A canonical text is built first:

- **A whitelist of semantically meaningful fields** — free-text incident descriptions, injury details, crop type, animal name, address, jurisdiction path, dates.
- **An explicit `SENSITIVE_FIELDS` blacklist** — `AadhaarNumber`, `AccountNumber`, `PANNumber`, `IFSCCode`, `BankName`, `AccountHolderName`, `Mobile`, `email` are **never embedded**.
- Pure-number and currency-only values are stripped, whitespace collapsed, repeated blocks deduped, length truncated.

Embedding a raw form would let account numbers and boilerplate dominate the vector. Cleaning the input first is what makes the semantic signal actually about the *incident*.

### Stage 1 — Vector similarity (recall)

**Files:** `app/utils/embeddings.py`, `app/utils/pinecone_store.py`

The canonical text runs through `all-MiniLM-L6-v2` **exported to ONNX** and executed on CPU via ONNX Runtime. Token embeddings are **mean-pooled** into one **384-dimensional** vector, upserted into a **serverless Pinecone index (cosine)** keyed by `FormID`, with lightweight metadata attached. Querying returns the **top-K nearest neighbours** — narrowing the corpus to a handful of semantically similar candidates.

> **Why ONNX rather than PyTorch + `sentence-transformers`?** It drops the container image size and cold-start cost sharply, removes heavy GPU-oriented dependencies, and gives deterministic CPU inference — the right trade for a government-budget deployment on modest hardware. The model files ship **inside the Docker image**, so there is no runtime download and no external inference service to depend on.

### Stage 2 — Weighted multi-signal re-ranking (precision)

**File:** `app/utils/simalirtyScores.py`

Semantic similarity alone over-flags: every elephant crop-damage claim reads alike. The final score blends the vector score with structured-field signals:

| Signal | Computation | Weight |
|---|---|---:|
| **RAG / semantic** | Pinecone cosine score | `0.80` |
| **Geo proximity** | Haversine distance, bucketed — ≤20 m = 1.0, ≤50 m = 0.8, ≤100 m = 0.5, ≤200 m = 0.3 | `0.80` |
| **Name match** | `rapidfuzz` token-sort — 60% applicant name + 40% father/spouse name | `0.80` |
| **Date proximity** | days between incident dates — ≤3d = 1.0, ≤7d = 0.8, ≤15d = 0.5 | `0.50` |
| **Aadhaar** | exact match | `0.05` |
| **Mobile** | exact match | `0.05` |
| **Bank account** | exact, last-4, or IFSC match | `0.03` |

Each sub-score is `0–1`, multiplied by its weight, summed, and **normalized by the total weight (`3.03`)** to yield a clean `0–1` result.

**The weighting is the argument.** Identifiers like Aadhaar and bank account carry deliberately *low* weight — not because identity is unimportant, but because **one changed digit defeats them**. Geo and date proximity carry high weight because **you cannot fake having been at the same GPS coordinates on the same day**. Fuzzy name matching absorbs transliteration drift, so *Ramesh Kumar* and *Ramesh Kumaar* still match. The engine trusts hard-to-fake signals over easy-to-fake ones.

**Explainability is a first-class output.** Alongside the score, the engine returns the **top contributing field** and the **full contribution breakdown**, so a reviewing officer sees the reasoning, not a verdict. In a government audit context, that is the difference between a usable system and an unusable one.

---

## Advanced Architectural Patterns

### 1. Hybrid Recall-then-Rerank Retrieval
**Challenge:** Pure embeddings over-flag — all crop-damage claims are semantically alike. Pure exact-match under-flags — one altered digit defeats it entirely.

**Solution:** Two stages with opposite characteristics. Vector search over a Pinecone index provides cheap, high-recall candidate generation across the whole corpus; a weighted multi-signal re-ranker then applies precision using structured fields the embedding deliberately never saw. Recall and precision are solved by different mechanisms rather than by tuning one model to do both.

### 2. Adversarial Weighting of Fraud Signals
**Challenge:** Naive scoring trusts identifiers most, because they look authoritative — which is exactly backwards under adversarial conditions.

**Solution:** Weights are assigned by **cost-to-forge**, not by apparent authority. Aadhaar (`0.05`), mobile (`0.05`) and bank account (`0.03`) are trivially altered and weighted near zero. Geo proximity (`0.80`) and date proximity (`0.50`) are physically constrained and weighted heavily. The scoring function encodes a threat model.

### 3. PII Exclusion from the Vector Space
**Challenge:** Embedding whole forms leaks identifiers into a third-party vector store *and* pollutes semantic similarity with meaningless numeric tokens.

**Solution:** An explicit `SENSITIVE_FIELDS` blacklist removes Aadhaar, account number, PAN, IFSC, bank name, account holder, mobile and email before embedding. Identifiers are still compared — but by exact/last-4 matching in the re-ranker, where they belong. Privacy and retrieval quality improve from the same decision.

### 4. Level-Gated Approval State Machine
**Challenge:** "Approved" must mean a specific officer at a specific rank signed off, in order — and must survive scrutiny years later.

**Solution:** The form's `status` **is** the role level currently responsible for it. `update_status.py` maps roles to levels 1–5 and permits action only when `current_status == employee_level`. A Ranger cannot reach into level 2 or level 4. `accept` escalates `+1`, `send_back` bounces `-1` (floored at 2), `reject` terminates at `-1`, and 6 is terminal-accepted. The hierarchy is a server-side invariant, not a UI convention.

### 5. Append-Only Status History
**Challenge:** A mutable status field records the present but destroys the past — useless when a disbursement is questioned later.

**Solution:** Every transition appends to a `statusHistory` JSON log capturing actor, timestamp, new status and comment, mirrored onto the linked complaint, with `verifiedBy` accumulating the chain of approving `emp_id`s. The full life of a claim is reconstructible end to end.

### 6. Server-Side Recomputation of Payable Totals
**Challenge:** A client that submits its own total is a direct path to overpayment from public funds.

**Solution:** Payment edits are gated by role level and restricted to a **whitelist of editable sub-amount fields** (crop, house, cattle, injury, death). The total is **recomputed server-side** from those components on every write. A client-supplied total is never trusted.

### 7. Dual-Transport JWT Auth
**Challenge:** One auth system must serve a mobile client and a browser, which have opposing security constraints.

**Solution:** One HS256 JWT, two delivery mechanisms. Mobile receives it in the response body and returns it as a `Bearer` header; web receives a **Secure, HttpOnly, SameSite=None cookie** that JavaScript cannot read. `@token_required` checks the header first, then the cookie. **Authorization is a separate layer** — ownership checks require the token's `emp_id` to match the request's target, so a valid token still cannot act on another officer's data.

### 8. Identity-Aware Distributed Rate Limiting
**Challenge:** IP-based limits punish shared connections and fail entirely across multiple Gunicorn workers.

**Solution:** A custom key function limits **per authenticated `emp_id`** when a JWT is present and falls back to IP for anonymous traffic. **Redis** is the shared store, so limits hold across all workers and instances. Defaults of `1000 per day` and `200 per hour` are tightened per endpoint — login and complaint submission at `5 per minute`, password update at `1 per day`.

### 9. Idempotent Cached PDF Generation
**Challenge:** Regenerating a multi-page ReportLab PDF on every download wastes CPU and returns a subtly different file each time.

**Solution:** Generated PDFs are cached to **Firebase Storage**; if one already exists for a claim, the stored URL is returned unchanged. Generation is idempotent, and the document a citizen downloads today matches the one an auditor retrieves later.

### 10. Measured Area Over Asserted Area
**Challenge:** Crop damage payouts are computed from affected area. An officer typing "2 acres" into a form produces a number nothing can check, and it directly sets the amount paid.

**Solution:** The field app captures area by **GPS boundary tracing** — the officer walks the perimeter, the app closes the polygon and computes the enclosed area in sq-m, which drives the damage amount. GPS is a receiver rather than a network service, so this runs **entirely offline** and the form is held as a local draft until connectivity returns. The backend stores the resulting area alongside the incident's lat/long, and the same coordinates later feed the Haversine proximity signal in duplicate detection. This is the same principle as the fraud weighting: **prefer evidence that is physically hard to fake over a value someone asserts.**

---

## API Surface

**32 endpoints** across 12 blueprints. Officer routes require a valid JWT via `@token_required`, which resolves the caller's `emp_id` and role; citizen-facing complaint routes are deliberately unauthenticated and rate-limited instead.

Representative endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/complaints/submit_complaint` | Citizen files a grievance (no login) |
| `POST` | `/complaints/get_complaint` | Track a claim by `complaint_id` + mobile |
| `POST` | `/complaints/get_guard_complaints` | Complaints assigned to a guard |
| `POST` | `/compensationform` | Create a formal compensation form |
| `GET` | `/compensationform/<role>/<emp_id>` | Role- and jurisdiction-scoped claim list |
| `POST` | `/update_form_status/<form_id>` | Advance / reject / send back a claim |
| `POST` | `/edit/<form_id>` | Level-gated payment amount edit |
| `POST` | `/users/check_user` | Authenticate; issues JWT via body and cookie |
| `GET` | `/guard/<mobile_number>` | Guard lookup by mobile |
| `POST` | `/verify/verify_guard` | Verify an officer by emp_id, mobile and role |

**Response envelope** — uniform across the API:
```json
{ "error": false, "message": "...", "result": {} }
```

---

## Getting Started

```bash
pip install -r requirements.txt
```

Create a `.env` in the project root — it is gitignored and must never be committed:

```env
# Database
DB_HOST=...
DB_USER=...
DB_PASSWORD=...
DB_NAME=...
DB_PORT=...

# Auth
SECRET_KEY=...

# Redis (rate limiting)
REDIS_URL=redis://...

# Firebase
GOOGLE_APPLICATION_CREDENTIALS_JSON={...}
FIREBASE_CERT_PATH=...

# Pinecone
PINECONE_API_KEY=...
PINECONE_ENV=...
PINECONE_INDEX=...

# Email
RESEND_API_KEY=...

# Model
MODEL_DIR=onnx_model
```

Run:
```bash
python backend.py
```

Production:
```bash
gunicorn --bind 0.0.0.0:8000 backend:app --workers 2 --timeout 60
```

Docker:
```bash
docker build -t anugraha .
docker run -p 8000:8000 --env-file .env anugraha
```

---

**Last Updated**: September 2026
