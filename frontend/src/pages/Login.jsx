import { useState, useEffect } from 'react';
import API from '../api/client';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import { MdEmail, MdLock, MdLogin, MdVisibility, MdVisibilityOff, MdShield } from 'react-icons/md';

export default function Login() {
  const [email, setEmail] = useState(() => {
    const saved = localStorage.getItem('ats_remembered_email') || '';
    return saved === 'sandhyagowda506@gmail.com' ? '' : saved;
  });
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => {
    return localStorage.getItem('ats_remember_me') === 'true';
  });
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const [isDbOffline, setIsDbOffline] = useState(false);
  const [backendOffline, setBackendOffline] = useState(false);

  useEffect(() => {
    API.get('/health').then(res => {
      const overallStatus = res.data?.status;
      const dbStatus = res.data?.database?.status;
      setIsDbOffline(overallStatus !== 'ok' || dbStatus === 'offline');
      setBackendOffline(false);
    }).catch(() => {
      setBackendOffline(true);
      setIsDbOffline(true);
    });
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email.trim(), password);
      if (rememberMe) {
        localStorage.setItem('ats_remembered_email', email.trim());
        localStorage.setItem('ats_remember_me', 'true');
      } else {
        localStorage.removeItem('ats_remembered_email');
        localStorage.setItem('ats_remember_me', 'false');
      }
      toast.success('Welcome back!');
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Invalid credentials';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = (e) => {
    e.preventDefault();
    toast.error('Self-service password recovery is disabled. Please contact your system administrator.');
  };

  return (
    <div className="login-page" style={{ background: '#0f172a', color: '#f8fafc', position: 'relative', overflow: 'hidden', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {/* Decorative premium dark gradient blobs */}
      <div style={{
        position:'absolute', width:500, height:500, borderRadius:'50%',
        background:'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)',
        top:-150, right:-150, pointerEvents:'none'
      }} />
      <div style={{
        position:'absolute', width:400, height:400, borderRadius:'50%',
        background:'radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)',
        bottom:-120, left:-120, pointerEvents:'none'
      }} />

      <div className="login-card animate-slide" style={{ background: '#1e293b', border: '1px solid #334155', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)', borderRadius: 16, padding: 40, width: '100%', maxWidth: 440 }}>
        <div style={{ textAlign: 'center', marginBottom: 30 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 48, height: 48, borderRadius: 12, background: 'rgba(99,102,241,0.1)', color: '#818cf8', marginBottom: 16 }}>
            <MdShield size={28} />
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 600, color: '#fff', margin: 0, letterSpacing: '-0.5px' }}>
            Hire<span style={{ color: '#818cf8' }}>IQ</span> <span style={{ fontWeight: 400, fontSize: 18, color: '#94a3b8' }}>SaaS Portal</span>
          </h1>
          <p style={{ color: '#94a3b8', fontSize: 13, marginTop: 6, marginBottom: 0 }}>
            Enterprise AI Recruitment Intelligence Platform
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display:'flex', flexDirection:'column', gap:20 }}>
          <div className="form-group">
            <label className="form-label" style={{ color: '#cbd5e1', fontWeight: 600, fontSize: 13 }}>
              <span style={{ display:'flex', alignItems:'center', gap:8 }}>
                <MdEmail style={{ color:'#818cf8' }} /> Recruiter Email
              </span>
            </label>
            <input
              type="email" className="form-input"
              style={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8, padding: '10px 14px', width: '100%' }}
              placeholder="recruiter@company.com"
              value={email} onChange={e => setEmail(e.target.value)}
              required autoFocus
            />
          </div>

          <div className="form-group" style={{ position: 'relative' }}>
            <label className="form-label" style={{ color: '#cbd5e1', fontWeight: 600, fontSize: 13 }}>
              <span style={{ display:'flex', alignItems:'center', gap:8 }}>
                <MdLock style={{ color:'#818cf8' }} /> Password
              </span>
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? "text" : "password"} className="form-input"
                style={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8, padding: '10px 40px 10px 14px', width: '100%' }}
                placeholder="••••••••"
                value={password} onChange={e => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0 }}
              >
                {showPassword ? <MdVisibilityOff size={20} /> : <MdVisibility size={20} />}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: -4 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#94a3b8', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={e => setRememberMe(e.target.checked)}
                style={{ accentColor: '#818cf8', cursor: 'pointer' }}
              />
              Remember Me
            </label>
            <a
              href="#"
              onClick={handleForgotPassword}
              style={{ fontSize: 13, color: '#818cf8', textDecoration: 'none', fontWeight: 500 }}
            >
              Forgot Password?
            </a>
          </div>

          <button type="submit" className="btn btn-primary"
            disabled={loading || isDbOffline || backendOffline}
            style={{ padding:'12px', fontSize:15, marginTop:8, justifyContent:'center', background: '#6366f1', border: 'none', color: '#fff', borderRadius: 8, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
            {loading ? <span className="spinner" /> : (backendOffline ? 'Backend Offline' : (isDbOffline ? 'Database Offline' : <><MdLogin /> Sign In</>))}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 24, fontSize: 14, color: '#94a3b8' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: '#818cf8', textDecoration: 'none', fontWeight: 600 }}>
            Create Account
          </Link>
        </div>
      </div>
    </div>
  );
}
