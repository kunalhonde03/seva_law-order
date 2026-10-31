# SurakshaVani: Operator Console & Intelligence Portal — UX Wireframes & Specifications

## 1. Design Philosophy for Law Enforcement & Cyber Desk Officers

Rather than cluttering screens with superficial "KPI cards" or flashy animations, SurakshaVani's console is engineered as a **mission-critical, high-utility tactical terminal** designed for 1930 operators and Maharashtra Cyber Cell inspectors.

### Key Principles:
1. **Golden-Hour Dominance**: Triage queues prioritize cases where money was lost in $< 60$ minutes with a dynamic countdown timer indicating the lien window before cashout at ATMs.
2. **Confidence Transparency**: Every extracted field shows its verbatim quote and an extraction confidence tag (High $\ge 0.85$, Medium $0.65-0.84$, Low $<0.65$). Officers can inline-edit fields without navigating away.
3. **One-Action Dispatch**: Pre-formatted CFCFRMS and bank lien payloads are one click away, copyable with standardized formatting for direct insertion into inter-bank clearing networks.
4. **Non-Intrusive Theme**: Clean, high-contrast, dark-mode ready, uncluttered UI adhering to India Enterprise Architecture (IndEA) accessibility standards.

---

## 2. Console Screen 1: Operator Triage & Live Queue

### Screen Wireframe Layout
```text
+--------------------------------------------------------------------------------------------------------------------+
| MAHARASHTRA CYBER CRIME CELL | SURAKSHAVANI OPERATOR TERMINAL             [District: Mumbai City v] [Off. S. Shinde] |
+--------------------------------------------------------------------------------------------------------------------+
| Filters: [All Statuses v]  [Urgency: Critical/High v]  [Category: All v]  [Search ref, phone, UPI, UTR...        ] |
+--------------------------------------------------------------------------------------------------------------------+
| GOLDEN-HOUR ACTIVE (Money Moved < 60 mins ago — Immediate Bank Lien Priority)                                     |
| Ref No.         Time Left  Amount     Victim Bank       Suspect UPI / Phone       Category      Conf.  Action      |
| ------------------------------------------------------------------------------------------------------------------ |
| SV-202610-0912  ⚡ 18m left ₹50,000   Bank of Maha      paytm-9823412345@paytm    MSEDCL KYC    98%    [Review Case]|
| SV-202610-0894  ⚡ 34m left ₹1,20,000 HDFC Bank         8877112233 / Axis Acc    Pension OTP   95%    [Review Case]|
+--------------------------------------------------------------------------------------------------------------------+
| ACTIVE INVESTIGATION QUEUE                                                                                         |
| Ref No.         Reported   Amount     Victim District   Suspect Identifier        Category      Status     Action    |
| ------------------------------------------------------------------------------------------------------------------ |
| SV-202610-0872  2h ago     ₹1,00,000  Pune Rural        payfast@icici             Telegram Job  NEW        [Review]  |
| SV-202610-0850  4h ago     ₹0 (Threat)Nagpur Urban      +91 9711223344            Sextortion    UNDER_REV  [Review]  |
| SV-202610-0810  Yesterday  ₹24,500    Thane Comm.       olx-seller@ybl            Fake Rental   FORWARDED  [Review]  |
+--------------------------------------------------------------------------------------------------------------------+
| System Notice: CFCFRMS Relay Online | 1930 API Gateway: Healthy | Total Unreviewed: 4 | Critical Escalations: 2    |
+--------------------------------------------------------------------------------------------------------------------+
```

---

## 3. Console Screen 2: Case Detail & Verified Handoff View

### Screen Wireframe Layout (Three-Column Triage View)
```text
+--------------------------------------------------------------------------------------------------------------------+
| < BACK TO QUEUE   Case Ref: SV-202610-0912 | Urgency: CRITICAL [⚡ 18 mins left in Golden Hour]  [Export Official PDF] |
+--------------------------------------------------+----------------------------------+------------------------------+
| COLUMN 1: STRUCTURED COMPLAINT DOSSIER           | COLUMN 2: CITIZEN EVIDENCE & ASR | COLUMN 3: DISPATCH & ACTIONS |
+--------------------------------------------------+----------------------------------+------------------------------+
| Status: [UNDER_REVIEW v] [Save Changes]          | Voice Note Audio Player:         | CFCFRMS / 1930 LIEN DISPATCH |
| Category: Financial Fraud                        | [ >  ====o========= 0:24 / 0:42 ]| Target: Bank of Maharashtra  |
| Subtype: MSEDCL Meter Disconnection Scam         | Audio Integrity: SHA256 Verified | Beneficiary: Axis Bank       |
|                                                  |                                  | Pre-filled Lien Request:     |
| Incident Time: 2026-10-31 14:30 IST [Verified]   | Original Marathi Transcript:     | "URGENT LIEN REQUEST UNDER   |
| Loss Amount:   ₹50,000.00          [Verified]    | "मला आज दुपारी अडीच वाजता एका...  | SEC 91 CrPC / CFCFRMS ID     |
| Payment Method:UPI (Google Pay)                  | महावितरण ऑफिसमधून बोलतोय, वीज    | REF: SV-202610-0912          |
| Victim Bank:   Bank of Maharashtra               | कापली जाईल... ५०,००० रुपये कट... | Amount: INR 50,000           |
| Transaction UTR: 429182736152                    | UTR: 429182736152"               | UTR: 429182736152"           |
|                                                  |                                  | [ COPY LIEN TEXT ]           |
| Suspect Contact: +91 9823412345                  | AI Dual-Language Summary:        | [ DISPATCH TO 1930 DESK ]    |
| Suspect UPI:     msedcl-billpay@axisbank         | Local: तक्रारदाराला वीज बिल...     |                              |
| Claimed Identity: MSEDCL Mahavitaran Officer     | English: Victim was coerced by an| EVIDENCE VAULT (2 files):    |
|                                                  | impersonator posing as MSEDCL... | • screenshot_gpay_utr.png    |
| Victim Contact (Decrypted for authorized officer)|                                  | • call_recording_clip.wav    |
| Name: [Kishore Patil] Phone: [+91 98900 11223]   | Confidence Inspector:            |                              |
| Language: Marathi | Consent: Granted (v1.2)      | Amount: 98% | Time: 95% | UTR:99%| AUDIT TRAIL:                 |
| Nominee: Alerted (+91 98220 99887)               |                                  | 14:32 - Voice note transcribed|
+--------------------------------------------------+----------------------------------+ 14:33 - Citizen confirmed    |
| [ MARK FORWARDED TO 1930 ]   [ MARK CLOSED ]   [ FLAG AS REPEAT OFFENDER ]          | 14:34 - Nominee alerted      |
+-------------------------------------------------------------------------------------+------------------------------+
```

---

## 4. Console Screen 3: Financial Crime Intelligence & Scam Cluster Graph

### Screen Wireframe Layout
```text
+--------------------------------------------------------------------------------------------------------------------+
| MAHARASHTRA CYBER INTELLIGENCE PORTAL — SYNDICATE & SCAM SCRIPT CLUSTERING                                         |
+--------------------------------------------------------------------------------------------------------------------+
| [ Emerging Scam Clusters ]   [ Repeat Identifier Graph ]   [ Generate Weekly Police Leads Report (PDF/JSON) ]      |
+--------------------------------------------------------------------------------------------------------------------+
| Active Cluster: "MSEDCL Electricity Disconnection Impersonation Ring"                                              |
| Total Linked Cases: 14 | Total Siphoned: ₹8,40,000 | Geographic Spread: Pune (6), Mumbai (5), Nagpur (3)          |
| Key Pattern: Coercive calls between 14:00-17:00 threatening cutoff at 20:00; uses fake AnyDesk/QuickSupport APKs.  |
+--------------------------------------------------------------------------------------------------------------------+
| REPEAT IDENTIFIERS DETECTED ACROSS COMPLAINTS:                                                                     |
| Identifier Value        Type    Frequency  First Seen   Latest Case  Linked Beneficiary Accounts                   |
| ------------------------------------------------------------------------------------------------------------------ |
| +91 9823412345          Phone   5 cases    28 Oct 2026  18 mins ago  Axis Bank (A/C **8912), Yes Bank UPI          |
| msedcl-billpay@axisbank UPI     7 cases    25 Oct 2026  18 mins ago  Axis Bank Branch: Vashi Navi Mumbai           |
| payfast@icici           UPI     12 cases   20 Oct 2026  2 hours ago  ICICI Bank (Mule Ring: Telegram Tasks)        |
+--------------------------------------------------------------------------------------------------------------------+
| RECOMMENDED LAW ENFORCEMENT ACTIONS:                                                                               |
| 1. Block 3 repeat phone numbers under DoT Sanchar Saathi / TAFCOP API relay.                                        |
| 2. Issue public cyber advisory in Marathi & Hindi regarding fake Mahavitaran bill alerts.                           |
| 3. Send bulk lien coordination request to Nodal Officers of Axis Bank and ICICI Bank.                               |
+--------------------------------------------------------------------------------------------------------------------+
```

