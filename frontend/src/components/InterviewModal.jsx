import { useState } from 'react';
import API from '../api/client';
import toast from 'react-hot-toast';
import { MdClose, MdCalendarToday } from 'react-icons/md';

export default function InterviewModal({ candidate, onClose, onSuccess }) {
  const [form, setForm] = useState({
    date: '', time: '10:00', mode: 'online', location: '', notes: ''
  });
  const [loading, setLoading] = useState(false);

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.date) { toast.error('Please select a date'); return; }
    setLoading(true);
    try {
      await API.post(`/interviews/schedule`, { ...form, candidate_id: candidate.id, job_id: candidate.job_id });
      toast.success('Interview scheduled!');
      onSuccess();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to schedule interview');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box animate-slide">
        <div className="modal-header">
          <div className="flex-center gap-8">
            <MdCalendarToday style={{ color: 'var(--info)', fontSize: 20 }} />
            <span className="modal-title">Schedule Interview</span>
          </div>
          <button className="modal-close" onClick={onClose}><MdClose /></button>
        </div>

        <div style={{ marginBottom: 16, padding: '10px 14px', background: '#f8fafc', borderRadius: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{candidate?.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{candidate?.email}</div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Interview Date *</label>
              <input type="date" className="form-input" value={form.date}
                onChange={e => set('date', e.target.value)}
                min={new Date().toISOString().split('T')[0]} required />
            </div>
            <div className="form-group">
              <label className="form-label">Time *</label>
              <input type="time" className="form-input" value={form.time}
                onChange={e => set('time', e.target.value)} required />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Mode *</label>
            <select className="form-select" value={form.mode} onChange={e => set('mode', e.target.value)}>
              <option value="online">Online (Video Call)</option>
              <option value="offline">Offline (In-Person)</option>
              <option value="phone">Phone Interview</option>
            </select>
          </div>

          {form.mode !== 'online' && (
            <div className="form-group">
              <label className="form-label">Location / Address</label>
              <input type="text" className="form-input" placeholder="Office address"
                value={form.location} onChange={e => set('location', e.target.value)} />
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Notes (optional)</label>
            <textarea className="form-textarea" rows={2} placeholder="Any instructions..."
              value={form.notes} onChange={e => set('notes', e.target.value)} />
          </div>

          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-info" disabled={loading}>
              {loading ? <span className="spinner" /> : 'Schedule Interview'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
