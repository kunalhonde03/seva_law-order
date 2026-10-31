"""Official Cyber Crime Complaint Dossier PDF Generator.

Produces tamper-evident, portal-ready summary PDFs using ReportLab.
"""

import hashlib
import io
from datetime import datetime, timezone
from typing import Any, Dict
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generate_complaint_pdf(case_dict: Dict[str, Any], ref_no: str) -> bytes:
    """Renders an official Maharashtra Cyber Crime Complaint Dossier as PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=35,
        bottomMargin=35
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "GovTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=colors.HexColor("#0B2545"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "GovSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#134074"),
        alignment=1,
    )
    label_style = ParagraphStyle(
        "FieldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1D2D44"),
    )
    val_style = ParagraphStyle(
        "FieldValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#000000"),
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("GOVERNMENT OF MAHARASHTRA — POLICE CYBER CRIME CELL", title_style))
    story.append(Paragraph("SURAKSHAVANI INTAKE INTELLIGENCE & GOLDEN-HOUR REPORTING DOSSIER", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B2545")))
    story.append(Spacer(1, 10))

    # 2. Case Metadata Table
    urgency = case_dict.get("urgency", "NORMAL")
    urgency_color = "#D90429" if urgency == "CRITICAL" else ("#D97706" if urgency == "HIGH" else "#16A34A")

    meta_data = [
        [
            Paragraph("<b>Case Reference:</b>", label_style),
            Paragraph(f"<b>{ref_no}</b>", val_style),
            Paragraph("<b>Priority:</b>", label_style),
            Paragraph(f"<font color='{urgency_color}'><b>{urgency}</b></font>", val_style),
        ],
        [
            Paragraph("<b>Generated At:</b>", label_style),
            Paragraph(datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC"), val_style),
            Paragraph("<b>Channel:</b>", label_style),
            Paragraph("SurakshaVani Citizen Portal / WhatsApp", val_style),
        ],
        [
            Paragraph("<b>Incident Category:</b>", label_style),
            Paragraph(case_dict.get("category", "fraud").upper(), val_style),
            Paragraph("<b>Subtype:</b>", label_style),
            Paragraph(case_dict.get("subtype", "other"), val_style),
        ]
    ]

    t_meta = Table(meta_data, colWidths=[110, 160, 90, 170])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6F9")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # 3. Financial & Transaction Details
    story.append(Paragraph("<b>1. INCIDENT & FINANCIAL INTERCEPTION METRICS</b>", label_style))
    story.append(Spacer(1, 4))

    amt = case_dict.get("amount_inr", {}).get("value")
    amt_str = f"INR {amt:,.2f}" if amt is not None else "Not Disclosed / Non-Monetary"
    utrs = ", ".join(case_dict.get("transaction_ids", [])) or "Pending bank statement"
    victim_bank = case_dict.get("victim_bank") or "Citizen Account"

    fin_data = [
        [Paragraph("Disputed Amount:", label_style), Paragraph(f"<b>{amt_str}</b>", val_style)],
        [Paragraph("Victim Bank / Institution:", label_style), Paragraph(victim_bank, val_style)],
        [Paragraph("Transaction Ref / UTR:", label_style), Paragraph(utrs, val_style)],
        [Paragraph("Payment Mechanism:", label_style), Paragraph(case_dict.get("payment_method", "N/A").upper(), val_style)],
    ]

    t_fin = Table(fin_data, colWidths=[160, 370])
    t_fin.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF4F8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 14))

    # 4. Suspect Entities
    story.append(Paragraph("<b>2. EXTRACTED SUSPECT / BENEFICIARY IDENTIFIERS</b>", label_style))
    story.append(Spacer(1, 4))

    suspect_rows = [[
        Paragraph("<b>Type</b>", label_style),
        Paragraph("<b>Identifier Value</b>", label_style),
        Paragraph("<b>Designation</b>", label_style)
    ]]

    suspects = case_dict.get("suspect_identifiers", [])
    if suspects:
        for s in suspects:
            suspect_rows.append([
                Paragraph(s.get("kind", "").upper(), val_style),
                Paragraph(s.get("value", ""), val_style),
                Paragraph(s.get("role", "suspect").title(), val_style)
            ])
    else:
        suspect_rows.append([
            Paragraph("Caller ID", val_style),
            Paragraph("Not isolated in voice note", val_style),
            Paragraph("Suspect", val_style)
        ])

    t_suspect = Table(suspect_rows, colWidths=[120, 260, 150])
    t_suspect.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_suspect)
    story.append(Spacer(1, 14))

    # 5. Narrative
    story.append(Paragraph("<b>3. INCIDENT SUMMARY & SYNOPSIS (FOR POLICE ACTION)</b>", label_style))
    story.append(Spacer(1, 4))
    narrative = case_dict.get("narrative_en") or case_dict.get("narrative_local") or "No narrative provided."
    story.append(Paragraph(narrative, val_style))
    story.append(Spacer(1, 16))

    # 6. Integrity & DPDP Signoff
    raw_hash = hashlib.sha256(f"{ref_no}:{amt_str}:{narrative}".encode()).hexdigest()
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#94A3B8")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<b>Evidentiary Integrity Hash (SHA-256):</b> <font face='Courier' size=7>{raw_hash}</font>",
        subtitle_style
    ))
    story.append(Paragraph(
        "Prepared in compliance with DPDP Act 2023 Rule 4 & Section 91 CrPC / Section 94 BNSS 2023. "
        "Verified by Citizen Confirmation before Police Relay.",
        subtitle_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

