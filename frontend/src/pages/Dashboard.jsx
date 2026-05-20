import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import API from '../api/client';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, FunnelChart, Funnel, LabelList, CartesianGrid, Cell,
} from 'recharts';
import {
  MdPeople, MdThumbUp, MdCalendarToday, MdCheckCircle,
  MdTrendingUp, MdAutoAwesome, MdWarning,
} from 'react-icons/md';
import { requestNotificationPermission, checkAndNotifyInterviews } from '../components/NotificationService';

// ── Stat card config ───────────────────────────────────────────────────────────
const STAT_CONFIG = [
  { key: 'total',               label: 'Total Candidates',  icon: <MdPeople />,       accent: '#6366f1', bg: '#ede9fe', textColor: '#4f46e5' },
  { key: 'screening',           label: 'In Screening',      icon: <MdTrendingUp />,   accent: '#f59e0b', bg: '#fef3c7', textColor: '#d97706' },
  { key: 'shortlisted',         label: 'Shortlisted',       icon: <MdThumbUp />,      accent: '#10b981', bg: '#d1fae5', textColor: '#059669' },
  { key: 'interview_scheduled', label: 'Interviews',        icon: <MdCalendarToday />,accent: '#3b82f6', bg: '#dbeafe', textColor: '#2563eb' },
  { key: 'selected',            label: 'Selected',          icon: <MdCheckCircle />,  accent: '#8b5cf6', bg: '#ede9fe', textColor: '#7c3aed' },
];

// ── Interview status computed live from datetime_iso ─────────────────────────
// JOIN WINDOW: scheduled_time → scheduled_time + 60 minutes
function computeInterviewStatus(datetimeIso) {
  if (!datetimeIso) return { status: 'upcoming', label: 'Upcoming', minutesUntil: null };
  const now = Date.now();
  const start = new Date(datetimeIso).getTime();
  const end   = start + 60 * 60 * 1000; // +1 hour join window
  const diffMs = start - now;
  const diffMin = Math.round(diffMs / 60000);

  if (now > end)         return { status: 'missed',   label: 'Missed — Expired',  minutesUntil: null };
  if (now >= start)      return { status: 'live',     label: 'Live Now',           minutesUntil: 0 };
  if (diffMin <= 15)     return { status: 'imminent', label: `Starts in ${diffMin} min${diffMin !== 1 ? 's' : ''}`, minutesUntil: diffMin };
  if (diffMin <= 60)     return { status: 'today',    label: `Starts in ${diffMin} mins`, minutesUntil: diffMin };
  const diffDays = Math.floor(diffMin / 1440);
  if (diffDays === 0)    return { status: 'today',    label: `Today at ${new Date(start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}`, minutesUntil: diffMin };
  if (diffDays === 1)    return { status: 'tomorrow', label: `Tomorrow at ${new Date(start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}`, minutesUntil: diffMin };
  return { status: 'upcoming', label: `${new Date(start).toLocaleDateString([], {month:'short',day:'numeric'})} at ${new Date(start).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}`, minutesUntil: diffMin };
}

const STATUS_STYLE = {
  missed:   { color: '#ef4444', bg: '#fee2e2', icon: '❌', joinable: false },
  live:     { color: '#10b981', bg: '#d1fae5', icon: '🟢', joinable: true  },
  imminent: { color: '#f59e0b', bg: '#fef3c7', icon: '⚡', joinable: true  },
  today:    { color: '#f59e0b', bg: '#fef3c7', icon: '🟡', joinable: true  },
  tomorrow: { color: '#3b82f6', bg: '#dbeafe', icon: '📅', joinable: false },
  upcoming: { color: '#6366f1', bg: '#ede9fe', icon: '🔵', joinable: false },
  completed:{ color: '#10b981', bg: '#d1fae5', icon: '✅', joinable: false },
  cancelled:{ color: '#94a3b8', bg: '#f1f5f9', icon: '⚫', joinable: false },
};

// ── Candidate status → color lookup ───────────────────────────────────────────
const candidateStatusColor = (status) => {
  const s = (status || '').toLowerCase();
  if (s.includes('selected') || s.includes('completed') || s.includes('attended'))
    return { bg: '#d1fae5', color: '#059669' };
  if (s.includes('interview_scheduled'))
    return { bg: '#dbeafe', color: '#2563eb' };
  if (s.includes('shortlisted'))
    return { bg: '#d1fae5', color: '#059669' };
  if (s.includes('missed') || s.includes('rejected') || s.includes('overdue'))
    return { bg: '#fee2e2', color: '#ef4444' };
  if (s.includes('on_hold'))
    return { bg: '#fef3c7', color: '#d97706' };
  return { bg: '#f1f5f9', color: '#64748b' };
};

// ── AI Insight Banner ─────────────────────────────────────────────────────────
function AIInsightBanner({ stats }) {
  if (!stats) return null;
  const shortlisted = stats.shortlisted || 0;
  const interviews  = stats.interview_scheduled || 0;
  const selected    = stats.selected || 0;
  const total       = stats.total || 0;
  const avgScore    = stats.avg_score || 0;

  let insight, color, bg, border;
  if (shortlisted > 0 && interviews === 0) {
    insight = `🎯 ${shortlisted} candidate${shortlisted > 1 ? 's are' : ' is'} shortlisted and ready for interview scheduling.`;
    color = '#059669'; bg = 'linear-gradient(135deg, #f0fdf4, #ecfdf5)'; border = '#6ee7b7';
  } else if (interviews > 0) {
    insight = `📅 ${interviews} interview${interviews > 1 ? 's are' : ' is'} scheduled. ${selected > 0 ? `${selected} candidate(s) already selected.` : 'Follow up with the pipeline.'}`;
    color = '#2563eb'; bg = 'linear-gradient(135deg, #eff6ff, #dbeafe)'; border = '#93c5fd';
  } else if (total === 0) {
    insight = '🚀 Get started — upload resumes and run AI ranking to see hiring insights here.';
    color = '#6366f1'; bg = 'linear-gradient(135deg, #faf5ff, #ede9fe)'; border = '#c4b5fd';
  } else if (avgScore > 65) {
    insight = `⭐ Strong pipeline! Average AI match is ${avgScore.toFixed(1)}% — approximately ${Math.round(total * 0.3)} candidates likely qualify for shortlisting.`;
    color = '#7c3aed'; bg = 'linear-gradient(135deg, #faf5ff, #ede9fe)'; border = '#c4b5fd';
  } else {
    insight = `📊 ${total} candidate${total > 1 ? 's' : ''} in pipeline. Run ranking to generate AI hiring recommendations and scores.`;
    color = '#6366f1'; bg = 'linear-gradient(135deg, #eff6ff, #eef2ff)'; border = '#bfdbfe';
  }

  return (
    <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 12, padding: '14px 20px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{ width: 36, height: 36, borderRadius: '50%', background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <MdAutoAwesome style={{ color: '#fff', fontSize: 18 }} />
      </div>
      <div style={{ fontSize: 13.5, fontWeight: 500, color: '#1e293b', flex: 1 }}>{insight}</div>
      <div style={{ fontSize: 11, color: color, fontWeight: 700, whiteSpace: 'nowrap' }}>AI INSIGHT</div>
    </div>
  );
}

// ── Interview Card — ticks every second, auto-expires after 1 hour ────────────
function InterviewCard({ item }) {
  const [live, setLive] = useState(() => computeInterviewStatus(item.datetime_iso));

  // Re-compute every 30 seconds so status auto-updates without full page reload
  useEffect(() => {
    const t = setInterval(() => setLive(computeInterviewStatus(item.datetime_iso)), 30000);
    return () => clearInterval(t);
  }, [item.datetime_iso]);

  const style   = STATUS_STYLE[live.status] || STATUS_STYLE.upcoming;
  const isMissed = live.status === 'missed';
  const isLive   = live.status === 'live' || live.status === 'imminent';

  return (
    <div style={{
      padding: 16, borderRadius: 14, background: '#fff',
      border: `1.5px solid ${isMissed ? '#fecaca' : isLive ? '#6ee7b7' : '#f1f5f9'}`,
      boxShadow: isMissed ? '0 0 0 3px rgba(239,68,68,0.08)' : isLive ? '0 0 0 3px rgba(16,185,129,0.1)' : '0 2px 8px rgba(0,0,0,0.04)',
      position: 'relative',
    }}>
      {/* Live pulse for active interviews */}
      {isLive && (
        <div style={{ position: 'absolute', top: 14, left: 14, width: 8, height: 8, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 0 3px rgba(16,185,129,0.3)', animation: 'pulse 1.5s infinite' }} />
      )}

      {/* Status Badge */}
      <div style={{ position: 'absolute', top: 12, right: 12 }}>
        <span style={{
          padding: '3px 9px', borderRadius: 999, fontSize: 10, fontWeight: 800,
          background: style.bg, color: style.color, textTransform: 'uppercase', letterSpacing: '0.5px',
        }}>
          {style.icon} {live.label}
        </span>
      </div>

      <div style={{ fontSize: 13, fontWeight: 800, color: '#1e293b', marginBottom: 2, paddingRight: 90, paddingLeft: isLive ? 20 : 0 }}>
        {item.candidate_name}
      </div>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 12 }}>{item.job_title}</div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: style.color, fontWeight: 700, marginBottom: 10 }}>
        <div style={{ width: 26, height: 26, borderRadius: 7, background: style.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          {isMissed ? <MdWarning size={13} /> : <MdCalendarToday size={13} />}
        </div>
        {item.date} {item.time && `at ${item.time}`}
      </div>

      {/* Action buttons — context-aware */}
      {isMissed ? (
        <button
          style={{ width: '100%', padding: '8px 0', fontSize: 11, background: '#fee2e2', color: '#ef4444', borderRadius: 8, fontWeight: 700, border: '1px solid #fecaca', cursor: 'pointer' }}
          onClick={() => (window.location.href = `/candidates/${item.id}`)}
        >
          ❌ Interview Expired — Review Profile
        </button>
      ) : style.joinable ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            style={{ flex: 1.5, padding: '8px 0', fontSize: 11, background: isLive ? '#10b981' : '#f59e0b', color: '#fff', borderRadius: 8, fontWeight: 700, border: 'none', cursor: item.link ? 'pointer' : 'not-allowed', opacity: item.link ? 1 : 0.5 }}
            onClick={() => item.link && window.open(item.link, '_blank')}
            disabled={!item.link}
          >
            {isLive ? '🟢 Join Now' : `⚡ ${live.label}`}
          </button>
          <button
            style={{ flex: 1, padding: '8px 0', fontSize: 11, background: '#f8fafc', color: '#475569', borderRadius: 8, fontWeight: 600, border: '1px solid #e2e8f0', cursor: 'pointer' }}
            onClick={() => (window.location.href = `/candidates/${item.id}`)}
          >
            Profile
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            style={{ flex: 1.5, padding: '8px 0', fontSize: 11, background: '#f1f5f9', color: '#94a3b8', borderRadius: 8, fontWeight: 600, border: '1px solid #e2e8f0', cursor: 'not-allowed' }}
            disabled
          >
            {live.label}
          </button>
          <button
            style={{ flex: 1, padding: '8px 0', fontSize: 11, background: '#f8fafc', color: '#475569', borderRadius: 8, fontWeight: 600, border: '1px solid #e2e8f0', cursor: 'pointer' }}
            onClick={() => (window.location.href = `/candidates/${item.id}`)}
          >
            Profile
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [topCandidates, setTopCandidates] = useState([]);
  const [selJob, setSelJob] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    API.get('/jobs/list').then(r => setJobs(r.data)).catch(() => {});
    API.get('/candidates/list').then(r => {
      const sorted = [...(r.data || [])].sort((a, b) => (b.score || 0) - (a.score || 0));
      setTopCandidates(sorted.slice(0, 4));
    }).catch(() => {});
    requestNotificationPermission();
  }, []);

  const fetchStats = () => {
    setLoading(true);
    const url = selJob ? `/dashboard/stats?job_id=${selJob}` : '/dashboard/stats';
    API.get(url)
      .then(r => {
        setStats(r.data);
        if (r.data?.upcoming_interviews) checkAndNotifyInterviews(r.data.upcoming_interviews);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStats();
    const t = setInterval(fetchStats, 60000); // refresh every minute for countdown accuracy
    return () => clearInterval(t);
  }, [selJob]);

  const funnelData = stats
    ? [
        { name: 'Total Applied', value: stats.total || 0, fill: '#6366f1' },
        { name: 'Screening',     value: stats.screening || 0, fill: '#3b82f6' },
        { name: 'Shortlisted',   value: stats.shortlisted || 0, fill: '#10b981' },
        { name: 'Interviews',    value: (stats.interview_scheduled || 0) + (stats.interviewed || 0), fill: '#8b5cf6' },
        { name: 'Selected',      value: stats.selected || 0, fill: '#f59e0b' },
      ].filter(d => d.value > 0)
    : [];

  const overdueCount = (stats?.upcoming_interviews || []).filter(
    i => i.interview_status === 'overdue' || i.interview_status === 'missed'
  ).length;

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-content">
        <Navbar title="Dashboard" />
        <div className="page-body animate-fade">

          {/* ── Header ──────────────────────────────────────────────────── */}
          <div className="flex-between page-header" style={{ marginBottom: 24 }}>
            <div>
              <h1 style={{ fontSize: 24, fontWeight: 800, color: '#1e293b' }}>Recruitment Command Center</h1>
              <p style={{ color: '#64748b', fontSize: 14 }}>Real-time intelligence and pipeline management</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <select
                className="form-select"
                style={{ width: 220, fontSize: 13, borderRadius: 10, border: '1px solid #e2e8f0' }}
                value={selJob}
                onChange={e => setSelJob(e.target.value)}
              >
                <option value="">All Roles</option>
                {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
              </select>
              <button className="btn btn-outline btn-sm" style={{ borderRadius: 10 }} onClick={fetchStats}>
                ↻ Refresh
              </button>
            </div>
          </div>

          {/* ── AI Insight Banner ────────────────────────────────────────── */}
          <AIInsightBanner stats={stats} />

          {/* ── Main Grid ───────────────────────────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>

            {/* Left column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

              {/* Stat Cards */}
              <div className="stats-grid">
                {STAT_CONFIG.map(({ key, label, icon, accent, bg, textColor }) => (
                  <div className="stat-card" key={key} style={{ '--stat-accent': accent, borderRadius: 16 }}>
                    <div className="stat-icon" style={{ background: bg, color: textColor }}>{icon}</div>
                    <div className="stat-info">
                      <div className="stat-label">{label}</div>
                      <div className="stat-value" style={{ color: textColor }}>
                        {loading ? <span style={{ fontSize: 20, color: '#d1d5db' }}>—</span> : (stats?.[key] ?? 0)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Charts Row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                {/* Pipeline Funnel */}
                <div className="card" style={{ borderRadius: 16 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 800, color: '#475569', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#6366f1' }} />
                    Pipeline Funnel
                  </h3>
                  <div style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <FunnelChart>
                        <Tooltip contentStyle={{ borderRadius: 10, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }} />
                        <Funnel dataKey="value" data={funnelData} isAnimationActive>
                          <LabelList position="right" fill="#64748b" stroke="none" dataKey="name" style={{ fontSize: 10, fontWeight: 600 }} />
                          {funnelData.map((entry, idx) => <Cell key={idx} fill={entry.fill} />)}
                        </Funnel>
                      </FunnelChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Score Distribution */}
                <div className="card" style={{ borderRadius: 16 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 800, color: '#475569', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }} />
                    Score Distribution
                  </h3>
                  <div style={{ height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats?.score_distribution || []}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="range" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                        <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: 10, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }} />
                        <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} barSize={32} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Top Candidates Table */}
              <div className="card" style={{ borderRadius: 16 }}>
                <div className="flex-between" style={{ marginBottom: 20 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 800, color: '#475569', display: 'flex', alignItems: 'center', gap: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    <MdTrendingUp style={{ color: '#f59e0b' }} /> High-Potential Candidates
                  </h3>
                  <a href="/candidates" style={{ fontSize: 11, fontWeight: 700, color: '#6366f1', textDecoration: 'none' }}>VIEW ALL →</a>
                </div>
                <div className="table-responsive">
                  <table className="table" style={{ fontSize: 13 }}>
                    <thead>
                      <tr>
                        <th style={{ color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>CANDIDATE</th>
                        <th style={{ color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>AI MATCH</th>
                        <th style={{ color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>STATUS</th>
                        <th style={{ color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>ACTION</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topCandidates.map(c => {
                        const sc = candidateStatusColor(c.status);
                        return (
                          <tr key={c.id}>
                            <td>
                              <div style={{ fontWeight: 700, color: '#1e293b' }}>{c.name}</div>
                              <div style={{ fontSize: 11, color: '#94a3b8' }}>{c.email}</div>
                            </td>
                            <td>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 60, height: 6, background: '#f1f5f9', borderRadius: 3, overflow: 'hidden' }}>
                                  <div style={{ width: `${c.score}%`, height: '100%', background: 'linear-gradient(90deg, #6366f1, #8b5cf6)', borderRadius: 3 }} />
                                </div>
                                <span style={{ fontSize: 12, fontWeight: 800, color: '#6366f1' }}>{Math.round(c.score)}%</span>
                              </div>
                            </td>
                            <td>
                              <span style={{ padding: '4px 10px', borderRadius: 8, fontSize: 10, fontWeight: 800, textTransform: 'uppercase', background: sc.bg, color: sc.color }}>
                                {(c.status || '').replace(/_/g, ' ')}
                              </span>
                            </td>
                            <td>
                              <button className="btn btn-sm btn-outline" style={{ borderRadius: 8, fontSize: 11 }} onClick={() => (window.location.href = `/candidates/${c.id}`)}>
                                View
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* ── Right Sidebar: Interview Sessions ──────────────────────── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div className="card" style={{ padding: 0, overflow: 'hidden', border: '1px solid #e2e8f0', borderRadius: 16, boxShadow: '0 10px 25px -5px rgba(0,0,0,0.05)' }}>
                {/* Header */}
                <div style={{ padding: '18px 20px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <h3 style={{ fontSize: 12, fontWeight: 800, color: '#475569', display: 'flex', alignItems: 'center', gap: 8, letterSpacing: '0.5px' }}>
                    <MdCalendarToday style={{ color: '#6366f1' }} /> INTERVIEW SESSIONS
                  </h3>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {overdueCount > 0 && (
                      <span style={{ fontSize: 10, fontWeight: 800, background: '#ef4444', color: '#fff', padding: '2px 8px', borderRadius: 999 }}>
                        {overdueCount} overdue
                      </span>
                    )}
                    <span style={{ fontSize: 10, fontWeight: 800, background: '#6366f1', color: '#fff', padding: '2px 8px', borderRadius: 999 }}>
                      {stats?.upcoming_interviews?.length || 0} total
                    </span>
                  </div>
                </div>

                {/* Interview list */}
                <div style={{ padding: 12, maxHeight: 620, overflowY: 'auto' }} className="custom-scrollbar">
                  {stats?.upcoming_interviews?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {stats.upcoming_interviews.map(item => (
                        <InterviewCard key={item.id} item={item} />
                      ))}
                    </div>
                  ) : (
                    <div style={{ padding: '60px 20px', textAlign: 'center', color: '#94a3b8' }}>
                      <div style={{ width: 50, height: 50, borderRadius: '50%', background: '#f8fafc', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                        <MdCalendarToday size={24} style={{ opacity: 0.3 }} />
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#475569' }}>All Clear</div>
                      <div style={{ fontSize: 11, marginTop: 4 }}>No interviews scheduled.</div>
                    </div>
                  )}
                </div>
              </div>

              {/* AI Tip Card */}
              <div className="card" style={{ background: 'linear-gradient(135deg, #1e293b, #0f172a)', color: '#fff', border: 'none', borderRadius: 16, padding: 24 }}>
                <h3 style={{ fontSize: 11, fontWeight: 800, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>
                  <MdAutoAwesome style={{ color: '#f59e0b' }} /> AI Hiring Tip
                </h3>
                <p style={{ fontSize: 13, lineHeight: 1.6, color: '#cbd5e1', fontWeight: 500 }}>
                  Candidates who switch browser tabs more than 3 times during an interview show a 40% higher probability of information retrieval assistance.{' '}
                  <span style={{ color: '#fbbf24', fontWeight: 700 }}>Monitor proctoring logs closely.</span>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
