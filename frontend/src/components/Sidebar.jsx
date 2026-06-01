import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  MdDashboard, MdPeople, MdWork, MdCloudUpload,
  MdSettings, MdBarChart, MdCompare,
} from 'react-icons/md';

const NAV = [
  { to: '/dashboard', icon: <MdDashboard />, label: 'Dashboard' },
  { to: '/candidates', icon: <MdPeople />,   label: 'Candidates' },
  { to: '/jobs',       icon: <MdWork />,      label: 'Jobs' },
  { to: '/upload',     icon: <MdCloudUpload />, label: 'Upload Resumes' },
  { to: '/compare',    icon: <MdCompare />,   label: 'Compare' },
];

const BOTTOM_NAV = [
  { to: '/settings', icon: <MdSettings />, label: 'Settings' },
];

export default function Sidebar() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="sidebar">
      <div className="sidebar-logo" style={{ borderBottom: '1px solid var(--sidebar-border)', padding: '24px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.25)',
            fontWeight: 800,
            color: '#ffffff',
            fontSize: 16,
            letterSpacing: '-0.5px',
            flexShrink: 0
          }}>
            H
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontWeight: 800, color: '#ffffff', letterSpacing: '-0.5px', fontSize: 19, lineHeight: 1 }}>
              Hire<span style={{ color: '#818cf8' }}>IQ</span>
            </span>
            <span style={{
              fontSize: 9,
              color: '#64748b',
              marginTop: 4,
              letterSpacing: '1.5px',
              fontWeight: 800,
              textTransform: 'uppercase'
            }}>
              Recruiter OS
            </span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section-label" style={{ color: '#64748b', fontSize: 10 }}>Workspace</div>
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            {icon}
            <span>{label}</span>
          </NavLink>
        ))}

        <div className="sidebar-section-label" style={{ marginTop: 12, color: '#64748b', fontSize: 10 }}>Account</div>
        {BOTTOM_NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            {icon}
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer" style={{ borderTop: '1px solid var(--sidebar-border)', background: '#0b0f19' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, var(--primary), var(--purple))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 13, flexShrink: 0 }}>
            {(user?.name || user?.email || 'U')[0].toUpperCase()}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.name || 'HR Recruiter'}
            </div>
            <div style={{ fontSize: 10.5, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email || ''}
            </div>
          </div>
        </div>
        <button className="nav-item" onClick={handleLogout} style={{ color: '#f87171', padding: '8px 12px', border: '1px solid rgba(248, 113, 113, 0.2)', borderRadius: 'var(--radius-sm)', background: 'rgba(248, 113, 113, 0.08)', justifyContent: 'center', fontWeight: 600, fontSize: 12, width: '100%' }}>
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}
