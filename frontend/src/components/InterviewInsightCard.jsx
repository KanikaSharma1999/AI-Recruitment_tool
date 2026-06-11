import { useState } from 'react';
import { AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Shield, Clock, CheckCircle, AlertCircle, UserCheck, MessageSquare, Brain, Activity, TrendingUp } from 'lucide-react';
import API from '../api/client';
import toast from 'react-hot-toast';

export default function InterviewInsightCard({ candidate }) {
  const [activeTab, setActiveTab] = useState('summary');
  const analysis = candidate?.ai_analysis;

  if (!analysis) {
    return (
      <div className="card animate-fade" style={{ textAlign: 'center', padding: '48px 24px', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h3 style={{ fontSize: 16, fontWeight: 800, color: '#1e293b' }}>Interview Intelligence Pending</h3>
        <p style={{ fontSize: 13, color: '#64748b', marginTop: 6, maxWidth: 300, margin: '8px auto', lineHeight: 1.5 }}>
          Once the interview is started and completed, the real-time behavioral logs and automated recruiter reports will display here.
        </p>
      </div>
    );
  }

  const {
    metrics = {},
    communication_analysis = {},
    behavioral_analysis = {},
    technical_evaluation = {},
    metadata = {},
    recommendation = "Hold",
    verdict = "Pending review",
    reasoning = "",
    timeline = [],
    event_log = [],
    cheating_risk = "Low",
    analysis_confidence = "High"
  } = analysis;

  const getStatusStyle = (level) => {
    const map = {
      'Strong Hire': { color: '#047857', backgroundColor: '#ecfdf5', borderColor: '#a7f3d0' },
      'Hire': { color: '#4338ca', backgroundColor: '#e0e7ff', borderColor: '#c7d2fe' },
      'Hold': { color: '#b45309', backgroundColor: '#fffbeb', borderColor: '#fde68a' },
      'Reject': { color: '#be123c', backgroundColor: '#fef2f2', borderColor: '#fecaca' },
      'High': { color: '#047857', backgroundColor: '#ecfdf5', borderColor: '#d1fae5' },
      'Medium': { color: '#b45309', backgroundColor: '#fffbeb', borderColor: '#fef3c7' },
      'Low': { color: '#475569', backgroundColor: '#f8fafc', borderColor: '#e2e8f0' },
      'Critical': { color: '#be123c', backgroundColor: '#fee2e2', borderColor: '#fecaca' },
      'High Risk': { color: '#e11d48', backgroundColor: '#fff1f2', borderColor: '#ffe4e6' },
      'Suspicious': { color: '#d97706', backgroundColor: '#fffbeb', borderColor: '#fef3c7' },
      'Clean': { color: '#059669', backgroundColor: '#ecfdf5', borderColor: '#a7f3d0' },
      'Slow': { color: '#d97706', backgroundColor: '#fffbeb', borderColor: 'transparent' },
      'Normal': { color: '#059669', backgroundColor: '#ecfdf5', borderColor: 'transparent' },
      'Fast': { color: '#2563eb', backgroundColor: '#eff6ff', borderColor: 'transparent' },
      'Exceptional': { color: '#047857', backgroundColor: '#ecfdf5', borderColor: '#a7f3d0' },
      'Good': { color: '#4338ca', backgroundColor: '#e0e7ff', borderColor: '#c7d2fe' },
      'Average': { color: '#b45309', backgroundColor: '#fffbeb', borderColor: '#fde68a' },
      'Basic': { color: '#475569', backgroundColor: '#f8fafc', borderColor: '#cbd5e1' },
      'Weak': { color: '#be123c', backgroundColor: '#fef2f2', borderColor: '#fecaca' },
    };
    return map[level] || { color: '#475569', backgroundColor: '#f8fafc', borderColor: '#e2e8f0' };
  };

  const handleExport = async () => {
    try {
      const r = await API.get(`/interviews/export/${candidate.id}`, { responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `interview_report_${candidate.name.replace(/\s+/g, '_')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to download interview report');
    }
  };

  const tabs = [
    { id: 'summary', label: 'Verdict & Info', icon: <CheckCircle size={14} /> },
    { id: 'communication', label: 'Comm & Behavior', icon: <MessageSquare size={14} /> },
    { id: 'technical', label: 'Technical Fit', icon: <Brain size={14} /> },
    { id: 'proctoring', label: 'Integrity & Timeline', icon: <Shield size={14} /> }
  ];

  const ProgressBar = ({ label, score, color = '#6366f1' }) => (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 6 }}>
        <span>{label}</span>
        <span>{score}%</span>
      </div>
      <div style={{ height: 8, background: '#f1f5f9', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: 4, transition: 'width 1s ease-in-out' }} />
      </div>
    </div>
  );

  return (
    <div className="card animate-fade" style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 16, padding: 24, boxShadow: '0 4px 20px rgba(0,0,0,0.03)' }}>
      
      {/* Confidence and Export Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>
          <Activity size={14} style={{ color: '#6366f1' }} /> Interview Intelligence Engine
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button 
            onClick={handleExport}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              backgroundColor: '#e0e7ff',
              color: '#4338ca',
              borderRadius: 8,
              fontSize: 11,
              fontWeight: 700,
              border: '1px solid #c7d2fe',
              cursor: 'pointer',
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
            }}
          >
            <TrendingUp size={12} /> Download PDF Report
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 10, fontWeight: 800, color: '#94a3b8' }}>AI CONFIDENCE:</span>
            <span style={{
              fontSize: 10, fontWeight: 900, padding: '2px 8px', borderRadius: 20,
              background: analysis_confidence === 'High' ? '#ecfdf5' : '#fffbeb',
              color: analysis_confidence === 'High' ? '#059669' : '#d97706'
            }}>{analysis_confidence.toUpperCase()}</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', gap: 8, marginBottom: 24, overflowX: 'auto', paddingBottom: 2 }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px', fontSize: 12, fontWeight: 700,
              border: 'none', borderBottom: activeTab === tab.id ? '2px solid #6366f1' : '2px solid transparent',
              background: 'none', color: activeTab === tab.id ? '#6366f1' : '#64748b', cursor: 'pointer',
              whiteSpace: 'nowrap', transition: 'all 0.2s'
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB CONTENTS */}
      {activeTab === 'summary' && (
        <div className="animate-fade">
          <div style={{ padding: 20, background: '#f8fafc', borderRadius: 12, border: '1px solid #e2e8f0', marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span style={{
                padding: '4px 10px',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 900,
                textTransform: 'uppercase',
                border: '1px solid',
                ...getStatusStyle(recommendation)
              }}>
                Verdict: {recommendation}
              </span>
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 800, color: '#1e293b', marginBottom: 8 }}>{verdict}</h3>
            <p style={{ fontSize: 13, lineHeight: 1.6, color: '#475569', fontStyle: 'italic', borderLeft: '3px solid #cbd5e1', paddingLeft: 12, margin: 0 }}>
              "{reasoning}"
            </p>
          </div>

          <h4 style={{ fontSize: 12, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 12, letterSpacing: '0.5px' }}>Session Metadata</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
            <MetadataTile label="Duration" value={metadata.total_duration || "N/A"} icon={<Clock size={16} />} />
            <MetadataTile label="Join Time" value={metadata.join_time ? new Date(metadata.join_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : "N/A"} icon={<Clock size={16} />} />
            <MetadataTile label="Completion" value={metadata.completion_time ? new Date(metadata.completion_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : "N/A"} icon={<CheckCircle size={16} />} />
            <MetadataTile label="Interruptions" value={`${metadata.interruptions || 0} events`} icon={<AlertCircle size={16} />} />
            <MetadataTile label="Attendance" value={metadata.attendance || "Present"} icon={<UserCheck size={16} />} />
          </div>
        </div>
      )}

      {activeTab === 'communication' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 24 }} className="animate-fade">
          {/* Communication Analysis */}
          <div>
            <h4 style={{ fontSize: 12, fontWeight: 800, color: '#6366f1', textTransform: 'uppercase', marginBottom: 16 }}>Communication Performance</h4>
            <ProgressBar label="Clarity & Articulation" score={communication_analysis.clarity_score ?? metrics.comm_score} color="#6366f1" />
            <ProgressBar label="Confidence Level" score={communication_analysis.confidence_score ?? metrics.conf_score} color="#4f46e5" />
            <ProgressBar label="Professionalism" score={communication_analysis.professionalism ?? 80} color="#4f46e5" />
            <ProgressBar label="Audience Engagement" score={communication_analysis.engagement ?? 85} color="#818cf8" />
            
            <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
              <BadgeBox label="Speech Pace" value={communication_analysis.speech_pace} getStatusStyle={getStatusStyle} />
              <BadgeBox label="Hesitation" value={communication_analysis.hesitation_detection} getStatusStyle={getStatusStyle} />
            </div>

            {communication_analysis.evidence_quote && (
              <div style={{ marginTop: 16, padding: '12px 16px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', borderLeft: '3px solid #6366f1' }}>
                <div style={{ fontSize: '10px', fontWeight: 800, color: '#6366f1', textTransform: 'uppercase', marginBottom: 4 }}>Speech Evidence Quote</div>
                <p style={{ fontSize: '11.5px', color: '#475569', fontStyle: 'italic', margin: 0 }}>"{communication_analysis.evidence_quote}"</p>
              </div>
            )}
          </div>

          {/* Behavioral Analysis */}
          <div>
            <h4 style={{ fontSize: 12, fontWeight: 800, color: '#f59e0b', textTransform: 'uppercase', marginBottom: 16 }}>Behavioral & Gaze Analysis</h4>
            <ProgressBar label="Eye Contact Ratio" score={behavioral_analysis.eye_contact ?? metrics.eye_contact} color="#f59e0b" />
            <ProgressBar label="Attentiveness Rate" score={behavioral_analysis.attentiveness ?? metrics.attention_score} color="#d97706" />
            <ProgressBar label="Emotional Stability" score={behavioral_analysis.emotional_stability ?? 80} color="#fbbf24" />
            
            <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
              <BadgeBox label="Honesty Index" value={behavioral_analysis.honesty_indicators} getStatusStyle={getStatusStyle} />
              <BadgeBox label="Stress Level" value={behavioral_analysis.stress_indicators} getStatusStyle={getStatusStyle} />
            </div>

            {behavioral_analysis.integrity_evidence && (
              <div style={{ marginTop: 16, padding: '12px 16px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', borderLeft: '3px solid #f59e0b' }}>
                <div style={{ fontSize: '10px', fontWeight: 800, color: '#f59e0b', textTransform: 'uppercase', marginBottom: 4 }}>Visual & Attention Evidence</div>
                <p style={{ fontSize: '11.5px', color: '#475569', margin: 0 }}>{behavioral_analysis.integrity_evidence}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'technical' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 24 }} className="animate-fade">
          <div>
            <h4 style={{ fontSize: 12, fontWeight: 800, color: '#06b6d4', textTransform: 'uppercase', marginBottom: 16 }}>Technical Understanding</h4>
            <ProgressBar label="Technical Knowledge Match" score={technical_evaluation.technical_understanding ?? 75} color="#06b6d4" />
            <ProgressBar label="Complexity / Depth of Answers" score={technical_evaluation.depth_of_answers ?? 70} color="#0891b2" />
          </div>

          <div>
            <h4 style={{ fontSize: 12, fontWeight: 800, color: '#06b6d4', textTransform: 'uppercase', marginBottom: 16 }}>Capability Assessments</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 12px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b' }}>Leadership Indicators</span>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 10,
                  fontWeight: 900,
                  textTransform: 'uppercase',
                  border: '1px solid',
                  ...getStatusStyle(technical_evaluation.leadership_indicators || "Average")
                }}>
                  {technical_evaluation.leadership_indicators || "Average"}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 12px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b' }}>Problem Solving Quality</span>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 10,
                  fontWeight: 900,
                  textTransform: 'uppercase',
                  border: '1px solid',
                  ...getStatusStyle(technical_evaluation.problem_solving_quality || "Good")
                }}>
                  {technical_evaluation.problem_solving_quality || "Good"}
                </span>
              </div>
            </div>
          </div>

          {technical_evaluation.evidence_quote && (
            <div style={{ gridColumn: 'span 2', padding: '12px 16px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', borderLeft: '3px solid #06b6d4' }}>
              <div style={{ fontSize: '10px', fontWeight: 800, color: '#06b6d4', textTransform: 'uppercase', marginBottom: 4 }}>Technical Evidence Quote</div>
              <p style={{ fontSize: '11.5px', color: '#475569', fontStyle: 'italic', margin: 0 }}>"{technical_evaluation.evidence_quote}"</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'proctoring' && (
        <div className="animate-fade">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
            <div style={{ padding: 16, background: '#fef2f2', borderRadius: 12, border: '1px solid #fecaca', display: 'flex', alignItems: 'center', gap: 12 }}>
              <Shield size={24} style={{ color: '#ef4444' }} />
              <div>
                <div style={{ fontSize: 10, fontWeight: 800, color: '#b91c1c', textTransform: 'uppercase' }}>Security Risk Index</div>
                <div style={{ fontSize: 18, fontWeight: 900, color: '#991b1b' }}>{cheating_risk.toUpperCase()}</div>
              </div>
            </div>
            <div style={{ padding: 16, background: '#f8fafc', borderRadius: 12, border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: 12 }}>
              <Clock size={24} style={{ color: '#6366f1' }} />
              <div>
                <div style={{ fontSize: 10, fontWeight: 800, color: '#475569', textTransform: 'uppercase' }}>Integrity Risk Score</div>
                <div style={{ fontSize: 18, fontWeight: 900, color: '#1e293b' }}>{metrics.risk_score ?? 0.0}%</div>
              </div>
            </div>
          </div>

          <h4 style={{ fontSize: 12, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 16, letterSpacing: '0.5px' }}>Gaze & Focus Timeline</h4>
          {timeline && timeline.length > 0 ? (
            <div style={{ height: 160, width: '100%', marginBottom: 20 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="focusGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="time" hide />
                  <YAxis domain={[0, 100]} hide />
                  <Tooltip 
                    contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', fontSize: 12 }}
                    formatter={(val) => [`${val}%`, 'Focus Level']}
                  />
                  <Area type="monotone" dataKey="focus" stroke="#6366f1" strokeWidth={2.5} fillOpacity={1} fill="url(#focusGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p style={{ fontSize: 12, color: '#94a3b8', fontStyle: 'italic', marginBottom: 20 }}>Timeline details not available for short test session.</p>
          )}

          <h4 style={{ fontSize: 12, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 12, letterSpacing: '0.5px' }}>Proctoring Log</h4>
          <div style={{ maxHeight: 200, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {event_log && event_log.length > 0 ? (
              event_log.map((evt, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: evt.severity === 'Critical' ? '#ef4444' : evt.severity === 'High' ? '#f59e0b' : '#3b82f6' }} />
                  <span style={{ fontSize: 9, fontWeight: 800, padding: '2px 6px', background: '#fff', border: '1px solid #cbd5e1', borderRadius: 4, textTransform: 'uppercase' }}>{evt.category}</span>
                  <span style={{ color: '#475569', flex: 1 }}>{evt.message}</span>
                  <span style={{ fontSize: 10, color: '#94a3b8' }}>{evt.time}</span>
                </div>
              ))
            ) : (
              <div style={{ textAlign: 'center', padding: '20px 0', color: '#94a3b8', fontSize: 12, fontStyle: 'italic' }}>
                Clean session — no suspicious proctoring alerts triggered.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MetadataTile({ label, value, icon }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10 }}>
      <div style={{ color: '#6366f1' }}>{icon}</div>
      <div>
        <div style={{ fontSize: 9, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase' }}>{label}</div>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#1e293b', marginTop: 2 }}>{value}</div>
      </div>
    </div>
  );
}

function BadgeBox({ label, value, getStatusStyle }) {
  const displayVal = value || "Normal";
  return (
    <div style={{ flex: 1, padding: '10px 12px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>{label}</span>
      <span style={{
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 9,
        fontWeight: 900,
        textTransform: 'uppercase',
        border: '1px solid',
        ...getStatusStyle(displayVal)
      }}>
        {displayVal}
      </span>
    </div>
  );
}
