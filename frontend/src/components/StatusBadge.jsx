const STATUS_MAP = {
  'pending':            { cls: 'badge-applied',     label: 'Pending' },
  'shortlisted':        { cls: 'badge-shortlisted',  label: 'Shortlisted' },
  'rejected':           { cls: 'badge-rejected',     label: 'Rejected' },
  'interview_scheduled':{ cls: 'badge-interview',    label: 'Interview' },
  'selected':           { cls: 'badge-selected',     label: 'Selected' },
};

export default function StatusBadge({ status }) {
  const cfg = STATUS_MAP[status] || STATUS_MAP['pending'];
  return <span className={`badge ${cfg.cls}`}>{cfg.label}</span>;
}
