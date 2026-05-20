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
      <div className="sidebar-logo">
        <h2>
          <span className="logo-icon">🤖</span>
          Hire<span>IQ</span>
        </h2>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 4, letterSpacing: '0.5px', fontWeight: 600 }}>
          Recruiter OS
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Workspace</div>
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

        <div className="sidebar-section-label" style={{ marginTop: 8 }}>Account</div>
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

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 13, flexShrink: 0 }}>
            {(user?.name || user?.email || 'U')[0].toUpperCase()}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: '#e5e7eb', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.name || 'HR Recruiter'}
            </div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email || ''}
            </div>
          </div>
        </div>
        <button className="nav-item" onClick={handleLogout} style={{ color: '#f87171', width: '100%' }}>
          <span style={{ fontSize: 15 }}>→</span>
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
}
