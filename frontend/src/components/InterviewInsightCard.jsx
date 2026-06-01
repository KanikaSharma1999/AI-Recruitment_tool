import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, ReferenceLine } from 'recharts';
import { Shield, MessageSquare, UserCheck, AlertCircle, Clock, Video, Info, TrendingUp, CheckCircle, Award, Brain, BarChart2, Activity } from 'lucide-react';
import API from '../api/client';

export default function InterviewInsightCard({ candidate }) {
  const [activeTab, setActiveTab] = useState('summary');
  const analysis = candidate?.ai_analysis;

  if (!analysis) {
    return (
      <div className="card animate-fade" style={{ textAlign: 'center', padding: '48px 24px', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <div style={{ fontSize: 54, marginBottom: 12, color: '#cbd5e1' }}></div>
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

  const getStatusColor = (level) => {
    const map = {
      'Strong Hire': 'text-emerald-700 bg-emerald-50 border-emerald-200',
      'Hire': 'text-indigo-700 bg-indigo-50 border-indigo-200',
      'Hold': 'text-amber-700 bg-amber-50 border-amber-200',
      'Reject': 'text-rose-700 bg-rose-50 border-rose-200',
      'High': 'text-emerald-700 bg-emerald-50 border-emerald-100',
      'Medium': 'text-amber-700 bg-amber-50 border-amber-100',
      'Low': 'text-slate-600 bg-slate-50 border-slate-100',
      'Critical': 'text-rose-700 bg-rose-100 border-rose-200',
      'High Risk': 'text-rose-600 bg-rose-50 border-rose-100',
      'Suspicious': 'text-amber-600 bg-amber-50 border-amber-100',
      'Clean': 'text-emerald-600 bg-emerald-50 border-emerald-100',
      'Slow': 'text-amber-600 bg-amber-50',
      'Normal': 'text-emerald-600 bg-emerald-50',
      'Fast': 'text-blue-600 bg-blue-50',
      'Exceptional': 'text-emerald-700 bg-emerald-50 border-emerald-200',
      'Good': 'text-indigo-700 bg-indigo-50 border-indigo-200',
      'Average': 'text-amber-700 bg-amber-50 border-amber-200',
      'Basic': 'text-slate-600 bg-slate-50 border-slate-200',
      'Weak': 'text-rose-700 bg-rose-50 border-rose-200',
    };
    return map[level] || 'text-slate-600 bg-slate-50 border-slate-100';
  };

  const handleExport = () => {
    window.open(`${API.defaults.baseURL}/interviews/export/${candidate.id}`, '_blank');
  };

  const tabs = [
    { id: 'summary', label: 'Verdict & Info', icon: <CheckCircle size={14} /> },
    { id: 'communication', label: 'Comm & Behavior', icon: <MessageSquare size={14} /> },
    { id: 'technical', label: 'Technical Fit', icon: <Brain size={14} /> },
    { id: 'proctoring', label: 'Integrity & Timeline', icon: <Shield size={14} /> }
  ];

  // Helper component to render progress bars
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
          <Activity size={14} className="text-indigo-500" /> Interview Intelligence Engine
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button 
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-[11px] font-bold transition-all border border-indigo-100 shadow-sm"
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
      <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', gap: 8, marginBottom: 24, overflowX: 'auto', paddingBottom: 2 }} className="custom-scrollbar">
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
              <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${getStatusColor(recommendation)}`}>
                Verdict: {recommendation}
              </span>
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 800, color: '#1e293b', marginBottom: 8 }}>{verdict}</h3>
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
        <div className="animate-fade grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Communication Analysis */}
          <div>
            <h4 style={{ fontSize: 12, fontWeight: 800, color: '#6366f1', textTransform: 'uppercase', marginBottom: 16 }}>Communication Performance</h4>
            <ProgressBar label="Clarity & Articulation" score={communication_analysis.clarity_score ?? metrics.comm_score} color="#6366f1" />
            <ProgressBar label="Confidence Level" score={communication_analysis.confidence_score ?? metrics.conf_score} color="#4f46e5" />
            <ProgressBar label="Professionalism" score={communication_analysis.professionalism ?? 80} color="#4f46e5" />
            <ProgressBar label="Audience Engagement" score={communication_analysis.engagement ?? 85} color="#818cf8" />
            
            <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
              <BadgeBox label="Speech Pace" value={communication_analysis.speech_pace} getStatusColor={getStatusColor} />
              <BadgeBox label="Hesitation" value={communication_analysis.hesitation_detection} getStatusColor={getStatusColor} />
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
              <BadgeBox label="Honesty Index" value={behavioral_analysis.honesty_indicators} getStatusColor={getStatusColor} />
              <BadgeBox label="Stress Level" value={behavioral_analysis.stress_indicators} getStatusColor={getStatusColor} />
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
        <div className="animate-fade grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 style={{ fontSize: 12, fontWeight: 800, color: '#06b6d4', textTransform: 'uppercase', marginBottom: 16 }}>Technical Understanding</h4>
            <ProgressBar label="Technical Knowledge Match" score={technical_evaluation.technical_understanding ?? 75} color="#06b6d4" />
            <ProgressBar label="Complexity / Depth of Answers" score={technical_evaluation.depth_of_answers ?? 70} color="#0891b2" />
          </div>

          <div>
            <h4 style={{ fontSize: 12, fontWeight: 800, color: '#06b6d4', textTransform: 'uppercase', marginBottom: 16 }}>Capability Assessments</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 12px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b' }}>Leadership Indicators</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${getStatusColor(technical_evaluation.leadership_indicators)}`}>
                  {technical_evaluation.leadership_indicators || "Average"}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 12px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b' }}>Problem Solving Quality</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${getStatusColor(technical_evaluation.problem_solving_quality)}`}>
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
              <Shield size={24} className="text-rose-500" />
              <div>
                <div style={{ fontSize: 10, fontWeight: 800, color: '#b91c1c', textTransform: 'uppercase' }}>Security Risk Index</div>
                <div style={{ fontSize: 18, fontWeight: 900, color: '#991b1b' }}>{cheating_risk.toUpperCase()}</div>
              </div>
            </div>
            <div style={{ padding: 16, background: '#f8fafc', borderRadius: 12, border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: 12 }}>
              <Clock size={24} className="text-indigo-500" />
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
          <div style={{ maxHeight: 200, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }} className="custom-scrollbar">
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

function BadgeBox({ label, value, getStatusColor }) {
  const displayVal = value || "Normal";
  return (
    <div style={{ flex: 1, padding: '10px 12px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>{label}</span>
      <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase border ${getStatusColor(displayVal)}`}>
        {displayVal}
      </span>
    </div>
  );
}
