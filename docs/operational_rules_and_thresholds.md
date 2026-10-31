# SurakshaVani: Operational Rules, Urgency Thresholds & Duplicate Detection Engine

## 1. Urgency Classification Matrix

In accordance with Maharashtra Cyber Crime Department protocols and I4C (Indian Cyber Crime Coordination Centre) guidelines, time is the single greatest determinant of whether fraudulent funds can be intercepted before hopping through mule bank accounts.

| Urgency Level | Criteria / Trigger Conditions | Immediate Automated Actions | Operator SLA |
| :--- | :--- | :--- | :--- |
| **CRITICAL** | 1. **Golden Hour Active**: Financial loss occurred within the last **60 minutes** (`now - incident_time <= 3600s`).<br>2. **Vulnerable Risk Flag**: Minor victim (`minor_involved == true`) OR active self-harm/suicide risk detected.<br>3. **High-Value Live Fraud**: Financial loss $\ge$ ₹1,00,000 within the last **120 minutes**.<br>4. **Active Sextortion / Imminent Threat**: Scammer threatening to release intimate media within 1-2 hours. | • Flash banner in Operator Console with audio chime.<br>• Auto-generate CFCFRMS Emergency Lien Export.<br>• Provide victim with 1-tap dialer to **1930** and bank fraud helpline.<br>• Dispatch immediate SMS/WhatsApp to Family Nominee (if opted in). | **< 3 minutes** |
| **HIGH** | 1. Financial loss occurred between **60 and 360 minutes** (1–6 hours ago).<br>2. Financial loss between ₹25,000 and ₹1,00,000.<br>3. Identity theft, fake police/customs "digital arrest" without physical hostage.<br>4. Loan app harassment with aggressive contact list calling. | • Queue at top of District Cyber Cell review queue.<br>• Auto-extract suspect identifiers (UPI IDs, bank account numbers, phone numbers).<br>• Generate ready-to-file complaint PDF summary. | **< 15 minutes** |
| **NORMAL** | 1. Financial loss > 6 hours ago.<br>2. Financial loss < ₹25,000.<br>3. Attempted scam where no money was transferred.<br>4. General phishing / suspicious link reports. | • Standard triage queue order.<br>• Aggregate into anonymized scam cluster intelligence pipeline. | **< 60 minutes** |

---

## 2. Duplicate Detection Engine & Window

To prevent denial-of-service, abuse, and accidental double-submissions while a victim is panicking, SurakshaVani implements a multi-tier duplicate prevention algorithm:

### Window Specifications
1. **Idempotency Window (10 minutes)**:
   - For webhooks and messaging channels, every incoming message UUID is cached in Redis with a 10-minute TTL. Re-sent webhooks from Meta/WhatsApp are ignored immediately.
2. **Active Incident Session Window (24 Hours)**:
   - If a citizen initiates a complaint, reports from the same phone number hash (`phone_hash`) within 24 hours are appended to the existing case file as additional evidence or comments rather than spawning duplicate police tickets.
3. **Cross-Reporter Suspect Collision Window (30 Days)**:
   - If an identifier (e.g. Scammer UPI ID `fraudster@ybl` or Phone `+91 9876543210`) was already reported by another victim in the last 30 days, the case is marked with `flag: REPEAT_OFFENDER` and automatically linked to the active investigative cluster, but both victims maintain distinct case reference IDs.

### Duplicate Scoring Algorithm
When a case is evaluated, a composite similarity score $S$ is calculated:
$$S = 0.40 \cdot \mathbb{I}_{\text{phone}} + 0.30 \cdot \mathbb{I}_{\text{upi\_or\_account}} + 0.20 \cdot \text{AmountMatch} + 0.10 \cdot \text{TimeProximity}$$
- If $S \ge 0.85$ within the same 24-hour window from the same reporter, the case is flagged as `REJECTED_DUPLICATE` with link to original ticket.
- If $0.50 \le S < 0.85$, the case is marked `UNDER_REVIEW` with an advisory note to the operator.

---

## 3. Rate Limiting and Abuse Prevention

1. **Per-Phone Rate Limit**:
   - Maximum **20 messages per minute** per hashed phone number.
   - Maximum **3 new cases per 24 hours** per phone number.
2. **Per-IP Rate Limit** (Web Simulator / Public Gateway):
   - Maximum **60 requests per minute** per `/24` subnet.
3. **Abuse Mitigation**:
   - If rate exceeded, system responds with catalog string `rate_limit_exceeded` and throttles requests for 15 minutes.
   - Critical 112/1930 emergency numbers are always displayed even if throttled.

---

## 4. Confidence Thresholds & Quality Gating

SurakshaVani never takes irreversible actions or submits low-confidence garbage to law enforcement databases.

1. **ASR (Speech-to-Text) Confidence Threshold**:
   - **Minimum Confidence**: $\ge 0.65$.
   - If ASR confidence $< 0.65$ or audio quality is low: The engine triggers the graceful fallback: *"We could not clearly hear your message due to background noise. Would you like to re-record, or choose quick buttons?"*
2. **Entity Extraction Confidence**:
   - `amount_inr`: Threshold $\ge 0.80$. Evidence quote must match words spoken.
   - `transaction_id`: Threshold $\ge 0.85$. Must conform to UTR / UPI / IMPS format (12-digit numeric or alphanumeric bank reference).
   - `suspect_identifier`: Validated against standard E.164 phone formats or VPA (`user@bank`) regex.
3. **Mandatory Read-Back Confirmation Rule**:
   - No case may enter `FORWARDED` status without explicit confirmation (`CONFIRM_YES`) by the victim, OR explicit operator manual verification on the console.

