import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, ReferenceDot, ReferenceLine } from 'recharts';
import { Shield, MessageSquare, UserCheck, AlertCircle, Clock, Video, Info, TrendingUp, CheckCircle } from 'lucide-react';

export default function InterviewInsightCard({ candidate }) {
  const analysis = candidate?.ai_analysis;

  if (!analysis) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '40px 24px', color: '#94a3b8' }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>🎥</div>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#475569' }}>Analysis Pending</div>
        <div style={{ fontSize: 13, marginTop: 4, maxWidth: 220, margin: '8px auto' }}>
          Complete the interview session to unlock behavioral insights and integrity reports.
        </div>
      </div>
    );
  }

  const { metrics, communication, confidence, attention, cheating_risk, recommendation, verdict, reasoning, timeline, security_evidence, event_log, analysis_confidence } = analysis;

  const getStatusColor = (level) => {
    const map = {
      'High': 'text-emerald-600 bg-emerald-50',
      'Medium': 'text-amber-600 bg-amber-50',
      'Low': 'text-slate-600 bg-slate-50',
      'Critical': 'text-rose-700 bg-rose-100 border-rose-200',
      'High Risk': 'text-rose-600 bg-rose-50 border-rose-100',
      'Suspicious': 'text-amber-600 bg-amber-50 border-amber-100',
      'Clean': 'text-emerald-600 bg-emerald-50 border-emerald-100',
      'Professional': 'text-indigo-600 bg-indigo-50',
      'Articulate': 'text-blue-600 bg-blue-50',
      'Conversational': 'text-slate-600 bg-slate-50',
      'Needs Improvement': 'text-rose-600 bg-rose-50',
      'Mostly Silent': 'text-rose-700 bg-rose-100',
      'Strong Hire': 'text-emerald-700 bg-emerald-100 border-emerald-200',
      'Hire': 'text-blue-700 bg-blue-100 border-blue-200',
      'Hold': 'text-amber-700 bg-amber-100 border-amber-200',
      'Reject': 'text-rose-700 bg-rose-100 border-rose-200',
    };
    return map[level] || 'text-slate-600 bg-slate-50 border-slate-100';
  };

  const getEventIcon = (type) => {
    if (type?.includes('silence')) return '🔇';
    if (type?.includes('tab')) return '💻';
    if (type?.includes('face')) return '👥';
    return '⚠️';
  };

  const handleExport = () => {
    window.open(`${API.defaults.baseURL}/interviews/export/${candidate.id}`, '_blank');
  };

  return (
    <div className="animate-fade" style={{ padding: 0, overflow: 'hidden' }}>
      
      {/* ── AI Analysis Confidence Meter ── */}
      <div className="flex items-center justify-between px-1 mb-3">
        <div className="flex items-center gap-2 text-[11px] font-bold text-slate-400 uppercase tracking-widest">
           <Info size={12} /> AI Analysis Confidence
        </div>
        <div className="flex items-center gap-4">
           <button 
             onClick={handleExport}
             className="flex items-center gap-2 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-[11px] font-bold transition-all border border-indigo-100 shadow-sm"
           >
             <TrendingUp size={12} /> Download Intelligence Report (PDF)
           </button>
           <div className="flex items-center gap-2">
              <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-1000 ${analysis_confidence === 'High' ? 'bg-emerald-500 w-full' : analysis_confidence === 'Medium' ? 'bg-amber-500 w-2/3' : 'bg-rose-500 w-1/3'}`} 
                />
              </div>
              <span className={`text-[10px] font-black uppercase ${analysis_confidence === 'High' ? 'text-emerald-600' : analysis_confidence === 'Medium' ? 'text-amber-600' : 'text-rose-600'}`}>
                {analysis_confidence}
              </span>
           </div>
        </div>
      </div>

      {/* ── TOP SECTION: Verdict ── */}
      <div className={`p-6 rounded-2xl border-2 mb-6 shadow-sm ${getStatusColor(recommendation)}`}>
        <div className="flex items-start justify-between">
          <div style={{ flex: 1 }}>
            <div className="flex items-center gap-3 mb-3">
              <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest shadow-sm border ${getStatusColor(recommendation)}`}>
                VERDICT: {recommendation}
              </span>
              {recommendation.includes('Hire') && <CheckCircle size={18} className="text-emerald-500" />}
            </div>
            <h2 className="text-2xl font-black text-slate-800 leading-tight">{verdict}</h2>
            <p className="text-sm text-slate-600 mt-3 font-medium leading-relaxed italic border-l-4 border-slate-200 pl-4">
              "{reasoning}"
            </p>
          </div>
          <div className="text-right ml-4 bg-white bg-opacity-40 p-3 rounded-xl border border-white border-opacity-50">
            <div className="text-4xl font-black text-slate-900 leading-none">{metrics.conf_score}%</div>
            <div className="text-[10px] font-bold text-slate-500 uppercase mt-2 tracking-tighter">Engagement Index</div>
          </div>
        </div>
      </div>

      {/* ── GRID: Behavioral Metrics ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <MetricCard 
            icon={<MessageSquare size={16} className="text-indigo-500" />} 
            label="Communication" 
            value={communication} 
            subValue={`${metrics.speaking_ratio}% talk ratio`}
            color={getStatusColor(communication)}
          />
          <MetricCard 
            icon={<UserCheck size={16} className="text-blue-500" />} 
            label="Visual Focus" 
            value={attention} 
            subValue={`${metrics.attention_score}% stability`}
            color={getStatusColor(attention)}
          />
          <MetricCard 
            icon={<Shield size={16} className={cheating_risk === 'Clean' ? 'text-emerald-500' : 'text-rose-500'} />} 
            label="Integrity Risk" 
            value={cheating_risk} 
            subValue={`Risk Score: ${metrics.risk_score}`}
            color={getStatusColor(cheating_risk)}
          />
      </div>

      {/* ── INTERACTIVE TIMELINE ── */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 mb-6 shadow-sm relative overflow-hidden">
        <div className="flex items-center justify-between mb-8">
          <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
            <TrendingUp size={14} className="text-indigo-500" /> Focus & Attention Timeline
          </h3>
          <div className="flex gap-4">
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400">
              <span className="w-2 h-2 rounded-full bg-indigo-500" /> FOCUS LEVEL
            </div>
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400">
              <span className="text-[12px]">⚠️</span> CRITICAL EVENTS
            </div>
          </div>
        </div>
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timeline}>
              <defs>
                <linearGradient id="colorFocus" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="time" hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 12px 24px rgba(0,0,0,0.1)', fontSize: '12px', fontWeight: '600' }}
                labelFormatter={(t) => `Interview Time: ${t}s`}
                formatter={(val, name, props) => [
                  val + '%', 
                  props.payload.event ? `ALERT: ${props.payload.event}` : 'Focus Level'
                ]}
              />
              <Area 
                type="monotone" 
                dataKey="focus" 
                stroke="#6366f1" 
                strokeWidth={3} 
                fillOpacity={1} 
                fill="url(#colorFocus)" 
                animationDuration={1500}
              />
              {timeline.map((entry, index) => (
                entry.event && (
                  <ReferenceLine
                    key={index}
                    x={entry.time}
                    stroke="#f43f5e"
                    strokeDasharray="3 3"
                    label={{ position: 'top', value: '⚠️', fontSize: 14 }}
                  />
                )
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── EVIDENCE LOG ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200">
          <h4 className="text-[11px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <AlertCircle size={14} className="text-rose-500" /> Evidence-Based Observations
          </h4>
          <div className="space-y-3">
            {security_evidence && security_evidence.length > 0 ? (
              security_evidence.map((item, idx) => (
                <div key={idx} className="text-[12px] text-slate-700 font-medium flex items-start gap-3 bg-white p-3 rounded-xl border border-slate-100 shadow-sm">
                  <span className="w-6 h-6 rounded-lg bg-rose-50 flex items-center justify-center text-rose-500 flex-shrink-0">
                    <AlertCircle size={12} />
                  </span>
                  <div className="pt-0.5">{item}</div>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400 italic bg-white p-4 rounded-xl border border-slate-100 flex items-center gap-3">
                <Shield size={16} className="text-emerald-500" /> High integrity session. No detectable anomalies.
              </div>
            )}
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <h4 className="text-[11px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <Video size={14} className="text-indigo-500" /> Behavioral Event Log
          </h4>
          <div className="max-h-56 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
            {event_log && event_log.length > 0 ? (
              event_log.map((event, idx) => (
                <div key={idx} className="flex items-center gap-3 text-[11px] p-2.5 rounded-lg bg-slate-50 border border-slate-100 transition-hover hover:bg-white">
                   <div style={{ width: 6, height: 6, borderRadius: '50%', background: event.severity === 'Critical' ? '#ef4444' : event.severity === 'High' ? '#f59e0b' : '#3b82f6' }} />
                   <span className="font-black text-slate-700 uppercase bg-white px-2 py-0.5 rounded-md border border-slate-200 text-[9px] min-w-[70px] text-center">
                     {event.category}
                   </span>
                   <span className="text-slate-500 font-medium flex-1">{event.message}</span>
                   <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${event.severity === 'Critical' ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'}`}>
                     {event.severity}
                   </span>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400 italic py-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                Continuous engagement maintained throughout session.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, subValue, color }) {
  return (
    <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4 transition-all hover:border-indigo-200 hover:shadow-md">
      <div className="w-12 h-12 rounded-xl bg-slate-50 flex items-center justify-center border border-slate-100 shadow-inner">
        {icon}
      </div>
      <div>
        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{label}</div>
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-[12px] font-black px-2 py-1 rounded-lg border shadow-sm ${color}`}>{value}</span>
          <span className="text-[10px] text-slate-400 font-bold">{subValue}</span>
        </div>
      </div>
    </div>
  );
}
