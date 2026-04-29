import re
from sentence_transformers import SentenceTransformer, util
from PyPDF2 import PdfReader

# Load model once
model = SentenceTransformer('all-MiniLM-L6-v2')

def read_file(file):
    if file.name.endswith('.pdf'):
        reader = PdfReader(file)
        text = ''
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    else:
        return file.read().decode('utf-8')


def clean_text(text):
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    return text.strip()


def rank_resumes(job_description, resumes):
    jd_embedding = model.encode(job_description, convert_to_tensor=True)
    ranked = []

    for filename, text in resumes.items():
        resume_embedding = model.encode(text, convert_to_tensor=True)
        score = util.cos_sim(jd_embedding, resume_embedding).item()
        ranked.append((filename, score))

    return sorted(ranked, key=lambda x: x[1], reverse=True)


# 🔥 NEW FEATURE: Skill Extraction
def extract_skills(text):
    skills_list = [
        "python", "java", "c++", "machine learning", "deep learning",
        "nlp", "sql", "excel", "data analysis", "pandas", "numpy",
        "tensorflow", "pytorch", "communication", "leadership"
    ]

    found_skills = []
    for skill in skills_list:
        if skill in text:
            found_skills.append(skill)

    return set(found_skills)


# 🔥 NEW FEATURE: Skill Match Analysis
def skill_match_analysis(job_description, resume_text):
    jd_skills = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)

    matched = jd_skills.intersection(resume_skills)
    missing = jd_skills - resume_skills

    match_percent = (len(matched) / len(jd_skills) * 100) if jd_skills else 0

    return match_percent, matched, missing