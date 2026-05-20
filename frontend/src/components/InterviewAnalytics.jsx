import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Shield, MessageSquare, UserCheck, AlertCircle, Clock, Video } from 'lucide-react';

export default function InterviewAnalytics({ analysis }) {
  if (!analysis) return null;

  const { metrics, communication, confidence, attention, cheating_risk, recommendation, verdict, reasoning, timeline, security_evidence, event_log } = analysis;

  const getStatusColor = (level) => {
    const map = {
      'High': 'text-green-600 bg-green-50',
      'Moderate': 'text-amber-600 bg-amber-50',
      'Low': 'text-rose-600 bg-rose-50',
      'Clean': 'text-green-600 bg-green-50',
      'Suspicious': 'text-amber-600 bg-amber-50',
      'High Risk': 'text-rose-600 bg-rose-50',
      'Professional': 'text-indigo-600 bg-indigo-50',
      'Articulate': 'text-blue-600 bg-blue-50',
      'Average': 'text-slate-600 bg-slate-50',
      'Limited': 'text-rose-600 bg-rose-50',
      'Strong Hire': 'text-green-700 bg-green-100',
      'Hire': 'text-blue-700 bg-blue-100',
      'Hold': 'text-amber-700 bg-amber-100',
      'Reject': 'text-rose-700 bg-rose-100',
    };
    return map[level] || 'text-slate-600 bg-slate-50';
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Verdict */}
      <div className={`p-6 rounded-xl border-2 flex items-center justify-between ${getStatusColor(recommendation).split(' ')[1].replace('bg-', 'bg-opacity-50 border-')}`}>
        <div>
          <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider mb-2 inline-block ${getStatusColor(recommendation)}`}>
            AI Recommendation: {recommendation}
          </span>
          <h2 className="text-2xl font-bold text-slate-900">{verdict}</h2>
          <p className="text-slate-600 mt-2 max-w-2xl italic leading-relaxed">
            "{reasoning}"
          </p>
        </div>
        <div className="text-right">
          <div className="text-4xl font-black text-slate-900">{metrics.conf_score}%</div>
          <div className="text-sm font-medium text-slate-500 uppercase">Confidence Score</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Key Metrics Cards */}
        <div className="lg:col-span-1 space-y-4">
          <MetricCard 
            icon={<MessageSquare className="w-5 h-5 text-indigo-500" />} 
            label="Communication" 
            value={communication} 
            subValue={`${metrics.speaking_ratio}% speaking ratio`}
            color={getStatusColor(communication)}
          />
          <MetricCard 
            icon={<UserCheck className="w-5 h-5 text-blue-500" />} 
            label="Attention Level" 
            value={attention} 
            subValue={`${metrics.attention_score}% eye contact`}
            color={getStatusColor(attention)}
          />
          <MetricCard 
            icon={<Shield className="w-5 h-5 text-rose-500" />} 
            label="Proctoring Status" 
            value={cheating_risk} 
            subValue={`${metrics.risk_score} risk index`}
            color={getStatusColor(cheating_risk)}
          />
        </div>

        {/* Focus Timeline Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-slate-800 flex items-center gap-2">
              <Clock className="w-4 h-4" /> Focus & Attention Timeline
            </h3>
            <span className="text-xs text-slate-400">Values updated every 5 seconds</span>
          </div>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeline}>
                <defs>
                  <linearGradient id="colorFocus" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="time" hide />
                <YAxis domain={[0, 100]} hide />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  labelFormatter={(t) => `Time: ${t}s`}
                />
                <Area type="monotone" dataKey="focus" stroke="#6366f1" strokeWidth={3} fillOpacity={1} fill="url(#colorFocus)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Security & Evidence Log */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-50 p-5 rounded-xl border border-slate-200">
          <h4 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-500" /> Proctoring Observations
          </h4>
          <ul className="space-y-2">
            {security_evidence.length > 0 ? (
              security_evidence.map((item, idx) => (
                <li key={idx} className="text-sm text-slate-600 flex items-start gap-2">
                  <span className="mt-1 w-1.5 h-1.5 rounded-full bg-rose-400 flex-shrink-0" />
                  {item}
                </li>
              ))
            ) : (
              <li className="text-sm text-slate-500 italic">No suspicious behavior detected.</li>
            )}
          </ul>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <h4 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Video className="w-4 h-4 text-indigo-500" /> Event Timeline
          </h4>
          <div className="max-height-48 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
            {event_log && event_log.length > 0 ? (
              event_log.map((event, idx) => (
                <div key={idx} className="flex gap-3 text-xs">
                   <span className="text-slate-400 font-mono whitespace-nowrap">
                     {new Date(event.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                   </span>
                   <span className="font-semibold text-slate-700 uppercase tracking-tight">
                     [{event.type.replace('_', ' ')}]
                   </span>
                   <span className="text-slate-500">{event.detail || 'Observation logged'}</span>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-400 italic">Continuous candidate presence confirmed.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, subValue, color }) {
  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
      <div className="w-10 h-10 rounded-lg bg-slate-50 flex items-center justify-center">
        {icon}
      </div>
      <div>
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className={`text-sm font-bold px-2 py-0.5 rounded-md ${color}`}>{value}</span>
          <span className="text-xs text-slate-500">{subValue}</span>
        </div>
      </div>
    </div>
  );
}
