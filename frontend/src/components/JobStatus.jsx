import React, { useState } from 'react';
import ProgressIndicator from './ProgressIndicator';
import { Clock, AlertTriangle, AlertCircle, Copy, Check } from 'lucide-react';

export default function JobStatus({ job }) {
  const [copiedId, setCopiedId] = useState(false);

  if (!job) return null;

  const { job_id, status, created_at, completed_at, error } = job;

  const handleCopyId = () => {
    navigator.clipboard.writeText(job_id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'queued':
        return <span className="status-indicator status-queued">Queued</span>;
      case 'processing':
        return (
          <span className="status-indicator status-processing">
            <span className="spinner" style={{ width: '12px', height: '12px' }}></span>
            Processing
          </span>
        );
      case 'completed':
        return <span className="status-indicator status-completed">Completed</span>;
      case 'failed':
        return <span className="status-indicator status-failed">Failed</span>;
      default:
        return <span className="status-indicator status-queued">{status}</span>;
    }
  };

  return (
    <div className="glass-card status-card">
      <div className="status-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Active Job:</span>
          <div
            onClick={handleCopyId}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              background: 'rgba(255,255,255,0.04)',
              padding: '0.2rem 0.5rem',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              border: '1px solid var(--border-color)',
            }}
            title="Click to copy Job ID"
          >
            <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#93c5fd' }}>
              {job_id}
            </code>
            {copiedId ? <Check size={12} color="#10b981" /> : <Copy size={12} color="var(--text-muted)" />}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {created_at && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
              <Clock size={13} /> {new Date(created_at).toLocaleTimeString()}
            </span>
          )}
          <div>{getStatusBadge()}</div>
        </div>
      </div>

      <ProgressIndicator status={status} startedAt={job.started_at} />

      {error && (
        <div className="alert-box alert-error">
          <AlertCircle size={20} style={{ flexShrink: 0 }} />
          <div>
            <strong>Processing Error:</strong> {error}
          </div>
        </div>
      )}
    </div>
  );
}
