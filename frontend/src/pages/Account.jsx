import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import toast from 'react-hot-toast';
import { MdPerson, MdEmail, MdLock, MdSave, MdCheckCircle } from 'react-icons/md';

export default function Account() {
  const { user, updateProfile } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (password && password !== confirmPassword) {
      return toast.error('Passwords do not match');
    }

    setLoading(true);
    try {
      const updateData = { name, email };
      if (password) updateData.password = password;
      
      await updateProfile(updateData);
      toast.success('Profile updated successfully');
      setPassword('');
      setConfirmPassword('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <Navbar title="My Account" />
        
        <div className="page-body animate-fade">
          <div className="page-header">
            <h1>Profile Settings</h1>
            <p>Manage your account details and security preferences.</p>
          </div>

          <div className="card" style={{ maxWidth: 600 }}>
            <div className="flex-between" style={{ marginBottom: 24 }}>
                <div className="flex-center gap-8">
                    <div className="user-avatar" style={{ width: 48, height: 48, fontSize: 18 }}>
                        {user?.name?.charAt(0) || 'U'}
                    </div>
                    <div>
                        <h3 style={{ fontSize: 16 }}>{user?.name}</h3>
                        <span className="badge badge-shortlisted">{user?.role?.toUpperCase()}</span>
                    </div>
                </div>
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <div style={{ position: 'relative' }}>
                        <MdPerson style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-secondary)' }} />
                        <input 
                            type="text" className="form-input" style={{ paddingLeft: 40 }}
                            value={name} onChange={e => setName(e.target.value)}
                            required
                        />
                    </div>
                </div>

                <div className="form-group">
                    <label className="form-label">Email Address</label>
                    <div style={{ position: 'relative' }}>
                        <MdEmail style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-secondary)' }} />
                        <input 
                            type="email" className="form-input" style={{ paddingLeft: 40 }}
                            value={email} onChange={e => setEmail(e.target.value)}
                            required
                        />
                    </div>
                </div>

                <div className="divider" />
                
                <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: -4 }}>Change Password</h4>
                <p className="text-muted text-sm">Leave blank to keep your current password.</p>

                <div className="form-grid">
                    <div className="form-group">
                        <label className="form-label">New Password</label>
                        <div style={{ position: 'relative' }}>
                            <MdLock style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-secondary)' }} />
                            <input 
                                type="password" className="form-input" style={{ paddingLeft: 40 }}
                                placeholder="••••••••"
                                value={password} onChange={e => setPassword(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Confirm New Password</label>
                        <div style={{ position: 'relative' }}>
                            <MdLock style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-secondary)' }} />
                            <input 
                                type="password" className="form-input" style={{ paddingLeft: 40 }}
                                placeholder="••••••••"
                                value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                <button type="submit" className="btn btn-primary" disabled={loading} style={{ padding: '12px', justifyContent: 'center', marginTop: 10 }}>
                    {loading ? <span className="spinner" /> : <><MdSave /> Save Changes</>}
                </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
