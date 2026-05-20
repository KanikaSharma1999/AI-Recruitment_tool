import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import {
  MdPerson, MdNotifications, MdStickyNote2, MdFolder,
  MdTune, MdEmail, MdLock, MdSave, MdAdd, MdDelete,
  MdVisibility, MdVisibilityOff, MdExpandMore, MdExpandLess,
  MdUpload, MdCheckCircle, MdBusiness, MdSchedule, MdPsychology,
  MdSend, MdInfo
} from 'react-icons/md';

const API = 'http://localhost:8000';
const token = () => localStorage.getItem('ats_token');
const hdr = () => ({ Authorization: `Bearer ${token()}` });

// ── Shared ──────────────────────────────────────────────────────────────────
const Section = ({ icon, title, subtitle, children, accent = '#6366f1' }) => (
  <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', overflow: 'hidden', marginBottom: 20, boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}>
    <div style={{ padding: '20px 24px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 14, background: 'linear-gradient(135deg,#fafafa,#f8fafc)' }}>
      <div style={{ width: 40, height: 40, borderRadius: 12, background: accent + '18', display: 'flex', alignItems: 'center', justifyContent: 'center', color: accent, fontSize: 20 }}>{icon}</div>
      <div><div style={{ fontWeight: 800, fontSize: 15, color: '#1e293b' }}>{title}</div>{subtitle && <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{subtitle}</div>}</div>
    </div>
    <div style={{ padding: 24 }}>{children}</div>
  </div>
);

const Field = ({ label, children, hint }) => (
  <div style={{ marginBottom: 18 }}>
    <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</label>
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
    <button onClick={onClick} disabled={disabled} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: small ? '6px 14px' : '10px 20px', borderRadius: 10, border: 'none', cursor: disabled ? 'not-allowed' : 'pointer', background: bg, color: col, fontWeight: 700, fontSize: small ? 12 : 13, opacity: disabled ? 0.6 : 1, ...style }}>
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
      <button onClick={() => setOpen(!open)} style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', background: '#f8fafc', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 13, color: '#475569' }}>
        {title} {open ? <MdExpandLess /> : <MdExpandMore />}
      </button>
      {open && <div style={{ padding: 20, borderTop: '1px solid #f1f5f9' }}>{children}</div>}
    </div>
  );
};

// ── Sections ────────────────────────────────────────────────────────────────
function AccountSection() {
  const [form, setForm] = useState({ name: '', company: '', role: '' });
  const [pass, setPass] = useState({ current: '', next: '', confirm: '' });
  const [showP, setShowP] = useState(false);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    setForm({ name: user.name || '', company: user.company || '', role: user.role || 'HR Recruiter' });
  }, []);

  const save = () => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    localStorage.setItem('user', JSON.stringify({ ...user, ...form }));
    toast.success('Profile saved');
  };

  const changePass = () => {
    if (pass.next !== pass.confirm) return toast.error('Passwords do not match');
    if (pass.next.length < 6) return toast.error('Password must be at least 6 characters');
    toast.success('Password updated (demo mode)');
    setPass({ current: '', next: '', confirm: '' });
  };

  return (
    <Section icon={<MdPerson />} title="Account & Profile" subtitle="Manage your recruiter identity" accent="#6366f1">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Field label="Full Name"><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Your full name" /></Field>
        <Field label="Job Title / Role"><Input value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} placeholder="HR Recruiter" /></Field>
        <Field label="Company Name"><Input value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} placeholder="Acme Corp" /></Field>
        <Field label="Profile Photo">
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', border: '1.5px dashed #c7d2fe', borderRadius: 10, cursor: 'pointer', fontSize: 13, color: '#6366f1', fontWeight: 600 }}>
            <MdUpload /> Upload Photo <input type="file" accept="image/*" hidden />
          </label>
        </Field>
      </div>
      <Btn onClick={save} style={{ marginTop: 8 }}><MdSave /> Save Profile</Btn>

      <div style={{ marginTop: 28, paddingTop: 24, borderTop: '1px solid #f1f5f9' }}>
        <div style={{ fontWeight: 800, fontSize: 14, color: '#1e293b', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}><MdLock style={{ color: '#6366f1' }} /> Change Password</div>
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

function NotificationsSection() {
  const [prefs, setPrefs] = useState({ emailNotifications: true, interviewReminders: true, aiReports: true, dailySummary: false, reminderMinutes: 15 });
  const toggle = k => setPrefs(p => ({ ...p, [k]: !p[k] }));
  return (
    <Section icon={<MdNotifications />} title="Notification Preferences" subtitle="Control when and how you get notified" accent="#f59e0b">
      <Toggle checked={prefs.emailNotifications} onChange={() => toggle('emailNotifications')} label="Email notifications for new candidate activity" />
      <Toggle checked={prefs.interviewReminders} onChange={() => toggle('interviewReminders')} label="Interview reminder emails before sessions" />
      <Toggle checked={prefs.aiReports} onChange={() => toggle('aiReports')} label="AI report ready notifications" />
      <Toggle checked={prefs.dailySummary} onChange={() => toggle('dailySummary')} label="Daily hiring pipeline summary (7:00 AM)" />
      <Field label="Reminder timing (minutes before interview)">
        <Select value={prefs.reminderMinutes} onChange={e => setPrefs(p => ({ ...p, reminderMinutes: +e.target.value }))}>
          {[5, 10, 15, 30, 60].map(m => <option key={m} value={m}>{m} minutes before</option>)}
        </Select>
      </Field>
      <Btn onClick={() => toast.success('Preferences saved')}><MdSave /> Save Preferences</Btn>
    </Section>
  );
}

function NotesSection() {
  const [notes, setNotes] = useState(() => JSON.parse(localStorage.getItem('hr_notes') || '[]'));
  const [text, setText] = useState('');
  const [type, setType] = useState('note');

  const add = () => {
    if (!text.trim()) return;
    const n = [...notes, { id: Date.now(), text, type, created: new Date().toLocaleString() }];
    setNotes(n);
    localStorage.setItem('hr_notes', JSON.stringify(n));
    setText('');
    toast.success('Note added');
  };

  const del = id => {
    const n = notes.filter(x => x.id !== id);
    setNotes(n);
    localStorage.setItem('hr_notes', JSON.stringify(n));
  };

  const colors = { note: '#fef3c7', reminder: '#dbeafe', task: '#d1fae5', observation: '#ede9fe' };
  const labels = { note: '📌 Note', reminder: '⏰ Reminder', task: '✅ Task', observation: '🔍 Observation' };

  return (
    <Section icon={<MdStickyNote2 />} title="HR Notes & Reminder Workspace" subtitle="Private recruiter workspace — sticky notes, tasks, follow-ups" accent="#8b5cf6">
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <Select value={type} onChange={e => setType(e.target.value)} style={{ width: 160 }}>
          <option value="note">📌 Note</option>
          <option value="reminder">⏰ Reminder</option>
          <option value="task">✅ Task</option>
          <option value="observation">🔍 Observation</option>
        </Select>
        <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && add()} placeholder="Add a note, task, or follow-up reminder..." style={{ flex: 1, padding: '10px 14px', border: '1.5px solid #e2e8f0', borderRadius: 10, fontSize: 13, outline: 'none' }} />
        <Btn onClick={add} variant="primary"><MdAdd /> Add</Btn>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14 }}>
        {notes.length === 0 && <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#94a3b8', padding: 40, fontSize: 13 }}>No notes yet. Add your first recruiter note above.</div>}
        {notes.map(n => (
          <div key={n.id} style={{ background: colors[n.type], borderRadius: 12, padding: 16, position: 'relative', minHeight: 90, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', marginBottom: 8 }}>{labels[n.type]}</div>
            <div style={{ fontSize: 13, color: '#1e293b', fontWeight: 500, lineHeight: 1.5 }}>{n.text}</div>
            <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 10 }}>{n.created}</div>
            <button onClick={() => del(n.id)} style={{ position: 'absolute', top: 10, right: 10, background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: 2 }}><MdDelete size={16} /></button>
          </div>
        ))}
      </div>
    </Section>
  );
}

function VaultSection() {
  const [files, setFiles] = useState(() => JSON.parse(localStorage.getItem('hr_vault') || '[]'));
  const [category, setCategory] = useState('interview_template');
  const fileRef = useRef();

  const upload = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const entry = { id: Date.now(), name: f.name, size: (f.size / 1024).toFixed(1) + ' KB', category, uploaded: new Date().toLocaleString() };
    const updated = [...files, entry];
    setFiles(updated);
    localStorage.setItem('hr_vault', JSON.stringify(updated));
    toast.success(`${f.name} uploaded to vault`);
  };

  const del = id => {
    const updated = files.filter(f => f.id !== id);
    setFiles(updated);
    localStorage.setItem('hr_vault', JSON.stringify(updated));
  };

  const catLabels = { interview_template: '📋 Interview Template', evaluation_form: '📊 Evaluation Form', onboarding: '🚀 Onboarding Doc', policy: '📜 HR Policy', other: '📁 Other' };
  const catColor = { interview_template: '#dbeafe', evaluation_form: '#d1fae5', onboarding: '#fef3c7', policy: '#fee2e2', other: '#f1f5f9' };

  return (
    <Section icon={<MdFolder />} title="HR Secure Vault" subtitle="Private recruiter-only document storage" accent="#10b981">
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <Select value={category} onChange={e => setCategory(e.target.value)} style={{ width: 220 }}>
          {Object.entries(catLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
        <Btn onClick={() => fileRef.current.click()} variant="primary"><MdUpload /> Upload File</Btn>
        <input ref={fileRef} type="file" hidden onChange={upload} />
      </div>
      {files.length === 0 && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 40, border: '2px dashed #e2e8f0', borderRadius: 12, fontSize: 13 }}>No files uploaded yet. Upload interview templates, evaluation forms, or onboarding docs.</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {files.map(f => (
          <div key={f.id} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 16px', background: catColor[f.category], borderRadius: 10 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: '#1e293b' }}>{f.name}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>{catLabels[f.category]} • {f.size} • {f.uploaded}</div>
            </div>
            <button onClick={() => del(f.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: 4 }}><MdDelete size={16} /></button>
          </div>
        ))}
      </div>
    </Section>
  );
}

function AIPrefsSection() {
  const [prefs, setPrefs] = useState({ rankStrictness: 70, autoShortlistThreshold: 75, monitoringSensitivity: 'medium', recommendationMode: 'balanced' });
  return (
    <Section icon={<MdPsychology />} title="AI Intelligence Preferences" subtitle="Fine-tune how the AI ranks, recommends, and evaluates candidates" accent="#4f46e5">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <Field label={`Ranking Strictness — ${prefs.rankStrictness}%`} hint="Higher = only top-tier candidates score well">
          <input type="range" min={40} max={95} value={prefs.rankStrictness} onChange={e => setPrefs(p => ({ ...p, rankStrictness: +e.target.value }))} style={{ width: '100%', accentColor: '#6366f1' }} />
        </Field>
        <Field label={`Auto-Shortlist Threshold — ${prefs.autoShortlistThreshold}%`} hint="Candidates above this score are auto-shortlisted">
          <input type="range" min={50} max={95} value={prefs.autoShortlistThreshold} onChange={e => setPrefs(p => ({ ...p, autoShortlistThreshold: +e.target.value }))} style={{ width: '100%', accentColor: '#10b981' }} />
        </Field>
        <Field label="Interview Monitoring Sensitivity" hint="How aggressively AI flags suspicious behavior">
          <Select value={prefs.monitoringSensitivity} onChange={e => setPrefs(p => ({ ...p, monitoringSensitivity: e.target.value }))}>
            <option value="low">Low — flag only obvious violations</option>
            <option value="medium">Medium — balanced detection</option>
            <option value="high">High — flag all anomalies</option>
          </Select>
        </Field>
        <Field label="AI Recommendation Mode" hint="How aggressive AI hiring suggestions are">
          <Select value={prefs.recommendationMode} onChange={e => setPrefs(p => ({ ...p, recommendationMode: e.target.value }))}>
            <option value="conservative">Conservative — high confidence only</option>
            <option value="balanced">Balanced — standard mode</option>
            <option value="aggressive">Aggressive — maximize candidate flow</option>
          </Select>
        </Field>
      </div>
      <Btn onClick={() => toast.success('AI preferences saved')}><MdSave /> Save AI Settings</Btn>
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
      <Accordion title="⚙️ SMTP Configuration (click to expand)">
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

// ── Navigation tabs ─────────────────────────────────────────────────────────
const TABS = [
  { id: 'account', label: 'Account', icon: <MdPerson /> },
  { id: 'notifications', label: 'Notifications', icon: <MdNotifications /> },
  { id: 'notes', label: 'Workspace', icon: <MdStickyNote2 /> },
  { id: 'vault', label: 'Vault', icon: <MdFolder /> },
  { id: 'ai', label: 'AI Settings', icon: <MdPsychology /> },
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
            <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1e293b' }}>HR Workspace Settings</h1>
            <p style={{ color: '#64748b', fontSize: 13 }}>Manage your recruiter profile, preferences, notes, and platform intelligence.</p>
          </div>

          {/* Tab bar */}
          <div style={{ display: 'flex', gap: 6, marginBottom: 28, background: '#f8fafc', padding: 6, borderRadius: 14, border: '1px solid #e2e8f0', flexWrap: 'wrap' }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setActiveTab(t.id)} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 10, border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 13, transition: 'all 0.15s', background: activeTab === t.id ? '#6366f1' : 'transparent', color: activeTab === t.id ? '#fff' : '#64748b' }}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          {/* Content */}
          {activeTab === 'account'       && <AccountSection />}
          {activeTab === 'notifications' && <NotificationsSection />}
          {activeTab === 'notes'         && <NotesSection />}
          {activeTab === 'vault'         && <VaultSection />}
          {activeTab === 'ai'            && <AIPrefsSection />}
          {activeTab === 'email'         && <EmailSection />}
        </div>
      </main>
    </div>
  );
}
