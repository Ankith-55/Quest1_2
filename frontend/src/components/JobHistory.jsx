import React, { useState, useEffect } from 'react';
import { listJobs } from '../api';
import { History, RefreshCw, Clock, CheckCircle2, AlertCircle, ChevronRight, Layers } from 'lucide-react';

export default function JobHistory({ onSelectJob, currentJobId }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await listJobs();
      setJobs(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Failed to load job history', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [currentJobId]);

  if (!jobs || jobs.length === 0) {
    return null;
  }

  return (
    <div style={{ marginTop: '1rem' }}>
      <button
        type="button"
        className="advanced-toggle"
        onClick={() => setIsOpen(!isOpen)}
        style={{ color: 'var(--text-secondary)' }}
      >
        <History size={14} color="var(--accent-cyan)" />
        <span>Recent Searches ({jobs.length})</span>
        <ChevronRight size={14} style={{ transform: isOpen ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
      </button>

      {isOpen && (
        <div
          className="glass-card"
          style={{
            marginTop: '0.75rem',
            padding: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Recent Searches & Extracted Frames
            </span>
            <button
              type="button"
              className="btn-secondary"
              onClick={fetchHistory}
              disabled={loading}
              style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
            >
              <RefreshCw size={12} className={loading ? 'spinner' : ''} />
              Refresh
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '280px', overflowY: 'auto' }}>
            {jobs.map((j) => {
              const isSelected = j.job_id === currentJobId;
              const matchesCount = j.result?.matches?.length || (j.result?.timestamp ? 1 : 0);
              const targetPhrase = j.request?.target_text || j.result?.text || 'Dialogue Search';

              return (
                <div
                  key={j.job_id}
                  onClick={() => onSelectJob(j)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.75rem 1rem',
                    background: isSelected ? 'rgba(254, 128, 25, 0.18)' : 'rgba(235, 219, 178, 0.03)',
                    border: `1px solid ${isSelected ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      "{targetPhrase}"
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      ID: {j.job_id}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {matchesCount > 0 && (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          background: 'rgba(131, 165, 152, 0.15)',
                          color: 'var(--accent-cyan)',
                          padding: '0.2rem 0.5rem',
                          borderRadius: '9999px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                        }}
                      >
                        <Layers size={11} /> {matchesCount} frame{matchesCount !== 1 ? 's' : ''}
                      </span>
                    )}

                    {j.status === 'completed' && <CheckCircle2 size={15} color="var(--accent-emerald)" />}
                    {j.status === 'failed' && <AlertCircle size={15} color="var(--accent-rose)" />}
                    {j.status === 'processing' && <span className="spinner" style={{ width: '12px', height: '12px' }}></span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
