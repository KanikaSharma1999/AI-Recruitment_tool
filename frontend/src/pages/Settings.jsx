import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import {
  MdPerson, MdNotifications, MdStickyNote2, MdFolder,
  MdTune, MdEmail, MdLock, MdSave, MdAdd, MdDelete,
  MdVisibility, MdVisibilityOff, MdExpandMore, MdExpandLess,
  MdUpload, MdCheckCircle, MdBusiness, MdSchedule, MdPsychology,
  MdSend, MdInfo
} from 'react-icons/md';

const API = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_BACKEND_URL || '';
const token = () => localStorage.getItem('ats_token');
const hdr = () => ({ Authorization: `Bearer ${token()}` });

// ── Shared ──────────────────────────────────────────────────────────────────
const Section = ({ icon, title, subtitle, children, accent = '#6366f1' }) => (
  <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', overflow: 'hidden', marginBottom: 20, boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}>
    <div style={{ padding: '20px 24px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 14, background: 'linear-gradient(135deg,#fafafa,#f8fafc)' }}>
      <div style={{ width: 40, height: 40, borderRadius: 12, background: accent + '18', display: 'flex', alignItems: 'center', justifyContent: 'center', color: accent, fontSize: 20 }}>{icon}</div>
      <div><div style={{ fontWeight: 600, fontSize: 15, color: '#1e293b' }}>{title}</div>{subtitle && <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{subtitle}</div>}</div>
    </div>
    <div style={{ padding: 24 }}>{children}</div>
  </div>
);

const Field = ({ label, children, hint }) => (
  <div style={{ marginBottom: 18 }}>
    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</label>
    {children}
    {hint && <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>{hint}</p>}
  </div>
);

const Input = (props) => (
  <input {...props} style={{ width: '100%', padding: '10px 12px', border: '1.5px solid #e2e8f0', borderRadius: 10, fontSize: 13, color: '#1e293b', background: '#f8fafc', outline: 'none', boxSizing: 'border-box', ...(props.style || {}) }} />
);

const Select = ({ children, ...props }) => (
  <select {...props} style={{ width: '100%', padding: '10px 12px', border: '1.5px solid #e2e8f0', borderRadius: 10, fontSize: 13, color: '#1e293b', background: '#f8fafc', outline: 'none', boxSizing: 'border-box' }}>{children}</select>
);

const Btn = ({ children, onClick, variant = 'primary', disabled, small, style = {} }) => {
  const bg = variant === 'primary' ? '#6366f1' : variant === 'danger' ? '#ef4444' : variant === 'green' ? '#10b981' : '#f1f5f9';
  const col = ['primary', 'danger', 'green'].includes(variant) ? '#fff' : '#475569';
  return (
    <button onClick={onClick} disabled={disabled} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: small ? '6px 14px' : '10px 20px', borderRadius: 10, border: 'none', cursor: disabled ? 'not-allowed' : 'pointer', background: bg, color: col, fontWeight: 600, fontSize: small ? 12 : 13, opacity: disabled ? 0.6 : 1, ...style }}>
      {children}
    </button>
  );
};

const Toggle = ({ checked, onChange, label }) => (
  <label style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', marginBottom: 14 }}>
    <div onClick={() => onChange(!checked)} style={{ width: 44, height: 24, borderRadius: 12, background: checked ? '#6366f1' : '#e2e8f0', position: 'relative', transition: 'background 0.2s', flexShrink: 0 }}>
      <div style={{ position: 'absolute', top: 3, left: checked ? 22 : 3, width: 18, height: 18, borderRadius: '50%', background: '#fff', transition: 'left 0.2s', boxShadow: '0 1px 4px rgba(0,0,0,0.2)' }} />
    </div>
    <span style={{ fontSize: 13, color: '#1e293b', fontWeight: 500 }}>{label}</span>
  </label>
);

const Accordion = ({ title, children }) => {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ border: '1px solid #e2e8f0', borderRadius: 12, overflow: 'hidden' }}>
      <button onClick={() => setOpen(!open)} style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', background: '#f8fafc', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13, color: '#475569' }}>
        {title} {open ? <MdExpandLess /> : <MdExpandMore />}
      </button>
      {open && <div style={{ padding: 20, borderTop: '1px solid #f1f5f9' }}>{children}</div>}
    </div>
  );
};

// ── Sections ────────────────────────────────────────────────────────────────
function AccountSection() {
  const { user, updateProfile } = useAuth();
  const [form, setForm] = useState({ name: '', company: '', role: '' });
  const [pass, setPass] = useState({ current: '', next: '', confirm: '' });
  const [showP, setShowP] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setForm({
        name: user.name || '',
        company: user.company_name || '',
        role: user.role || 'HR Recruiter'
      });
    }
  }, [user]);

  const save = async () => {
    setSaving(true);
    try {
      await updateProfile({
        name: form.name,
        company_name: form.company,
        role: form.role
      });
      toast.success('Profile saved successfully');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const changePass = async () => {
    if (pass.next !== pass.confirm) return toast.error('Passwords do not match');
    if (pass.next.length < 6) return toast.error('Password must be at least 6 characters');
    try {
      await updateProfile({ password: pass.next });
      toast.success('Password updated successfully');
      setPass({ current: '', next: '', confirm: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update password');
    }
  };

  return (
    <Section icon={<MdPerson />} title="Account & Profile" subtitle="Manage your recruiter identity" accent="#6366f1">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
        <Field label="Full Name"><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Your full name" /></Field>
        <Field label="Job Title / Role"><Input value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} placeholder="HR Recruiter" /></Field>
        <Field label="Company Name"><Input value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} placeholder="Acme Corp" /></Field>
      </div>
      <Btn onClick={save} disabled={saving} style={{ marginTop: 8 }}><MdSave /> {saving ? 'Saving...' : 'Save Profile'}</Btn>

      <div style={{ marginTop: 28, paddingTop: 24, borderTop: '1px solid #f1f5f9' }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: '#1e293b', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}><MdLock style={{ color: '#6366f1' }} /> Change Password</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
          <Field label="Current Password">
            <div style={{ position: 'relative' }}>
              <Input type={showP ? 'text' : 'password'} value={pass.current} onChange={e => setPass({ ...pass, current: e.target.value })} placeholder="Current" />
              <button onClick={() => setShowP(!showP)} style={{ position: 'absolute', right: 10, top: 10, background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
                {showP ? <MdVisibilityOff size={16} /> : <MdVisibility size={16} />}
              </button>
            </div>
          </Field>
          <Field label="New Password"><Input type="password" value={pass.next} onChange={e => setPass({ ...pass, next: e.target.value })} placeholder="New password" /></Field>
          <Field label="Confirm Password"><Input type="password" value={pass.confirm} onChange={e => setPass({ ...pass, confirm: e.target.value })} placeholder="Confirm" /></Field>
        </div>
        <Btn onClick={changePass} variant="primary" small><MdLock /> Update Password</Btn>
      </div>
    </Section>
  );
}



function EmailSection() {
  const [config, setConfig] = useState({ provider: 'gmail', smtp_host: 'smtp.gmail.com', smtp_port: 587, smtp_user: '', smtp_password: '', from_email: '', app_name: 'AI Hiring Platform', use_tls: true });
  const [showPass, setShowPass] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testTarget, setTestTarget] = useState('');

  useEffect(() => {
    axios.get(`${API}/settings/email`, { headers: hdr() }).then(r => setConfig(r.data)).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try { await axios.post(`${API}/settings/email`, config, { headers: hdr() }); toast.success('Email config saved'); }
    catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
    finally { setSaving(false); }
  };

  const test = async () => {
    if (!testTarget) return toast.error('Enter a target email');
    setTesting(true);
    try { await axios.post(`${API}/settings/test-email`, { settings: config, target_email: testTarget }, { headers: hdr() }); toast.success('Test email sent!'); }
    catch (e) { toast.error(e.response?.data?.detail || 'Test failed'); }
    finally { setTesting(false); }
  };

  return (
    <Section icon={<MdEmail />} title="Advanced Email Configuration" subtitle="SMTP settings for HR notification delivery" accent="#0ea5e9">
      <Accordion title="SMTP Configuration (click to expand)">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
          <Field label="SMTP Host"><Input value={config.smtp_host} onChange={e => setConfig({ ...config, smtp_host: e.target.value })} placeholder="smtp.gmail.com" /></Field>
          <Field label="SMTP Port"><Input type="number" value={config.smtp_port} onChange={e => setConfig({ ...config, smtp_port: +e.target.value })} /></Field>
          <Field label="SMTP Username / Email"><Input value={config.smtp_user} onChange={e => setConfig({ ...config, smtp_user: e.target.value })} placeholder="you@gmail.com" /></Field>
          <Field label="App Password" hint="For Gmail: use a 16-char App Password">
            <div style={{ position: 'relative' }}>
              <Input type={showPass ? 'text' : 'password'} value={config.smtp_password} onChange={e => setConfig({ ...config, smtp_password: e.target.value })} placeholder="App password" />
              <button onClick={() => setShowPass(!showPass)} style={{ position: 'absolute', right: 10, top: 10, background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}>
                {showPass ? <MdVisibilityOff size={16} /> : <MdVisibility size={16} />}
              </button>
            </div>
          </Field>
          <Field label="From Email"><Input value={config.from_email} onChange={e => setConfig({ ...config, from_email: e.target.value })} placeholder="noreply@company.com" /></Field>
          <Field label="App Name"><Input value={config.app_name} onChange={e => setConfig({ ...config, app_name: e.target.value })} /></Field>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', marginBottom: 16 }}>
          <input type="checkbox" checked={config.use_tls} onChange={e => setConfig({ ...config, use_tls: e.target.checked })} />
          Enable TLS (recommended for port 587)
        </label>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Btn onClick={save} disabled={saving}><MdSave /> {saving ? 'Saving...' : 'Save Config'}</Btn>
        </div>
      </Accordion>
      <div style={{ marginTop: 16, display: 'flex', gap: 10, alignItems: 'center' }}>
        <Input value={testTarget} onChange={e => setTestTarget(e.target.value)} placeholder="Send test email to..." style={{ maxWidth: 280 }} />
        <Btn onClick={test} disabled={testing} variant="green"><MdSend /> {testing ? 'Sending...' : 'Send Test'}</Btn>
      </div>
    </Section>
  );
}

function RankingConfigSection() {
  const [preset, setPreset] = useState('Software Engineer');
  const [weights, setWeights] = useState({
    skills: 40,
    experience: 25,
    semantic: 15,
    projects: 10,
    certifications: 5,
    quality: 5
  });
  const [saving, setSaving] = useState(false);

  const presets = {
    'Software Engineer': { skills: 40, experience: 25, semantic: 15, projects: 10, certifications: 5, quality: 5 },
    'Fresher Hiring': { skills: 30, experience: 5, semantic: 20, projects: 25, certifications: 10, quality: 10 },
    'Senior Hiring': { skills: 30, experience: 40, semantic: 10, projects: 10, certifications: 5, quality: 5 },
    'Data Science': { skills: 45, experience: 20, semantic: 15, projects: 10, certifications: 5, quality: 5 },
    'Custom': null
  };

  useEffect(() => {
    axios.get(`${API}/settings/ranking`, { headers: hdr() })
      .then(res => {
        if (res.data) {
          setPreset(res.data.preset || 'Software Engineer');
          if (res.data.weights) {
            setWeights(res.data.weights);
          }
        }
      })
      .catch(err => {
        console.error('Failed to load ranking settings', err);
      });
  }, []);

  const handlePresetChange = (p) => {
    setPreset(p);
    if (presets[p]) {
      setWeights(presets[p]);
    }
  };

  const handleWeightChange = (key, val) => {
    const intVal = parseInt(val) || 0;
    const clamped = Math.max(0, Math.min(100, intVal));
    
    setWeights(prev => {
      const updated = { ...prev, [key]: clamped };
      // Check if matches any preset. If not, set to Custom
      let matchedPreset = 'Custom';
      for (const [name, w] of Object.entries(presets)) {
        if (w && Object.keys(w).every(k => w[k] === updated[k])) {
          matchedPreset = name;
          break;
        }
      }
      setPreset(matchedPreset);
      return updated;
    });
  };

  const total = weights.skills + weights.experience + weights.semantic + weights.projects + weights.certifications + weights.quality;
  const isValid = total === 100;

  const save = async () => {
    if (!isValid) return;
    setSaving(true);
    try {
      await axios.post(`${API}/settings/ranking`, { preset, weights }, { headers: hdr() });
      toast.success('Ranking weights updated successfully');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section icon={<MdTune />} title="Candidate Ranking Configuration" subtitle="Configure weight distribution to customize AI evaluation criteria" accent="#6366f1">
      <div style={{ marginBottom: 20 }}>
        <Field label="Configuration Preset" hint="Select a standard preset or adjust values to create a custom weighting mix.">
          <Select value={preset} onChange={e => handlePresetChange(e.target.value)}>
            {Object.keys(presets).map(name => <option key={name} value={name}>{name}</option>)}
          </Select>
        </Field>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        <Field label={`Skills Match — ${weights.skills}%`} hint="Relevance of candidate skills against JD required/preferred skills.">
          <input type="range" min={0} max={100} value={weights.skills} onChange={e => handleWeightChange('skills', e.target.value)} style={{ width: '100%', accentColor: '#6366f1' }} />
        </Field>
        <Field label={`Experience Match — ${weights.experience}%`} hint="Total and relevant professional tenure compared to requirements.">
          <input type="range" min={0} max={100} value={weights.experience} onChange={e => handleWeightChange('experience', e.target.value)} style={{ width: '100%', accentColor: '#6366f1' }} />
        </Field>
        <Field label={`Semantic Similarity — ${weights.semantic}%`} hint="Sentence-transformer textual correlation of resume and JD.">
          <input type="range" min={0} max={100} value={weights.semantic} onChange={e => handleWeightChange('semantic', e.target.value)} style={{ width: '100%', accentColor: '#6366f1' }} />
        </Field>
        <Field label={`Projects — ${weights.projects}%`} hint="Presence and relevance of documented projects.">
          <input type="range" min={0} max={100} value={weights.projects} onChange={e => handleWeightChange('projects', e.target.value)} style={{ width: '100%', accentColor: '#6366f1' }} />
        </Field>
        <Field label={`Certifications — ${weights.certifications}%`} hint="Alignment of professional certifications.">
          <input type="range" min={0} max={100} value={weights.certifications} onChange={e => handleWeightChange('certifications', e.target.value)} style={{ width: '100%', accentColor: '#6366f1' }} />
        </Field>
        <Field label={`Resume Quality — ${weights.quality}%`} hint="Format, depth, layout completeness, and lack of warning indicators.">
          <input type="range" min={0} max={100} value={weights.quality} onChange={e => handleWeightChange('quality', e.target.value)} style={{ width: '100%', accentColor: '#6366f1' }} />
        </Field>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 16, background: isValid ? '#f0fdf4' : '#fef2f2', border: `1px solid ${isValid ? '#bbf7d0' : '#fecaca'}`, borderRadius: 12, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontWeight: 600, fontSize: 14, color: isValid ? '#166534' : '#991b1b' }}>
            Total Allocated Weight:
          </span>
          <span style={{ fontWeight: 700, fontSize: 18, color: isValid ? '#15803d' : '#dc2626' }}>
            {total}%
          </span>
        </div>
        {!isValid && (
          <p style={{ margin: 0, fontSize: 12, color: '#b91c1c' }}>
            ⚠️ Sum of weights must equal exactly 100%. Please adjust sliders (current gap: {100 - total}%).
          </p>
        )}
        {isValid && (
          <p style={{ margin: 0, fontSize: 12, color: '#166534' }}>
            ✅ Weights are perfectly balanced! Ready to save.
          </p>
        )}
      </div>

      <Btn onClick={save} disabled={!isValid || saving}><MdSave /> {saving ? 'Saving...' : 'Save Ranking Config'}</Btn>
    </Section>
  );
}

// ── Navigation tabs ─────────────────────────────────────────────────────────
const TABS = [
  { id: 'account', label: 'Account', icon: <MdPerson /> },
  { id: 'ranking', label: 'Ranking Config', icon: <MdTune /> },
  { id: 'email', label: 'Email Config', icon: <MdEmail /> },
];

export default function Settings() {
  const [activeTab, setActiveTab] = useState('account');

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <Navbar title="Recruiter Control Center" />
        <div className="page-body animate-fade">
          <div style={{ marginBottom: 24 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1e293b' }}>HR Workspace Settings</h1>
            <p style={{ color: '#64748b', fontSize: 13 }}>Manage your recruiter profile, preferences, notes, and platform intelligence.</p>
          </div>

          {/* Tab bar */}
          <div style={{ display: 'flex', gap: 6, marginBottom: 28, background: '#f8fafc', padding: 6, borderRadius: 14, border: '1px solid #e2e8f0', flexWrap: 'wrap' }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setActiveTab(t.id)} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 10, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13, transition: 'all 0.15s', background: activeTab === t.id ? '#6366f1' : 'transparent', color: activeTab === t.id ? '#fff' : '#64748b' }}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          {/* Content */}
          {activeTab === 'account'       && <AccountSection />}
          {activeTab === 'ranking'       && <RankingConfigSection />}
          {activeTab === 'email'         && <EmailSection />}
        </div>
      </main>
    </div>
  );
}

