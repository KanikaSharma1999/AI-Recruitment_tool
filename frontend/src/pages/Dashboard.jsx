import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import API from '../api/client';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import {
  MdPeople, MdThumbUp, MdCalendarToday, MdCheckCircle,
  MdTrendingUp, MdAutoAwesome, MdWarning, MdWork, MdCompare,
  MdSearch, MdNotifications, MdChatBubbleOutline, MdMoreVert
} from 'react-icons/md';
import { requestNotificationPermission, checkAndNotifyInterviews } from '../components/NotificationService';

// ── Interview status computed live from datetime_iso ─────────────────────────
function computeInterviewStatus(datetimeIso, itemStatus) {
  if (itemStatus === 'completed') {
    return { status: 'completed', label: 'Completed', minutesUntil: null };
  }
  if (itemStatus === 'live') {
    return { status: 'live', label: 'Live Now', minutesUntil: 0 };
  }
  if (itemStatus === 'missed' || itemStatus === 'overdue') {
    return { status: 'missed', label: 'Missed', minutesUntil: null };
  }

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
  missed:   { color: '#ef4444', bg: '#fee2e2', icon: '', joinable: false },
  live:     { color: '#10b981', bg: '#d1fae5', icon: '', joinable: true  },
  imminent: { color: '#3b82f6', bg: '#dbeafe', icon: '', joinable: true  },
  today:    { color: '#3b82f6', bg: '#dbeafe', icon: '', joinable: true  },
  tomorrow: { color: '#3b82f6', bg: '#dbeafe', icon: '', joinable: false },
  upcoming: { color: '#3b82f6', bg: '#dbeafe', icon: '', joinable: false },
  completed:{ color: '#475569', bg: '#f1f5f9', icon: '', joinable: false },
  cancelled:{ color: '#94a3b8', bg: '#f1f5f9', icon: '', joinable: false },
};

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [allCandidates, setAllCandidates] = useState([]);
  const [topCandidates, setTopCandidates] = useState([]);
  const [selJob, setSelJob] = useState('');
  const [loading, setLoading] = useState(true);

  // Custom navbar header states
  const [dashboardSearch, setDashboardSearch] = useState('');
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifs, setNotifs] = useState([]);



  useEffect(() => {
    API.get('/jobs/list').then(r => setJobs(r.data || [])).catch(() => {});
    API.get('/candidates/list').then(r => {
      setAllCandidates(r.data || []);
      const sorted = [...(r.data || [])].sort((a, b) => {
        const scoreA = a.ai_match_score !== undefined && a.ai_match_score !== null ? a.ai_match_score : (a.score || 0);
        const scoreB = b.ai_match_score !== undefined && b.ai_match_score !== null ? b.ai_match_score : (b.score || 0);
        return scoreB - scoreA;
      });
      setTopCandidates(sorted.slice(0, 4));
    }).catch(() => {});

    API.get('/notifications/recent').then(r => setNotifs(r.data || [])).catch(() => {});
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
    const t = setInterval(fetchStats, 60000);
    return () => clearInterval(t);
  }, [selJob]);

  const getGreeting = () => {
    const hr = new Date().getHours();
    if (hr < 12) return 'Good Morning';
    if (hr < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  const getWeeklyDays = () => {
    const days = [];
    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const now = new Date();
    // Generate week starting 3 days ago up to 3 days from now
    for (let i = -3; i <= 3; i++) {
      const d = new Date();
      d.setDate(now.getDate() + i);
      days.push({
        dayName: weekdays[d.getDay()],
        dayNum: d.getDate(),
        isToday: i === 0,
      });
    }
    return days;
  };



  const getDaysOpen = (job) => {
    if (!job.posted_at && !job.created_at) return '12d';
    const postDate = new Date(job.posted_at || job.created_at);
    const diffTime = Math.abs(new Date() - postDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return `${diffDays}d`;
  };

  // Metrics configurations — NO fake trend numbers, only real counts
  const dashboardMetrics = [
    { label: 'Total Jobs', value: jobs.length, trend: `${jobs.length} active`, positive: true, icon: <MdWork style={{ fontSize: 20, color: '#6366f1' }} /> },
    { label: 'Active Applicants', value: stats?.total || 0, trend: `${stats?.applied || 0} pending review`, positive: true, icon: <MdPeople style={{ fontSize: 20, color: '#10b981' }} /> },
    { label: 'Interviews Scheduled', value: stats?.interview_scheduled || 0, trend: `${stats?.interview_completed || 0} completed`, positive: true, icon: <MdCalendarToday style={{ fontSize: 20, color: '#3b82f6' }} /> },
    { label: 'Successful Hires', value: stats?.hired || 0, trend: `${stats?.offered || 0} offered`, positive: true, icon: <MdCheckCircle style={{ fontSize: 20, color: '#8b5cf6' }} /> },
  ];

  const quickActions = [
    { title: 'New Job', desc: 'Create a new job posting', icon: <MdWork style={{ color: '#6366f1', fontSize: 18 }} />, path: '/jobs' },
    { title: 'New Applicant', desc: 'Add a new candidate', icon: <MdPeople style={{ color: '#10b981', fontSize: 18 }} />, path: '/upload' },
    { title: 'Schedule Interview', desc: 'Set up an interview', icon: <MdCalendarToday style={{ color: '#3b82f6', fontSize: 18 }} />, path: '/candidates' },
    { title: 'Compare Resumes', desc: 'AI resume comparison', icon: <MdCompare style={{ color: '#8b5cf6', fontSize: 18 }} />, path: '/compare' },
  ];

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-content" style={{ display: 'flex', flexDirection: 'column', background: '#f8fafc' }}>
        
        {/* ── Custom Header Bar (Ashby Style) ────────────────────────────────── */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '20px 32px',
          borderBottom: '1px solid #e2e8f0',
          background: '#ffffff',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8 }}>
              {getGreeting()}, {user?.name || 'Recruiter'}! 👋
            </h1>
            <p style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>
              Here's what's happening with your hiring pipeline today
            </p>
          </div>

          {/* Center search bar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: 9999,
            padding: '8px 16px',
            width: 320,
            cursor: 'text',
          }} onClick={() => document.getElementById('dashboard-search-input')?.focus()}>
            <MdSearch style={{ color: '#94a3b8', fontSize: 18 }} />
            <input
              id="dashboard-search-input"
              type="text"
              placeholder="Search..."
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                fontSize: 13,
                width: '100%',
                color: '#1e293b',
              }}
              value={dashboardSearch}
              onChange={e => setDashboardSearch(e.target.value)}
            />
            <span style={{
              fontSize: 10,
              color: '#94a3b8',
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: 4,
              padding: '2px 6px',
              fontWeight: 700,
              whiteSpace: 'nowrap',
            }}>
              Ctrl + K
            </span>
          </div>

          {/* Right actions and Profile info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <button className="btn-icon" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', display: 'flex', alignItems: 'center' }}>
                <MdChatBubbleOutline size={20} />
              </button>
              
              <div style={{ position: 'relative' }}>
                <button 
                  className="btn-icon" 
                  onClick={() => setShowNotifs(!showNotifs)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', position: 'relative', display: 'flex', alignItems: 'center' }}
                >
                  <MdNotifications size={22} />
                  {notifs.filter(n => !n.read).length > 0 && (
                    <span style={{ 
                      position: 'absolute', top: 0, right: 0, width: 8, height: 8, 
                      background: '#ef4444', borderRadius: '50%', border: '1.5px solid #fff' 
                    }} />
                  )}
                </button>

                {showNotifs && (
                  <div className="card" style={{ 
                    position: 'absolute', top: 35, right: 0, width: 300, zIndex: 100, 
                    padding: 0, overflow: 'hidden', boxShadow: '0 10px 40px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0',
                    background: '#ffffff'
                  }}>
                    <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', fontSize: 12, fontWeight: 600, color: '#475569' }}>
                      RECENT NOTIFICATIONS
                    </div>
                    <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                      {notifs.length > 0 ? notifs.map(n => (
                        <div key={n.id} style={{ padding: '12px 16px', borderBottom: '1px solid #f1f5f9', background: n.read ? '#fff' : '#f0f9ff' }}>
                          <div style={{ fontSize: 10, fontWeight: 700, color: n.type === 'security' ? '#ef4444' : '#6366f1', marginBottom: 2 }}>
                            {n.type.toUpperCase()}
                          </div>
                          <div style={{ fontSize: 12, color: '#1e293b', lineHeight: 1.4 }}>{n.message}</div>
                          <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>{n.time}</div>
                        </div>
                      )) : (
                        <div style={{ padding: 24, textAlign: 'center', color: '#94a3b8', fontSize: 11 }}>No new notifications</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Profile Avatar Card */}
            <div 
              onClick={() => navigate('/settings')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                borderLeft: '1px solid #e2e8f0',
                paddingLeft: 20,
                cursor: 'pointer'
              }}
              title="Go to Settings"
            >
              <div style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, var(--primary), var(--purple))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                fontWeight: 700,
                fontSize: 14,
              }}>
                {(user?.name || 'A')[0].toUpperCase()}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', lineHeight: 1.2 }}>{user?.name || 'Admin'}</span>
                <span style={{ fontSize: 10.5, color: '#64748b' }}>{user?.role || 'Senior Recruiter'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Page Content (Two-Column Layout) ───────────────────────────────── */}
        <div className="page-body animate-fade" style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24, padding: 32 }}>
          
          {/* LEFT COLUMN: Metrics, Actions, Open Positions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            
            {/* Stat metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
              {dashboardMetrics.map((m, idx) => (
                <div className="card" key={idx} style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 8, minHeight: 120, border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#64748b' }}>{m.label}</span>
                    <div style={{ width: 34, height: 34, borderRadius: 8, background: '#f8fafc', border: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {m.icon}
                    </div>
                  </div>
                  <span style={{ fontSize: 28, fontWeight: 700, color: '#0f172a', lineHeight: 1 }}>{m.value}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: m.positive ? '#10b981' : '#ef4444', display: 'flex', alignItems: 'center' }}>
                      {m.positive ? '↑' : '↓'} {m.trend.split(' ')[0]}
                    </span>
                    <span style={{ fontSize: 11, color: '#64748b' }}>{m.trend.split(' ').slice(1).join(' ')}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Quick Actions Panel */}
            <div className="card" style={{ padding: 24, border: '1px solid #e2e8f0' }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16 }}></span> Quick Actions
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                {quickActions.map((a, idx) => (
                  <div
                    key={idx}
                    onClick={() => navigate(a.path)}
                    style={{
                      padding: 16,
                      borderRadius: 12,
                      border: '1px solid #e2e8f0',
                      background: '#ffffff',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = 'var(--primary)';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.background = '#f8fafc';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = '#e2e8f0';
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.background = '#ffffff';
                    }}
                  >
                    <div style={{
                      width: 40,
                      height: 40,
                      borderRadius: 8,
                      background: '#eff6ff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      {a.icon}
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a' }}>{a.title}</div>
                      <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{a.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Open Positions list */}
            <div className="card" style={{ padding: 24, border: '1px solid #e2e8f0' }}>
              <div className="flex-between" style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 16 }}></span> Open Positions
                </h3>
                <button className="btn btn-outline btn-sm" onClick={() => navigate('/jobs')} style={{ fontSize: 11 }}>
                  View All
                </button>
              </div>

              <div className="table-responsive">
                <table className="table" style={{ fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <th style={{ color: '#64748b', fontWeight: 600, fontSize: 11, paddingBottom: 12 }}>POSITION</th>
                      <th style={{ color: '#64748b', fontWeight: 600, fontSize: 11, paddingBottom: 12 }}>STATUS</th>
                      <th style={{ color: '#64748b', fontWeight: 600, fontSize: 11, paddingBottom: 12, textAlign: 'center' }}>APPLICANTS</th>
                      <th style={{ color: '#64748b', fontWeight: 600, fontSize: 11, paddingBottom: 12, textAlign: 'center' }}>INTERVIEWS</th>
                      <th style={{ color: '#64748b', fontWeight: 600, fontSize: 11, paddingBottom: 12, textAlign: 'center' }}>HIRES</th>
                      <th style={{ color: '#64748b', fontWeight: 600, fontSize: 11, paddingBottom: 12, textAlign: 'right' }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.length > 0 ? jobs.map((j, index) => {
                      const jobCandidates = allCandidates.filter(c => c.job_id === j.id || c.job_id === j._id);
                      
                      return (
                        <tr key={j.id || j._id} style={{ borderBottom: '1px solid #f8fafc' }}>
                          <td style={{ padding: '12px 0' }}>
                            <div style={{ fontWeight: 700, color: '#0f172a' }}>{j.title}</div>
                            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{j.department || 'Engineering'}</div>
                          </td>
                          <td style={{ padding: '12px 0' }}>
                            <span style={{
                              padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700,
                              background: '#d1fae5', color: '#065f46', textTransform: 'uppercase'
                            }}>
                              Active
                            </span>
                          </td>
                          <td style={{ padding: '12px 0', textAlign: 'center', fontWeight: 600, color: '#334155' }}>
                            {jobCandidates.length}
                          </td>
                          <td style={{ padding: '12px 0', textAlign: 'center', fontWeight: 600, color: '#334155' }}>
                            {jobCandidates.filter(c => ['interview_scheduled', 'interview_live'].includes(c.status)).length}
                          </td>
                          <td style={{ padding: '12px 0', textAlign: 'center', fontWeight: 600, color: '#334155' }}>
                            {jobCandidates.filter(c => c.status === 'hired').length}
                          </td>
                          <td style={{ padding: '12px 0', textAlign: 'right' }}>
                            <button className="btn-icon" style={{ color: '#94a3b8', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => navigate('/jobs')}>
                              <MdMoreVert size={18} />
                            </button>
                          </td>
                        </tr>
                      );
                    }) : (
                      <tr>
                        <td colSpan="6" style={{ padding: '40px 0', textAlign: 'center', color: '#94a3b8' }}>
                          No jobs available. Create a new job description to begin tracking.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: Calendar schedule, Pending alerts */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            
            {/* Calendar widget */}
            <div className="card" style={{ padding: 20, borderRadius: 16, border: '1px solid #e2e8f0' }}>
              <h3 style={{ fontSize: 13, fontWeight: 800, color: '#64748b', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: 8 }}>
                <MdCalendarToday style={{ color: '#6366f1' }} /> Schedule
              </h3>
              
              {/* Day selector strip */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6, marginBottom: 20, textAlign: 'center' }}>
                {getWeeklyDays().map((d, i) => (
                  <div key={i} style={{
                    padding: '8px 4px',
                    borderRadius: 8,
                    background: d.isToday ? '#6366f1' : 'transparent',
                    color: d.isToday ? '#ffffff' : '#64748b',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 4
                  }}>
                    <span style={{ fontSize: 10, fontWeight: 600, opacity: d.isToday ? 0.9 : 0.7 }}>{d.dayName}</span>
                    <span style={{ fontSize: 13, fontWeight: 700 }}>{d.dayNum}</span>
                  </div>
                ))}
              </div>

              {/* Schedule list — grouped by actual date */}
              <div>
                {(() => {
                  const allInterviews = stats?.upcoming_interviews || [];
                  if (allInterviews.length === 0) {
                    return (
                      <div style={{ padding: '20px 10px', textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>
                        No interviews scheduled.
                      </div>
                    );
                  }

                  // Use the interview_status the backend already computed — it's the source of truth
                  const todayItems    = allInterviews.filter(i => i.interview_status === 'today' || i.interview_status === 'live');
                  const tomorrowItems = allInterviews.filter(i => i.interview_status === 'tomorrow');
                  const upcomingItems = allInterviews.filter(i => i.interview_status === 'upcoming');
                  const missedItems   = allInterviews.filter(i => i.interview_status === 'missed' || i.interview_status === 'overdue');

                  const renderGroup = (label, items, accentColor) => {
                    if (items.length === 0) return null;
                    return (
                      <div key={label} style={{ marginBottom: 14 }}>
                        <h4 style={{ fontSize: 11, fontWeight: 800, color: accentColor, textTransform: 'uppercase', marginBottom: 10, letterSpacing: '0.5px' }}>{label}</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                          {items.map(item => {
                            const liveStatus = computeInterviewStatus(item.datetime_iso, item.interview_status);
                            const isLive = liveStatus.status === 'live' || liveStatus.status === 'imminent';
                            return (
                              <div
                                key={item.id}
                                style={{
                                  padding: '12px 14px',
                                  borderRadius: 10,
                                  background: '#ffffff',
                                  border: '1px solid #f1f5f9',
                                  borderLeft: isLive ? '4px solid #6366f1' : `4px solid ${accentColor}40`,
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
                                }}
                              >
                                <div style={{ minWidth: 0, flex: 1, marginRight: 8 }}>
                                  <div style={{ fontSize: 12.5, fontWeight: 700, color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {item.candidate_name}
                                  </div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, fontSize: 10.5, color: '#64748b' }}>
                                    <span>{item.time || '--:--'}</span>
                                    <span>•</span>
                                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.job_title}</span>
                                  </div>
                                </div>
                                <div>
                                  {isLive ? (
                                    <button
                                      className="btn btn-primary"
                                      style={{ padding: '4px 10px', fontSize: 11, borderRadius: 8, height: 28 }}
                                      onClick={() => (window.location.href = `/candidates/${item.id}?start=true`)}
                                    >
                                      Join
                                    </button>
                                  ) : (
                                    <span style={{
                                      fontSize: 9, fontWeight: 800,
                                      background: '#e0e7ff', color: '#4338ca',
                                      padding: '2px 8px', borderRadius: 4,
                                      textTransform: 'uppercase', whiteSpace: 'nowrap'
                                    }}>
                                      INTERVIEW
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  };

                  return (
                    <div style={{ maxHeight: 360, overflowY: 'auto' }}>
                      {renderGroup("Today's Schedule", todayItems, '#6366f1')}
                      {renderGroup("Tomorrow", tomorrowItems, '#3b82f6')}
                      {renderGroup("Upcoming", upcomingItems, '#94a3b8')}
                      {renderGroup("Missed", missedItems, '#ef4444')}
                      {todayItems.length === 0 && tomorrowItems.length === 0 && upcomingItems.length === 0 && missedItems.length === 0 && (
                        <div style={{ padding: '20px 10px', textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>
                          No interviews scheduled.
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>



          </div>

        </div>

      </div>
    </div>
  );
}
