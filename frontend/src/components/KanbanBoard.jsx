import React, { useState } from 'react';
import {
  DndContext,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useNavigate } from 'react-router-dom';

const COLUMNS = [
  { id: 'applied', title: 'Applied' },
  { id: 'screening', title: 'Screening' },
  { id: 'shortlisted', title: 'Shortlisted' },
  { id: 'interview_scheduled', title: 'Interview Scheduled' },
  { id: 'interviewed', title: 'Interviewed' },
  { id: 'selected', title: 'Selected' },
  { id: 'rejected', title: 'Rejected' },
  { id: 'on_hold', title: 'On Hold' }
];

function SortableItem({ candidate, onClick }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: candidate.id, data: { ...candidate } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    padding: '12px',
    margin: '0 0 8px 0',
    backgroundColor: '#fff',
    borderRadius: '8px',
    boxShadow: isDragging ? '0 5px 15px rgba(0,0,0,0.15)' : '0 1px 3px rgba(0,0,0,0.1)',
    cursor: 'grab',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    border: '1px solid #e2e8f0',
    position: 'relative'
  };

  const safeScore = (v) => Math.min(100, Math.max(0, Math.round(Number(v || 0))));
  const score = safeScore(candidate.score);

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} onClick={() => onClick(candidate.id)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#1e293b' }}>{candidate.name}</h4>
        <span style={{ 
          fontSize: '12px', 
          fontWeight: 700,
          color: score >= 70 ? '#059669' : score >= 45 ? '#d97706' : '#dc2626',
          backgroundColor: score >= 70 ? '#d1fae5' : score >= 45 ? '#fef3c7' : '#fee2e2',
          padding: '2px 6px',
          borderRadius: '4px'
        }}>
          {score}%
        </span>
      </div>
      <span style={{ fontSize: '11px', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{candidate.email}</span>
      {candidate.hiring_summary?.recommendation && (
        <span style={{ fontSize: '10px', color: '#475569', marginTop: '4px', fontStyle: 'italic' }}>
          {candidate.hiring_summary.recommendation}
        </span>
      )}
    </div>
  );
}

function Column({ id, title, candidates, onCardClick }) {
  const { setNodeRef } = useSortable({
    id: id,
    data: { type: 'Column', columnId: id }
  });

  return (
    <div
      ref={setNodeRef}
      style={{
        flex: '0 0 280px',
        backgroundColor: '#f8fafc',
        borderRadius: '8px',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: 'calc(100vh - 200px)',
        border: '1px solid #e2e8f0'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{title}</h3>
        <span style={{ fontSize: '12px', backgroundColor: '#e2e8f0', color: '#475569', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
          {candidates.length}
        </span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <SortableContext items={candidates.map(c => c.id)} strategy={verticalListSortingStrategy}>
          {candidates.map((c) => (
            <SortableItem key={c.id} candidate={c} onClick={onCardClick} />
          ))}
        </SortableContext>
      </div>
    </div>
  );
}

export default function KanbanBoard({ candidates, onStatusChange }) {
  const navigate = useNavigate();
  
  // Initialize local state for optimistic updates
  const [localCandidates, setLocalCandidates] = useState(candidates);
  
  // Sync with props when candidates change from parent
  React.useEffect(() => {
    setLocalCandidates(candidates);
  }, [candidates]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over) return;

    const candidateId = active.id;
    const overId = over.id;

    // Find the candidate
    const activeCandidate = localCandidates.find(c => c.id === candidateId);
    if (!activeCandidate) return;

    // Determine target column
    let targetStatus = null;
    const overIsColumn = COLUMNS.some(col => col.id === overId);
    
    if (overIsColumn) {
      targetStatus = overId;
    } else {
      const overCandidate = localCandidates.find(c => c.id === overId);
      if (overCandidate) {
        targetStatus = overCandidate.status || 'applied'; // Default to applied if empty
      }
    }

    if (targetStatus && activeCandidate.status !== targetStatus) {
      // Confirm modal (simplified browser confirm for now, as requested "confirmation modal")
      if (window.confirm(`Move ${activeCandidate.name} to ${COLUMNS.find(c => c.id === targetStatus).title}?`)) {
        // Optimistic update
        setLocalCandidates(prev => 
          prev.map(c => c.id === candidateId ? { ...c, status: targetStatus } : c)
        );
        onStatusChange(candidateId, targetStatus);
      }
    }
  };

  const handleCardClick = (id) => {
    navigate(`/candidates/${id}`);
  };

  return (
    <div style={{ display: 'flex', gap: '16px', overflowX: 'auto', paddingBottom: '16px', height: '100%' }}>
      <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={handleDragEnd}>
        {COLUMNS.map((col) => {
          const colCandidates = localCandidates.filter(c => (c.status || 'applied') === col.id);
          return (
            <Column
              key={col.id}
              id={col.id}
              title={col.title}
              candidates={colCandidates}
              onCardClick={handleCardClick}
            />
          );
        })}
      </DndContext>
    </div>
  );
}
