"""Patch: update greeting and help text to include new intents"""
import os

path = os.path.join(os.path.dirname(__file__), "chat.py")
content = open(path, "r", encoding="utf-8").read()

OLD_GREETING = '''    return (
        "👋 **Hello! I'm your AI Hiring Assistant.**\\n\\n"
        "I can help you with:\\n"
        "• 🔍 **Find candidates** — 'Show Python developers'\\n"
        "• 🏆 **Rankings** — 'Top 5 for Data Scientist'\\n"
        "• 📋 **Job info** — 'Skills for Frontend Developer'\\n"
        "• 👤 **Profiles** — 'Summarize John Doe'\\n"
        "• 📊 **Analytics** — 'Most common skills'\\n"
        "• 🔎 **Filters** — 'Candidates with 3+ years experience'\\n\\n"
        "What would you like to know?"
    )'''

NEW_GREETING = '''    return (
        "👋 **Hello! I'm your AI Recruitment Analyst.**\\n\\n"
        "I can help you with:\\n"
        "• 🔍 **Find candidates** — 'Show Python developers'\\n"
        "• 🏆 **Rankings** — 'Top 5 for Data Scientist'\\n"
        "• ⚖️ **Compare** — 'Compare Alice and Ravi'\\n"
        "• 🎯 **Hire decision** — 'Who should I hire for Backend?'\\n"
        "• 📉 **Explain score** — 'Why did Ravi rank low?'\\n"
        "• 🎥 **Interview** — 'How did Priya perform in the interview?'\\n"
        "• 📝 **Questions** — 'Generate interview questions for ML Engineer'\\n"
        "• 📊 **Analytics** — 'Most common skills'\\n\\n"
        "What would you like to know?"
    )'''

OLD_HELP = '''def _response_help() -> str:
    return (
        "🤖 **AI Hiring Assistant — Capabilities**\\n\\n"
        "**Candidate Search:**\\n"
        "• 'Show Python developers'\\n"
        "• 'Candidates with React and Node experience'\\n"
        "• 'Candidates with 3+ years experience'\\n\\n"
        "**Rankings:**\\n"
        "• 'Top 5 candidates for Backend Developer'\\n"
        "• 'Best candidate for Data Analyst'\\n\\n"
        "**Job Info:**\\n"
        "• 'Show JD for Frontend Developer'\\n"
        "• 'List all available job roles'\\n\\n"
        "**Profiles:**\\n"
        "• 'Summarize this candidate'\\n"
        "• 'What skills does John Doe have?'\\n\\n"
        "**Analytics:**\\n"
        "• 'Most common skills'\\n"
        "• 'Average experience of shortlisted candidates'\\n"
        "• 'How many candidates missing Docker?'"
    )'''

NEW_HELP = '''def _response_help() -> str:
    return (
        "🤖 **AI Recruitment Analyst — Full Capabilities**\\n\\n"
        "**🔍 Candidate Search:**\\n"
        "• 'Show Python developers'\\n"
        "• 'Candidates with React and Node experience'\\n"
        "• 'Candidates with 3+ years experience'\\n\\n"
        "**🏆 Rankings & Recommendations:**\\n"
        "• 'Top 5 candidates for Backend Developer'\\n"
        "• 'Who should I hire for Data Analyst?'\\n"
        "• 'Best candidate for this role'\\n\\n"
        "**⚖️ Candidate Comparison:**\\n"
        "• 'Compare Alice and Ravi'\\n"
        "• 'Alice vs Bob for Backend role'\\n"
        "• 'Who is better between Priya and Sam?'\\n\\n"
        "**📉 Score Explanation:**\\n"
        "• 'Why did Ravi rank low?'\\n"
        "• 'What skills is Alice missing?'\\n"
        "• 'Why was this candidate not shortlisted?'\\n\\n"
        "**🎥 Interview Intelligence:**\\n"
        "• 'How did Ravi perform in the interview?'\\n"
        "• 'What was Priya communication score?'\\n"
        "• 'Show cheating risk for this candidate'\\n\\n"
        "**📝 Interview Prep:**\\n"
        "• 'Generate interview questions for ML Engineer'\\n"
        "• 'What should I ask a Backend Developer?'\\n\\n"
        "**📊 Analytics:**\\n"
        "• 'Most common skills'\\n"
        "• 'Average experience of shortlisted candidates'\\n"
        "• 'How many candidates missing Docker?'"
    )'''

changed = False
if OLD_GREETING in content:
    content = content.replace(OLD_GREETING, NEW_GREETING, 1)
    changed = True
    print("OK: greeting updated")
else:
    print("WARN: greeting marker not found, skipping")

if OLD_HELP in content:
    content = content.replace(OLD_HELP, NEW_HELP, 1)
    changed = True
    print("OK: help updated")
else:
    print("WARN: help marker not found, skipping")

if changed:
    open(path, "w", encoding="utf-8").write(content)
    print("File saved")
