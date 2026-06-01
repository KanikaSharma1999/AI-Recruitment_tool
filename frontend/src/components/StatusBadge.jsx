const STATUS_MAP = {
  'applied':            { cls: 'badge-applied',     label: 'Applied' },
  'screening':          { cls: 'badge-screening',   label: 'Screening' },
  'shortlisted':        { cls: 'badge-shortlisted', label: 'Shortlisted' },
  'interview_scheduled':{ cls: 'badge-interview',   label: 'Interview Scheduled' },
  'interview_completed':{ cls: 'badge-completed',   label: 'Interview Completed' },
  'offered':            { cls: 'badge-selected',    label: 'Offered' },
  'hired':              { cls: 'badge-selected',    label: 'Hired' },
  'rejected':           { cls: 'badge-rejected',    label: 'Rejected' },
  'missed':             { cls: 'badge-rejected',    label: 'Missed' },
  'pending':            { cls: 'badge-applied',     label: 'Applied' },
};

export default function StatusBadge({ status, interview }) {
  let displayStatus = status;
  if (interview?.status === 'missed') {
    displayStatus = 'missed';
  } else if (status === 'interview_scheduled' && interview && interview.date && interview.time) {
    const scheduledDateTime = new Date(`${interview.date}T${interview.time}:00`);
    const cutOffTime = new Date(scheduledDateTime.getTime() + 15 * 60 * 1000);
    if (new Date() > cutOffTime) {
      displayStatus = 'missed';
    }
  }
  const cfg = STATUS_MAP[displayStatus] || STATUS_MAP['applied'];
  return <span className={`badge ${cfg.cls}`}>{cfg.label}</span>;
}
