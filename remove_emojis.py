import os
import re

src_path = r"d:\Job_resume_ranker-main\frontend\src"

# Ordered: specific multi-word first, then single chars
REPLACEMENTS = [
    # Section headers visible in screenshot
    ("\u2705 AI Strengths",            "AI Strengths"),
    ("\u2705 AI STRENGTHS",            "AI STRENGTHS"),
    ("\u26a0\ufe0f AI WEAKNESSES / GAPS",  "AI WEAKNESSES / GAPS"),
    ("\u26a0\ufe0f AI Weaknesses / Gaps",  "AI Weaknesses / Gaps"),
    ("\u26a0\ufe0f AI Weaknesses",         "AI Weaknesses"),
    ("\U0001f50d SKILLS ANALYSIS",     "SKILLS ANALYSIS"),
    ("\U0001f50d Skills Analysis",     "Skills Analysis"),
    ("\U0001f6e1\ufe0f RISK ASSESSMENT",   "RISK ASSESSMENT"),
    ("\U0001f6e1\ufe0f Risk Assessment",   "Risk Assessment"),
    ("\u2705 MATCHED SKILLS",          "MATCHED SKILLS"),
    ("\u2705 Matched Skills",          "Matched Skills"),
    ("\u274c MISSING SKILLS",          "MISSING SKILLS"),
    ("\u274c Missing Skills",          "Missing Skills"),
    ("\U0001f4ca MATCH SCORE BREAKDOWN","MATCH SCORE BREAKDOWN"),
    ("\U0001f4ca Match Score Breakdown","Match Score Breakdown"),
    ("\U0001f31f AI Candidate Summary", "AI Candidate Summary"),
    ("\U0001f31f AI CANDIDATE SUMMARY", "AI CANDIDATE SUMMARY"),
    # Buttons
    ("\U0001f4c5 Schedule Interview",  "Schedule Interview"),
    ("\u27a1\ufe0f Move to Next Stage","Move to Next Stage"),
    ("\U0001f504 Re-Analyze Resume",   "Re-Analyze Resume"),
    ("\U0001f504 Re-Analyse Resume",   "Re-Analyse Resume"),
    ("\U0001f4c4 View Resume",         "View Resume"),
    ("\U0001f504 Re-rank All",         "Re-rank All"),
    ("\U0001f504 Re-Rank All",         "Re-Rank All"),
    # Inline status labels
    ("\u23f3 Awaiting JD",             "Awaiting JD"),
    ("\u26a0\ufe0f ",                  ""),
    ("\u2705 Strengths",               "Strengths"),
    ("\u26a0\ufe0f Weaknesses",        "Weaknesses"),
    ("\u2713 Strengths",               "Strengths"),
    ("\u2713 ",                        ""),
    # Single emojis - remove entirely
    ("\U0001f3af", ""),  # 🎯
    ("\U0001f680", ""),  # 🚀
    ("\U0001f4a1", ""),  # 💡
    ("\u26a1",     ""),  # ⚡
    ("\U0001f3c6", ""),  # 🏆
    ("\U0001f4cb", ""),  # 📋
    ("\U0001f514", ""),  # 🔔
    ("\U0001f4bc", ""),  # 💼
    ("\U0001f5c2\ufe0f", ""),  # 🗂️
    ("\U0001f4ca", ""),  # 📊
    ("\U0001f31f", ""),  # 🌟
    ("\U0001f4c5", ""),  # 📅
    ("\u27a1\ufe0f", ""),  # ➡️
    ("\U0001f4c4", ""),  # 📄
    ("\U0001f504", ""),  # 🔄
    ("\U0001f50d", ""),  # 🔍
    ("\U0001f6e1\ufe0f", ""),  # 🛡️
    ("\u274c",     ""),  # ❌
    ("\u2705",     ""),  # ✅
    ("\u23f3",     ""),  # ⏳
    ("\u2713 ",    ""),  # ✓ (with space)
    ("\u2713",     ""),  # ✓
    ("\u26a0\ufe0f", ""),  # ⚠️
    ("\u26a0",     ""),  # ⚠
]

updated = []
for root, dirs, files in os.walk(src_path):
    dirs[:] = [d for d in dirs if d != "node_modules"]
    for fname in files:
        if fname.endswith((".jsx", ".js")):
            fpath = os.path.join(root, fname)
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            original = content
            for old, new in REPLACEMENTS:
                content = content.replace(old, new)
            if content != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)
                updated.append(fname)
                print(f"Updated: {fname}")

print(f"\nDone. {len(updated)} file(s) updated.")
