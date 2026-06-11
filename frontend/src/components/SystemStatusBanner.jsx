import { useState, useEffect, useCallback } from 'react';
import API from '../api/client';
import { MdErrorOutline, MdRefresh, MdCheckCircle } from 'react-icons/md';
import toast from 'react-hot-toast';

export default function SystemStatusBanner() {
  const [status, setStatus] = useState('ok');   // 'ok' | 'degraded' | 'offline'
  const [dbError, setDbError] = useState(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);

  const checkHealth = useCallback(async (showToast = false) => {
    try {
      if (showToast) setIsRetrying(true);
      const { data } = await API.get('/health');

      // Backend now returns 'ok' or 'degraded'
      const s = data.status === 'ok' ? 'ok' : 'degraded';
      setStatus(s);

      // Extract DB offline details
      if (data.database && data.database.status !== 'connected') {
        setDbError(data.database.last_error || 'Database connection unavailable');
      } else {
        setDbError(null);
        if (showToast) toast.success('Database connected successfully!');
      }

      // Extract background sync status
      if (data.vector_store && data.vector_store.sync_status) {
        setSyncStatus(data.vector_store.sync_status);
      } else {
        setSyncStatus(null);
      }
    } catch (err) {
      // Only show 'offline' banner when the request itself fails (network error)
      setStatus('offline');
      setDbError('Backend server is unreachable — verify it is running on port 8000');
      setSyncStatus(null);
    } finally {
      setIsRetrying(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    // Poll more frequently during active vector sync
    const intervalTime = syncStatus && syncStatus.status === 'syncing' ? 3000 : 20000;
    const interval = setInterval(checkHealth, intervalTime);
    return () => clearInterval(interval);
  }, [checkHealth, syncStatus?.status]);

  const keyframesStyle = `
    @keyframes sync-pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.3; transform: scale(1.15); }
    }
    @keyframes sync-ping {
      75%, 100% { transform: scale(2.8); opacity: 0; }
    }
  `;

  // 1. Render indexing progress banner if sync is active and database is online
  if (status === 'ok' && syncStatus && syncStatus.status === 'syncing') {
    const total = syncStatus.total || 0;
    const processed = syncStatus.processed || 0;
    const percent = total > 0 ? Math.round((processed / total) * 100) : 0;

    return (
      <div style={{
        background: 'linear-gradient(135deg, #f0f7ff 0%, #e0f2fe 100%)',
        color: '#1e3a8a',
        padding: '10px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        fontSize: '13px',
        fontWeight: 500,
        borderBottom: '1px solid #bae6fd',
        position: 'sticky',
        top: 0,
        zIndex: 9999,
        boxShadow: '0 2px 8px rgba(30, 58, 138, 0.06)',
        fontFamily: 'Poppins, system-ui, sans-serif'
      }}>
        <style>{keyframesStyle}</style>

        {/* Pulsing indicator dot */}
        <span style={{
          display: 'inline-flex',
          height: '10px',
          width: '10px',
          borderRadius: '50%',
          backgroundColor: '#0284c7',
          position: 'relative',
          animation: 'sync-pulse 2s infinite ease-in-out'
        }}>
          <span style={{
            position: 'absolute',
            display: 'inline-flex',
            height: '100%',
            width: '100%',
            borderRadius: '50%',
            backgroundColor: '#38bdf8',
            opacity: 0.8,
            animation: 'sync-ping 1.2s cubic-bezier(0, 0, 0.2, 1) infinite'
          }} />
        </span>
        
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <span>
            <strong style={{ color: '#0369a1' }}>AI Resume Indexing in Progress:</strong> {processed} of {total} resumes processed ({percent}%).
          </span>
          <span style={{ 
            fontSize: '11px', 
            color: '#0284c7', 
            backgroundColor: '#e0f2fe', 
            padding: '2px 8px', 
            borderRadius: '12px', 
            border: '1px solid #bae6fd',
            fontWeight: 600,
            letterSpacing: '0.02em'
          }}>
            Platform Fully Functional
          </span>
        </div>
        
        {/* Sleek progress bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <span style={{ fontSize: '12px', color: '#0369a1', fontWeight: 600 }}>{percent}%</span>
          <div style={{
            width: '120px',
            height: '6px',
            backgroundColor: '#e0f2fe',
            borderRadius: '3px',
            overflow: 'hidden',
            border: '1px solid #bae6fd'
          }}>
            <div style={{
              width: `${percent}%`,
              height: '100%',
              backgroundColor: '#0284c7',
              borderRadius: '3px',
              transition: 'width 0.5s ease-out'
            }} />
          </div>
        </div>
      </div>
    );
  }

  // 2. Render database offline warning banner
  if (status !== 'ok') {
    return (
      <div style={{
        backgroundColor: '#fef2f2',
        color: '#991b1b',
        padding: '10px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        fontSize: '13px',
        fontWeight: 500,
        borderBottom: '1px solid #fee2e2',
        position: 'sticky',
        top: 0,
        zIndex: 9999,
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
      }}>
        <MdErrorOutline size={18} style={{ color: '#ef4444' }} />
        <div style={{ flex: 1 }}>
          <strong style={{ color: '#b91c1c' }}>
            {status === 'offline' ? 'Backend Server Offline: ' : 'Database Connection Failed: '}
          </strong>
          {status === 'offline' 
            ? 'The frontend cannot communicate with the backend. Please start the FastAPI backend server on port 8000.' 
            : 'The platform is currently in Read-Only mode. Actions like login, signup, and ranking are disabled.'}
          {dbError && (
            <div style={{ fontSize: '11px', opacity: 0.8, marginTop: '2px', fontFamily: 'monospace' }}>
              Error: {dbError}
            </div>
          )}
        </div>
        <button 
          onClick={() => checkHealth(true)}
          disabled={isRetrying}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            backgroundColor: '#fff',
            border: '1px solid #fecaca',
            borderRadius: '6px',
            color: '#991b1b',
            cursor: 'pointer',
            fontSize: '12px',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fef2f2'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#fff'}
        >
          <MdRefresh size={16} className={isRetrying ? 'animate-spin' : ''} />
          {isRetrying ? 'Checking...' : 'Retry Connection'}
        </button>
      </div>
    );
  }

  return null;
}

