"""Patch script: inserts new intents into chat.py"""
import os

path = os.path.join(os.path.dirname(__file__), "chat.py")
content = open(path, "r", encoding="utf-8").read()

NEW_INTENTS = """
    "candidate_comparison": [
        r"compare\\s+\\w[\\w\\s]+and\\s+\\w",
        r"\\bvs\\b|\\bversus\\b",
        r"difference\\s+between",
        r"who\\s+is\\s+better",
        r"side.by.side",
    ],
    "hiring_recommendation": [
        r"(who|which)\\s+(should|shall|would)\\s+(i|we|you)\\s+hire",
        r"recommend.*hire",
        r"hiring\\s+(decision|recommendation)",
        r"should\\s+(i|we)\\s+hire",
        r"(best|top)\\s+(candidate|person)\\s+to\\s+hire",
    ],
    "why_low_rank": [
        r"why.*(rank|score).*(low|poor|weak|bad)",
        r"why.*(low|poor|bad|weak).*(score|rank)",
        r"reason.*(low|poor).*(score|rank)",
        r"why.*not.*shortlist",
    ],
    "interview_performance": [
        r"how.*did.*perform.*interview",
        r"interview\\s+(score|result|analysis|feedback|performance)",
        r"(communication|confidence)\\s+(score|level|rating)",
        r"cheating\\s+risk",
    ],
    "generate_questions": [
        r"(generate|create|give|make|suggest).*interview.*question",
        r"what.*should.*i.*ask",
        r"question.*to.*ask",
        r"prepare.*interview",
    ],
"""

MARKER = '    "greeting": ['
if MARKER not in content:
    print("ERROR: marker not found")
else:
    result = content.replace(MARKER, NEW_INTENTS + "\n" + MARKER, 1)
    open(path, "w", encoding="utf-8").write(result)
    print("OK: new intents inserted successfully")
