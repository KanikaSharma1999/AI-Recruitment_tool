import csv
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


STATUS_COLORS = {
    "Shortlisted": colors.HexColor("#10b981"),
    "Selected": colors.HexColor("#4f46e5"),
    "Interview Scheduled": colors.HexColor("#3b82f6"),
    "Rejected": colors.HexColor("#ef4444"),
    "Applied": colors.HexColor("#6b7280"),
}


def generate_csv_report(candidates: list) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Rank", "Name", "Email", "Phone", "Score", "Skill Match",
                     "Experience (yrs)", "Status", "Matched Skills", "Missing Skills", "Feedback"])
    for i, c in enumerate(candidates, 1):
        writer.writerow([
            i,
            c.get("name", ""),
            c.get("email", ""),
            c.get("phone", ""),
            f"{c.get('score', 0):.1f}%",
            f"{c.get('skill_score', 0):.1f}%",
            c.get("experience_years", 0),
            c.get("status", ""),
            ", ".join(c.get("matched_skills", [])),
            ", ".join(c.get("missing_skills", [])),
            c.get("feedback", "").replace("\n", " | "),
        ])
    return output.getvalue()


def generate_pdf_report(candidates: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle("Title", parent=styles["Title"],
                                  fontSize=20, spaceAfter=6,
                                  textColor=colors.HexColor("#0f172a"))
    elements.append(Paragraph("AI Resume Screening Report", title_style))

    sub_style = ParagraphStyle("Sub", parent=styles["Normal"],
                                fontSize=10, textColor=colors.HexColor("#64748b"),
                                spaceAfter=16)
    elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Total Candidates: {len(candidates)}", sub_style))
    elements.append(Spacer(1, 0.3*cm))

    # Table
    col_widths = [0.8*cm, 3.5*cm, 4.2*cm, 1.8*cm, 1.8*cm, 2.5*cm]
    header = [["#", "Name", "Email", "Score", "Status", "Skills Matched"]]

    data = header
    for i, c in enumerate(candidates, 1):
        matched = ", ".join(c.get("matched_skills", [])[:4])
        if len(c.get("matched_skills", [])) > 4:
            matched += "…"
        data.append([
            str(i),
            c.get("name", "")[:22],
            c.get("email", "")[:26],
            f"{c.get('score', 0):.0f}%",
            c.get("status", "Applied"),
            matched[:30],
        ])

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ])
    # Color status column
    for i, c in enumerate(candidates, 1):
        status = c.get("status", "Applied")
        clr = STATUS_COLORS.get(status, colors.HexColor("#6b7280"))
        table_style.add("TEXTCOLOR", (4, i), (4, i), clr)
        table_style.add("FONTNAME", (4, i), (4, i), "Helvetica-Bold")

    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 0.6*cm))

    # Feedback section
    feedback_title = ParagraphStyle("FBTitle", parent=styles["Heading2"],
                                     fontSize=13, textColor=colors.HexColor("#0f172a"),
                                     spaceAfter=8, spaceBefore=12)
    elements.append(Paragraph("Candidate Feedback Details", feedback_title))

    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=8,
                                 leading=12, spaceAfter=4, textColor=colors.HexColor("#334155"))
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=9,
                                  fontName="Helvetica-Bold", textColor=colors.HexColor("#0f172a"),
                                  spaceBefore=8, spaceAfter=2)

    for i, c in enumerate(candidates, 1):
        elements.append(Paragraph(
            f"{i}. {c.get('name', 'N/A')} — Score: {c.get('score', 0):.1f} | {c.get('status', '')}",
            label_style))
        fb = c.get("feedback", "No feedback available.").replace("\n", "<br/>")
        elements.append(Paragraph(fb, body_style))

    doc.build(elements)
    return buffer.getvalue()


def generate_interview_report(candidate: dict, job: dict) -> bytes:
    """Generates a professional enterprise-grade interview intelligence report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = []
    
    analysis = candidate.get("ai_analysis", {})
    metrics = analysis.get("metrics", {})

    # 1. Header
    header_style = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=22, spaceAfter=4, textColor=colors.HexColor("#1e293b"))
    elements.append(Paragraph("Interview Intelligence Report", header_style))
    
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#64748b"), spaceAfter=20)
    elements.append(Paragraph(f"Candidate: {candidate['name']} | Role: {job.get('title', 'N/A')} | Date: {datetime.utcnow().strftime('%Y-%m-%d')}", meta_style))

    # 2. Executive Summary (Verdict)
    elements.append(Paragraph("Executive Verdict", styles["Heading2"]))
    
    verdict_color = {
        "Strong Hire": "#10b981",
        "Hire": "#3b82f6",
        "Hold": "#f59e0b",
        "Reject": "#ef4444"
    }.get(analysis.get("recommendation"), "#64748b")

    verdict_data = [[
        Paragraph(f"<font color='{verdict_color}' size='14'><b>{analysis.get('recommendation', 'N/A').upper()}</b></font><br/>{analysis.get('verdict', '')}", styles["Normal"]),
        Paragraph(f"<b>AI Confidence:</b> {analysis.get('confidence', 'N/A')}<br/><b>Risk Status:</b> {analysis.get('cheating_risk', 'N/A')}", styles["Normal"])
    ]]
    
    v_table = Table(verdict_data, colWidths=[10*cm, 7*cm])
    v_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#e2e8f0")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(v_table)
    elements.append(Spacer(1, 0.5*cm))

    # 3. Behavioral Notes
    elements.append(Paragraph("Recruiter Observations", styles["Heading3"]))
    elements.append(Paragraph(analysis.get("reasoning", "No detailed analysis available."), styles["Normal"]))
    elements.append(Spacer(1, 0.8*cm))

    # 4. Behavioral Metrics Table
    elements.append(Paragraph("Behavioral & Communication Metrics", styles["Heading3"]))
    m_data = [
        ["Metric", "Value", "Status"],
        ["Visual Engagement", f"{metrics.get('attention_score', 0):.1f}%", analysis.get("attention", "N/A")],
        ["Communication Clarity", f"{metrics.get('comm_score', 0):.1f}%", analysis.get("communication", "N/A")],
        ["Speaking Ratio", f"{metrics.get('speaking_ratio', 0):.1f}%", "Optimal" if 30 <= metrics.get('speaking_ratio', 0) <= 60 else "Variable"],
        ["Integrity Index", f"{metrics.get('risk_score', 0):.1f}", analysis.get("cheating_risk", "N/A")]
    ]
    m_table = Table(m_data, colWidths=[6*cm, 4*cm, 5*cm])
    m_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))
    elements.append(m_table)
    elements.append(Spacer(1, 0.8*cm))

    # 5. Behavioral Event Log
    elements.append(Paragraph("Behavioral Event Log (Evidence Log)", styles["Heading3"]))
    log = analysis.get("event_log", [])
    if not log:
        elements.append(Paragraph("No significant behavioral events recorded.", styles["Italic"]))
    else:
        l_data = [["Category", "Severity", "Event Observation"]]
        for e in log[:15]: # Limit to top 15 for PDF
            l_data.append([
                e.get("category", "N/A"),
                e.get("severity", "N/A"),
                e.get("message", "")
            ])
        
        l_table = Table(l_data, colWidths=[4*cm, 3*cm, 10*cm])
        l_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('FONTSIZE', (0,1), (-1,-1), 8),
        ]))
        # Color severities
        for idx, e in enumerate(log[:15], 1):
            sev = e.get("severity", "")
            color = colors.black
            if sev == "Critical": color = colors.red
            elif sev == "High": color = colors.orange
            l_table.setStyle(TableStyle([('TEXTCOLOR', (1, idx), (1, idx), color)]))
            
        elements.append(l_table)

    # 6. Disclaimer
    elements.append(Spacer(1, 1.5*cm))
    disc_style = ParagraphStyle("Disc", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#94a3b8"), italic=True)
    elements.append(Paragraph("This report is generated by AI based on behavioral monitoring. Final hiring decisions should be made by human recruiters in conjunction with technical assessment results.", disc_style))

    doc.build(elements)
    return buffer.getvalue()
