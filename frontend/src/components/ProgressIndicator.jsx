import React from 'react';
import { Music, AudioWaveform, FileText, Film, Camera, CheckCircle2 } from 'lucide-react';

const STAGES = [
  { id: 'downloading_audio', label: '1. Audio Stream', desc: 'yt-dlp extract / cache', icon: Music },
  { id: 'converting_audio', label: '2. 16kHz WAV', desc: 'PCM normalization', icon: AudioWaveform },
  { id: 'transcribing_and_matching', label: '3. Whisper ASR', desc: 'Word timestamps & search', icon: FileText },
  { id: 'downloading_video', label: '4. Video Stream', desc: 'MP4 visual frames', icon: Film },
  { id: 'extracting_frame', label: '5. Frame Capture', desc: 'OpenCV millisecond seek', icon: Camera },
];

export default function ProgressIndicator({ status, startedAt }) {
  const isFinished = status === 'completed';
  const isFailed = status === 'failed';
  const isProcessing = status === 'processing';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Pipeline State:{' '}
          <strong style={{ color: isFinished ? 'var(--accent-emerald)' : isFailed ? 'var(--accent-rose)' : 'var(--text-primary)' }}>
            {status ? status.toUpperCase() : 'QUEUED'}
          </strong>
        </span>
        {isProcessing && (
          <span style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
            <span className="spinner" style={{ width: '14px', height: '14px' }}></span>
            Executing ML Pipeline...
          </span>
        )}
        {isFinished && (
          <span style={{ fontSize: '0.8rem', color: 'var(--accent-emerald)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
            <CheckCircle2 size={16} /> Completed
          </span>
        )}
      </div>

      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{
            width: isFinished ? '100%' : isProcessing ? '65%' : isFailed ? '100%' : '15%',
            background: isFailed
              ? 'linear-gradient(90deg, var(--accent-rose), #cc241d)'
              : isFinished
              ? 'linear-gradient(90deg, var(--accent-emerald), var(--accent-cyan))'
              : 'linear-gradient(90deg, var(--accent-primary), var(--accent-amber))',
          }}
        ></div>
      </div>

      <div className="timeline-steps">
        {STAGES.map((s, idx) => {
          const Icon = s.icon;
          const isActive = isProcessing;
          const isDone = isFinished;
          return (
            <div
              key={s.id}
              className={`step-box ${isDone ? 'completed' : isActive ? 'active' : ''}`}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.2rem' }}>
                <Icon size={14} color={isDone ? 'var(--accent-emerald)' : isActive ? 'var(--accent-cyan)' : 'var(--text-muted)'} />
                <span className="step-title">{s.label}</span>
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{s.desc}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
