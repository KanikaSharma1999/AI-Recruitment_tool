"""Patch: wire new intent handlers into the main routing block"""
import os

path = os.path.join(os.path.dirname(__file__), "chat.py")
content = open(path, "r", encoding="utf-8").read()

OLD = '''    elif intent == "candidate_profile":
        response = await _response_candidate_profile(query, memory)

    else:'''

NEW = '''    elif intent == "candidate_profile":
        response = await _response_candidate_profile(query, memory)

    elif intent == "candidate_comparison":
        response = await _response_candidate_comparison(query, memory)

    elif intent == "hiring_recommendation":
        response = await _response_hiring_recommendation(query, memory)

    elif intent == "why_low_rank":
        response = await _response_why_low_rank(query, memory)

    elif intent == "interview_performance":
        response = await _response_interview_performance(query, memory)

    elif intent == "generate_questions":
        response = await _response_generate_questions(query, memory)

    else:'''

if OLD not in content:
    print("ERROR: routing block marker not found")
else:
    result = content.replace(OLD, NEW, 1)
    open(path, "w", encoding="utf-8").write(result)
    print("OK: new routing cases wired")
