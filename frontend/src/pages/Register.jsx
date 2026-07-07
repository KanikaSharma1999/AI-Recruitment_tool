import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';
import { MdEmail, MdLock, MdPerson, MdBusiness, MdVisibility, MdVisibilityOff, MdShield } from 'react-icons/md';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const { signup } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (password.length < 6) {
      toast.error('Password must be at least 6 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await signup({
        name: name.trim(),
        email: email.trim(),
        password,
        company_name: companyName.trim()
      });
      toast.success('Registration successful! Please sign in.');
      navigate('/login');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Registration failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-page" style={{ background: '#0f172a', color: '#f8fafc', position: 'relative', overflow: 'hidden', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px 0' }}>
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

      <div className="register-card animate-slide" style={{ background: '#1e293b', border: '1px solid #334155', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)', borderRadius: 16, padding: 40, width: '100%', maxWidth: 460, position: 'relative', zIndex: 10 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 48, height: 48, borderRadius: 12, background: 'rgba(99,102,241,0.1)', color: '#818cf8', marginBottom: 16 }}>
            <MdShield size={28} />
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 600, color: '#fff', margin: 0, letterSpacing: '-0.5px' }}>
            Create <span style={{ color: '#818cf8' }}>Account</span>
          </h1>
          <p style={{ color: '#94a3b8', fontSize: 13, marginTop: 6, marginBottom: 0 }}>
            Register as an enterprise recruiter on HireIQ
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="form-group">
            <label className="form-label" style={{ color: '#cbd5e1', fontWeight: 600, fontSize: 13, marginBottom: 6, display: 'block' }}>
              <span style={{ display:'flex', alignItems:'center', gap:8 }}>
                <MdPerson style={{ color:'#818cf8' }} /> Full Name
              </span>
            </label>
            <input
              type="text" className="form-input"
              style={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8, padding: '10px 14px', width: '100%', boxSizing: 'border-box' }}
              placeholder="Sarah Jenkins"
              value={name} onChange={e => setName(e.target.value)}
              required autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" style={{ color: '#cbd5e1', fontWeight: 600, fontSize: 13, marginBottom: 6, display: 'block' }}>
              <span style={{ display:'flex', alignItems:'center', gap:8 }}>
                <MdEmail style={{ color:'#818cf8' }} /> Recruiter Email
              </span>
            </label>
            <input
              type="email" className="form-input"
              style={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8, padding: '10px 14px', width: '100%', boxSizing: 'border-box' }}
              placeholder="recruiter@company.com"
              value={email} onChange={e => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" style={{ color: '#cbd5e1', fontWeight: 600, fontSize: 13, marginBottom: 6, display: 'block' }}>
              <span style={{ display:'flex', alignItems:'center', gap:8 }}>
                <MdBusiness style={{ color:'#818cf8' }} /> Company Name (Optional)
              </span>
            </label>
            <input
              type="text" className="form-input"
              style={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8, padding: '10px 14px', width: '100%', boxSizing: 'border-box' }}
              placeholder="Acme Corp"
              value={companyName} onChange={e => setCompanyName(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ position: 'relative' }}>
            <label className="form-label" style={{ color: '#cbd5e1', fontWeight: 600, fontSize: 13, marginBottom: 6, display: 'block' }}>
              <span style={{ display:'flex', alignItems:'center', gap:8 }}>
                <MdLock style={{ color:'#818cf8' }} /> Password
              </span>
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? "text" : "password"} className="form-input"
                style={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8, padding: '10px 40px 10px 14px', width: '100%', boxSizing: 'border-box' }}
                placeholder="Minimum 6 characters"
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

          <div className="form-group" style={{ position: 'relative' }}>
            <label className="form-label" style={{ color: '#cbd5e1', fontWeight: 600, fontSize: 13, marginBottom: 6, display: 'block' }}>
              <span style={{ display:'flex', alignItems:'center', gap:8 }}>
                <MdLock style={{ color:'#818cf8' }} /> Confirm Password
              </span>
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showConfirmPassword ? "text" : "password"} className="form-input"
                style={{ background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: 8, padding: '10px 40px 10px 14px', width: '100%', boxSizing: 'border-box' }}
                placeholder="••••••••"
                value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0 }}
              >
                {showConfirmPassword ? <MdVisibilityOff size={20} /> : <MdVisibility size={20} />}
              </button>
            </div>
          </div>

          <button type="submit" className="btn btn-primary"
            disabled={loading}
            style={{ padding:'12px', fontSize:15, marginTop:8, justifyContent:'center', background: '#6366f1', border: 'none', color: '#fff', borderRadius: 8, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
            {loading ? <span className="spinner" /> : 'Register'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 24, fontSize: 14, color: '#94a3b8' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: '#818cf8', textDecoration: 'none', fontWeight: 600 }}>
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
