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
    
    # Custom styles to support leading when changing fontSize
    title_style = ParagraphStyle(
        "RepTitle", parent=styles["Heading1"], fontSize=20, leading=24,
        textColor=colors.HexColor("#0f172a"), spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "RepSub", parent=styles["Normal"], fontSize=9, leading=13,
        textColor=colors.HexColor("#64748b"), spaceAfter=15
    )
    heading_style = ParagraphStyle(
        "RepHeading", parent=styles["Heading2"], fontSize=13, leading=17,
        textColor=colors.HexColor("#1e293b"), spaceBefore=12, spaceAfter=6,
        keepWithNext=True
    )
    subheading_style = ParagraphStyle(
        "RepSubHeading", parent=styles["Heading3"], fontSize=11, leading=15,
        textColor=colors.HexColor("#475569"), spaceBefore=10, spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        "RepBody", parent=styles["Normal"], fontSize=9.5, leading=13.5,
        textColor=colors.HexColor("#334155")
    )
    bold_body = ParagraphStyle(
        "RepBoldBody", parent=body_style, fontName="Helvetica-Bold"
    )
    italic_body = ParagraphStyle(
        "RepItalicBody", parent=body_style, fontName="Helvetica-Oblique"
    )
    table_hdr_style = ParagraphStyle(
        "RepTableHdr", parent=styles["Normal"], fontSize=9, leading=12,
        textColor=colors.white, fontName="Helvetica-Bold"
    )

    elements = []
    
    def safe_float(v, default=0.0):
        if v is None:
            return default
        try:
            return float(v)
        except:
            return default
            
    analysis = candidate.get("ai_analysis", {})
    metrics = analysis.get("metrics", {})
    comm_analysis = analysis.get("communication_analysis", {})
    beh_analysis = analysis.get("behavioral_analysis", {})
    tech_eval = analysis.get("technical_evaluation", {})
    meta = analysis.get("metadata", {})
    event_log = analysis.get("event_log", [])
    
    # 1. Header
    elements.append(Paragraph("Interview Intelligence Report", title_style))
    elements.append(Paragraph(
        f"Candidate: {candidate.get('name', 'N/A')} | Target Role: {job.get('title', 'N/A')} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        subtitle_style
    ))
    
    # 2. Executive Summary
    elements.append(Paragraph("Executive Verdict", heading_style))
    
    verdict_color = {
        "Strong Hire": "#10b981",
        "Hire": "#3b82f6",
        "Hold": "#f59e0b",
        "Reject": "#ef4444"
    }.get(analysis.get("recommendation"), "#64748b")
    
    rec_str = analysis.get("recommendation", "HOLD").upper()
    verdict_text = f"<b>Recommendation:</b> <font color='{verdict_color}'><b>{rec_str}</b></font><br/><b>Verdict Summary:</b> {analysis.get('verdict', 'N/A')}"
    
    meta_text = (
        f"<b>AI Confidence:</b> {analysis.get('analysis_confidence', 'High')}<br/>"
        f"<b>Integrity Risk Status:</b> {analysis.get('cheating_risk', 'Low')}"
    )
    
    verdict_data = [
        [Paragraph(verdict_text, body_style), Paragraph(meta_text, body_style)]
    ]
    
    v_table = Table(verdict_data, colWidths=[10.5*cm, 6.5*cm])
    v_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor("#cbd5e1")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(v_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # Reasoning
    elements.append(Paragraph("<b>Recruiter Reasoning & Analysis:</b>", subheading_style))
    elements.append(Paragraph(f"\"{analysis.get('reasoning', 'No detailed reasoning provided.')}\"", italic_body))
    elements.append(Spacer(1, 0.4*cm))
    
    # Format join/completion time for report
    join_time_str = meta.get("join_time", "N/A")
    if join_time_str != "N/A" and isinstance(join_time_str, str):
        t_part = join_time_str.replace("Z", "").split(".")[0]
        join_time_display = t_part.replace("T", " ") + " UTC"
    else:
        join_time_display = "N/A"

    comp_time_str = meta.get("completion_time", "N/A")
    if comp_time_str != "N/A" and isinstance(comp_time_str, str):
        t_part = comp_time_str.replace("Z", "").split(".")[0]
        comp_time_display = t_part.replace("T", " ") + " UTC"
    else:
        comp_time_display = "N/A"

    # 3. Session Metadata Table
    elements.append(Paragraph("Session Information", heading_style))
    meta_data = [
        [
            Paragraph("Total Duration", bold_body),
            Paragraph(meta.get("total_duration", "N/A"), body_style),
            Paragraph("Attendance", bold_body),
            Paragraph(meta.get("attendance", "Present"), body_style),
        ],
        [
            Paragraph("Join Time", bold_body),
            Paragraph(join_time_display, body_style),
            Paragraph("Completion Time", bold_body),
            Paragraph(comp_time_display, body_style),
        ],
        [
            Paragraph("Interruptions Count", bold_body),
            Paragraph(f"{meta.get('interruptions', 0)} events", body_style),
            Paragraph("Proctoring Risk Score", bold_body),
            Paragraph(f"{safe_float(metrics.get('risk_score')): .1f}%", body_style),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[4.25*cm, 4.25*cm, 4.25*cm, 4.25*cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # 4. Detailed Behavioral & Communication Breakdown
    elements.append(Paragraph("Communication & Behavioral Breakdown", heading_style))
    analysis_data = [
        [Paragraph("Behavioral & Gaze Metric", table_hdr_style), Paragraph("Score", table_hdr_style), Paragraph("Evaluation Details", table_hdr_style)],
        [Paragraph("Communication Clarity", bold_body), Paragraph(f"{safe_float(comm_analysis.get('clarity_score', metrics.get('comm_score'))):.1f}%", body_style), Paragraph(f"Speech Pace: {comm_analysis.get('speech_pace', 'Normal')} | Hesitation: {comm_analysis.get('hesitation_detection', 'Low')}", body_style)],
        [Paragraph("Confidence & Engagement", bold_body), Paragraph(f"{safe_float(comm_analysis.get('confidence_score', metrics.get('conf_score'))):.1f}%", body_style), Paragraph(f"Audience Engagement Index: {comm_analysis.get('engagement', 80)}%", body_style)],
        [Paragraph("Eye Contact Consistency", bold_body), Paragraph(f"{safe_float(beh_analysis.get('eye_contact', metrics.get('eye_contact'))):.1f}%", body_style), Paragraph(f"Stress Indicator: {beh_analysis.get('stress_indicators', 'Low')} | Honesty Index: {beh_analysis.get('honesty_indicators', 'High')}", body_style)],
        [Paragraph("Session Attentiveness", bold_body), Paragraph(f"{safe_float(beh_analysis.get('attentiveness', metrics.get('attention_score'))):.1f}%", body_style), Paragraph(f"Stability: {beh_analysis.get('emotional_stability', 80)}% | Distractions: {beh_analysis.get('distraction_detection', 'None')}", body_style)],
        [Paragraph("Speaking Distribution", bold_body), Paragraph(f"{safe_float(metrics.get('candidate_speaking_ratio', metrics.get('speaking_ratio', 50.0))):.1f}%", body_style), Paragraph(f"Candidate: {safe_float(metrics.get('candidate_speaking_ratio', metrics.get('speaking_ratio', 50.0))):.1f}% | Interviewer: {safe_float(metrics.get('interviewer_speaking_ratio', 100.0 - safe_float(metrics.get('speaking_ratio', 50.0)))):.1f}%", body_style)],
        [Paragraph("Filler Words Count", bold_body), Paragraph(f"{metrics.get('word_count', 0)} words", body_style), Paragraph(f"Um/Uh: {comm_analysis.get('filler_word_detection', {}).get('um_uh_count', 0)} | Like: {comm_analysis.get('filler_word_detection', {}).get('like_count', 0)} | Other: {comm_analysis.get('filler_word_detection', {}).get('other_fillers_count', 0)}", body_style)],
    ]
    analysis_table = Table(analysis_data, colWidths=[5.5*cm, 2.5*cm, 9.0*cm])
    analysis_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(analysis_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # 5. Technical Evaluation Fit
    elements.append(Paragraph("Technical Evaluation & Fit", heading_style))
    tech_data = [
        [
            Paragraph("Technical Understanding", bold_body),
            Paragraph(f"{tech_eval.get('technical_understanding', 70)}%", body_style),
            Paragraph("Depth of Answers", bold_body),
            Paragraph(f"{tech_eval.get('depth_of_answers', 70)}%", body_style),
        ],
        [
            Paragraph("Leadership Indicators", bold_body),
            Paragraph(tech_eval.get("leadership_indicators", "Average"), body_style),
            Paragraph("Problem Solving Quality", bold_body),
            Paragraph(tech_eval.get("problem_solving_quality", "Good"), body_style),
        ]
    ]
    tech_table = Table(tech_data, colWidths=[4.25*cm, 4.25*cm, 4.25*cm, 4.25*cm])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(tech_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # 6. Detailed Proctoring & Event Log
    if event_log:
        elements.append(Paragraph("Behavioral Event Log", heading_style))
        log_data = [[Paragraph("Category", table_hdr_style), Paragraph("Severity", table_hdr_style), Paragraph("Observation Message", table_hdr_style)]]
        for e in event_log[:10]:
            log_data.append([
                Paragraph(e.get("category", "N/A"), body_style),
                Paragraph(e.get("severity", "N/A"), body_style),
                Paragraph(e.get("message", "N/A"), body_style)
            ])
        log_table = Table(log_data, colWidths=[3.5*cm, 2.5*cm, 11.0*cm])
        log_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#334155")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(log_table)
        elements.append(Spacer(1, 0.4*cm))
        
    # 7. Transcript Section
    transcript = candidate.get("transcript", [])
    if transcript:
        elements.append(Paragraph("Interview Conversation Transcript", heading_style))
        trans_data = []
        for idx, sentence in enumerate(transcript):
            speaker = "Interviewer" if idx % 2 == 0 else "Candidate"
            trans_data.append([
                Paragraph(f"<b>{speaker}:</b>", body_style),
                Paragraph(sentence, body_style)
            ])
        trans_table = Table(trans_data, colWidths=[2.5*cm, 14.5*cm])
        trans_table.setStyle(TableStyle([
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        elements.append(trans_table)

    # Disclaimer
    elements.append(Spacer(1, 1.0*cm))
    disc_style = ParagraphStyle("Disc", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#94a3b8"), italic=True)
    elements.append(Paragraph("This report is generated by AI based on behavioral monitoring. Final hiring decisions should be made by human recruiters in conjunction with technical assessment results.", disc_style))

    doc.build(elements)
    return buffer.getvalue()
