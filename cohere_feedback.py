import time

import cohere
import os

co = cohere.Client(os.getenv("COHERE_API_KEY"))

def get_resume_feedback(resume_text, job_description):
    prompt = f"""You are an HR assistant. Give a short evaluation of this resume based on the job description in ONLY 3 to 4 concise bullet points.

Job Description:
{job_description[:1500]}

Resume:
{resume_text[:2000]}

Rules:
- Return ONLY 3 to 4 plain bullet points starting with "- "
- No headings like Strengths, Weaknesses, Suggestions, or Final Verdict
- No long paragraphs
- Each bullet point must be one short sentence
- Focus on fit, key skills match, gaps, and overall suitability
"""

    try:
        response = co.chat(
            model="command-r-plus-08-2024",
            message=prompt,
            temperature=0.5
        )
        return response.text.strip()

    except Exception as e:
        return f"⚠️ Error generating feedback: {str(e)}"