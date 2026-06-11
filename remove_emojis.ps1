param()

$srcPath = "d:\Job_resume_ranker-main\frontend\src"
$files = Get-ChildItem -Path $srcPath -Recurse -Include "*.jsx","*.js"

# Ordered replacements: specific multi-word phrases first, then single emojis
$replacements = @(
    # Section headers (from screenshot)
    [pscustomobject]@{ Old = "✅ AI Strengths";           New = "AI Strengths" },
    [pscustomobject]@{ Old = "✅ AI STRENGTHS";           New = "AI STRENGTHS" },
    [pscustomobject]@{ Old = "⚠️ AI WEAKNESSES / GAPS";  New = "AI WEAKNESSES / GAPS" },
    [pscustomobject]@{ Old = "⚠️ AI Weaknesses / Gaps";  New = "AI Weaknesses / Gaps" },
    [pscustomobject]@{ Old = "🔍 SKILLS ANALYSIS";       New = "SKILLS ANALYSIS" },
    [pscustomobject]@{ Old = "🔍 Skills Analysis";       New = "Skills Analysis" },
    [pscustomobject]@{ Old = "🛡️ RISK ASSESSMENT";      New = "RISK ASSESSMENT" },
    [pscustomobject]@{ Old = "🛡️ Risk Assessment";      New = "Risk Assessment" },
    [pscustomobject]@{ Old = "✅ MATCHED SKILLS";        New = "MATCHED SKILLS" },
    [pscustomobject]@{ Old = "✅ Matched Skills";        New = "Matched Skills" },
    [pscustomobject]@{ Old = "❌ MISSING SKILLS";        New = "MISSING SKILLS" },
    [pscustomobject]@{ Old = "❌ Missing Skills";        New = "Missing Skills" },
    [pscustomobject]@{ Old = "📊 MATCH SCORE BREAKDOWN"; New = "MATCH SCORE BREAKDOWN" },
    [pscustomobject]@{ Old = "📊 Match Score Breakdown"; New = "Match Score Breakdown" },
    [pscustomobject]@{ Old = "🌟 AI Candidate Summary";  New = "AI Candidate Summary" },
    [pscustomobject]@{ Old = "🌟 AI CANDIDATE SUMMARY";  New = "AI CANDIDATE SUMMARY" },
    # Buttons (from screenshot)
    [pscustomobject]@{ Old = "📅 Schedule Interview";    New = "Schedule Interview" },
    [pscustomobject]@{ Old = "➡️ Move to Next Stage";   New = "Move to Next Stage" },
    [pscustomobject]@{ Old = "🔄 Re-Analyze Resume";     New = "Re-Analyze Resume" },
    [pscustomobject]@{ Old = "📄 View Resume";           New = "View Resume" },
    [pscustomobject]@{ Old = "🔄 Re-rank All";           New = "Re-rank All" },
    [pscustomobject]@{ Old = "🔄 Re-Rank All";           New = "Re-Rank All" },
    # Dashboard & Candidates
    [pscustomobject]@{ Old = "⏳ Awaiting JD";           New = "Awaiting JD" },
    [pscustomobject]@{ Old = "⚠️ ";                      New = "" },
    [pscustomobject]@{ Old = "✅ Strengths";             New = "Strengths" },
    [pscustomobject]@{ Old = "⚠️ Weaknesses";           New = "Weaknesses" },
    [pscustomobject]@{ Old = "✓ Strengths";              New = "Strengths" },
    # Single emojis (clean up any remaining)
    [pscustomobject]@{ Old = "🎯"; New = "" },
    [pscustomobject]@{ Old = "🚀"; New = "" },
    [pscustomobject]@{ Old = "💡"; New = "" },
    [pscustomobject]@{ Old = "⚡"; New = "" },
    [pscustomobject]@{ Old = "🏆"; New = "" },
    [pscustomobject]@{ Old = "📋"; New = "" },
    [pscustomobject]@{ Old = "🔔"; New = "" },
    [pscustomobject]@{ Old = "💼"; New = "" },
    [pscustomobject]@{ Old = "🗂️"; New = "" },
    [pscustomobject]@{ Old = "📊"; New = "" },
    [pscustomobject]@{ Old = "🌟"; New = "" },
    [pscustomobject]@{ Old = "📅"; New = "" },
    [pscustomobject]@{ Old = "➡️"; New = "" },
    [pscustomobject]@{ Old = "📄"; New = "" },
    [pscustomobject]@{ Old = "🔄"; New = "" },
    [pscustomobject]@{ Old = "🔍"; New = "" },
    [pscustomobject]@{ Old = "🛡️"; New = "" },
    [pscustomobject]@{ Old = "❌"; New = "" },
    [pscustomobject]@{ Old = "✅"; New = "" },
    [pscustomobject]@{ Old = "⏳"; New = "" },
    [pscustomobject]@{ Old = "✓ "; New = "" }
)

$count = 0
foreach ($file in $files) {
    $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
    $original = $content
    foreach ($r in $replacements) {
        $content = $content.Replace($r.Old, $r.New)
    }
    if ($content -ne $original) {
        [System.IO.File]::WriteAllText($file.FullName, $content, [System.Text.Encoding]::UTF8)
        Write-Host "Updated: $($file.Name)"
        $count++
    }
}
Write-Host ""
Write-Host "Done. $count file(s) updated."
