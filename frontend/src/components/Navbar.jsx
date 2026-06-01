import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { MdNotifications, MdCircle } from 'react-icons/md';
import API from '../api/client';

export default function Navbar({ title }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifs, setNotifs] = useState([]);

  useEffect(() => {
    API.get('/notifications/recent').then(r => setNotifs(r.data)).catch(() => {});
  }, []);

  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
    : 'HR';

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <header className="navbar">
      <span className="navbar-title">{title}</span>
      <div className="navbar-right">
        
        {/* Notification Bell */}
        <div style={{ position: 'relative', marginRight: 15 }}>
          <button 
            className="btn-icon" 
            onClick={() => setShowNotifs(!showNotifs)}
            style={{ position: 'relative', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', padding: 5 }}
          >
            <MdNotifications size={24} />
            {notifs.filter(n => !n.read).length > 0 && (
              <span style={{ 
                position: 'absolute', top: 2, right: 2, width: 10, height: 10, 
                background: '#ef4444', borderRadius: '50%', border: '2px solid #fff' 
              }} />
            )}
          </button>

          {showNotifs && (
            <div className="card" style={{ 
              position: 'absolute', top: 40, right: 0, width: 300, zIndex: 1000, 
              padding: 0, overflow: 'hidden', boxShadow: '0 10px 40px rgba(0,0,0,0.15)', border: '1px solid #e2e8f0'
            }}>
              <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', fontSize: 12, fontWeight: 600, color: '#475569' }}>
                RECENT NOTIFICATIONS
              </div>
              <div style={{ maxHeight: 350, overflowY: 'auto' }}>
                {notifs.length > 0 ? notifs.map(n => (
                  <div key={n.id} style={{ padding: '12px 16px', borderBottom: '1px solid #f1f5f9', background: n.read ? '#fff' : '#f0f9ff' }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: n.type === 'security' ? '#ef4444' : '#6366f1', marginBottom: 2 }}>
                      {n.type.toUpperCase()}
                    </div>
                    <div style={{ fontSize: 12, color: '#1e293b', lineHeight: 1.4 }}>{n.message}</div>
                    <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>{n.time}</div>
                  </div>
                )) : (
                  <div style={{ padding: 30, textAlign: 'center', color: '#94a3b8', fontSize: 11 }}>No new notifications</div>
                )}
              </div>
              <div style={{ padding: 10, textAlign: 'center', borderTop: '1px solid #e2e8f0', background: '#fff' }}>
                <button className="btn btn-link" style={{ fontSize: 11, fontWeight: 600 }} onClick={() => navigate('/notifications')}>View All Notifications</button>
              </div>
            </div>
          )}
        </div>

        <div className="user-avatar" title={user?.name}>{initials}</div>
        <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)', marginRight: 15 }}>
          {user?.name}
        </span>
        <button className="btn-logout" onClick={handleLogout}>Logout</button>
      </div>
    </header>
  );
}
