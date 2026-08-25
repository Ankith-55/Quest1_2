import React, { useState, useEffect } from 'react';
import FrameCard from './FrameCard';
import { resolveImageUrl } from '../api';
import {
  Layers,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  X,
  AlertTriangle,
  Download,
  Copy,
  Check,
  Film,
  Search,
} from 'lucide-react';

export default function ResultDisplay({ result, targetText }) {
  const [lightboxIndex, setLightboxIndex] = useState(null);
  const [modalCopied, setModalCopied] = useState(false);

  if (!result) return null;

  const {
    status,
    timestamp,
    timestamp_seconds,
    frame_number,
    text,
    confidence,
    image_url,
    image_path,
    matches = [],
    candidates = [],
    fps = 30.0,
  } = result;

  // Compile list of matches to display
  let displayMatches = [...matches];

  // If matches array is empty but top-level match exists, construct array
  if (displayMatches.length === 0 && (timestamp || image_url || image_path)) {
    displayMatches.push({
      instance: 1,
      timestamp,
      timestamp_seconds,
      frame_number,
      text: text || targetText,
      confidence: confidence || 1.0,
      image_url,
      image_path,
    });
  }

  // Handle keyboard navigation for lightbox modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (lightboxIndex === null) return;
      if (e.key === 'Escape') {
        setLightboxIndex(null);
      } else if (e.key === 'ArrowRight') {
        setLightboxIndex((prev) => (prev + 1) % displayMatches.length);
      } else if (e.key === 'ArrowLeft') {
        setLightboxIndex((prev) => (prev - 1 + displayMatches.length) % displayMatches.length);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxIndex, displayMatches.length]);

  const isFound = status === 'found' || displayMatches.length > 0;
  const activeModalMatch = lightboxIndex !== null ? displayMatches[lightboxIndex] : null;
  const activeModalImage = activeModalMatch
    ? activeModalMatch.image_url || resolveImageUrl(activeModalMatch.image_path)
    : '';

  const copyModalTimestamp = () => {
    if (activeModalMatch?.timestamp) {
      navigator.clipboard.writeText(activeModalMatch.timestamp);
      setModalCopied(true);
      setTimeout(() => setModalCopied(false), 2000);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Found State: Render All Matching Frames on Same Page */}
      {isFound ? (
        <section className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Header Summary */}
          <div className="matches-section-header">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem' }}>
                <span className="matches-badge-count">
                  <Layers size={14} />
                  {displayMatches.length} Spoken Occurrence{displayMatches.length !== 1 ? 's' : ''} Located
                </span>
                {fps && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    FPS: {fps.toFixed(2)}
                  </span>
                )}
              </div>

              <h2 style={{ fontSize: '1.5rem', fontFamily: 'var(--font-heading)', color: '#ffffff' }}>
                Extracted Dialogue Video Frames
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                All matching timestamps and OpenCV frame captures for:{' '}
                <strong style={{ color: '#ffffff', fontStyle: 'italic' }}>"{targetText}"</strong>
              </p>
            </div>
          </div>

          {/* All Frames Displayed in Grid on Same Page */}
          <div className="frames-grid">
            {displayMatches.map((m, idx) => (
              <FrameCard
                key={idx}
                match={m}
                index={idx}
                isPrimary={idx === 0}
                fps={fps}
                onOpenLightbox={(cardIdx) => setLightboxIndex(cardIdx)}
              />
            ))}
          </div>

          {/* Optional Candidates Alignment Table */}
          {candidates && candidates.length > 0 && (
            <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
              <h3 style={{ fontSize: '1rem', fontFamily: 'var(--font-heading)', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                Additional Audio Alignments & Confidence Ranks ({candidates.length})
              </h3>
              <div className="candidates-table-container">
                <table className="candidates-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Spoken Text in Video</th>
                      <th>Timestamp</th>
                      <th>Frame Approx.</th>
                      <th>Similarity Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((cand, idx) => (
                      <tr key={idx}>
                        <td style={{ color: 'var(--text-muted)' }}>{cand.candidate || idx + 1}</td>
                        <td style={{ color: '#ffffff', fontWeight: 500 }}>"{cand.text}"</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                          {cand.timestamp}
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          #{cand.frame_number !== undefined ? cand.frame_number : '-'}
                        </td>
                        <td>
                          <span
                            style={{
                              fontWeight: 600,
                              fontFamily: 'var(--font-mono)',
                              color:
                                cand.score >= 0.85
                                  ? 'var(--accent-emerald)'
                                  : cand.score >= 0.7
                                  ? 'var(--accent-amber)'
                                  : 'var(--text-muted)',
                            }}
                          >
                            {Math.round((cand.score || 0) * 100)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      ) : (
        /* Not Found / Below Threshold State */
        <section className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="alert-box alert-warning">
            <AlertTriangle size={24} style={{ flexShrink: 0 }} />
            <div>
              <strong style={{ fontSize: '1rem', display: 'block', marginBottom: '0.25rem' }}>
                No Exact Dialogue Match Above Similarity Threshold
              </strong>
              <span>
                The spoken phrase <em style={{ color: '#ffffff' }}>"{targetText}"</em> did not match any segment above the required threshold. Review the closest audio candidates detected below.
              </span>
            </div>
          </div>

          {candidates && candidates.length > 0 ? (
            <div>
              <h3 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-heading)', color: '#ffffff', marginBottom: '0.75rem' }}>
                Closest Audio Transcripts Detected in Video ({candidates.length})
              </h3>
              <div className="candidates-table-container">
                <table className="candidates-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Transcribed Spoken Text</th>
                      <th>Timestamp</th>
                      <th>Approx Frame</th>
                      <th>Match Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((cand, idx) => (
                      <tr key={idx}>
                        <td style={{ color: 'var(--text-muted)', fontWeight: 600 }}>#{cand.candidate || idx + 1}</td>
                        <td style={{ color: '#ffffff', fontWeight: 500 }}>"{cand.text}"</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                          {cand.timestamp}
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          #{cand.frame_number !== undefined ? cand.frame_number : '-'}
                        </td>
                        <td>
                          <span
                            style={{
                              fontWeight: 600,
                              fontFamily: 'var(--font-mono)',
                              color:
                                cand.score >= 0.75
                                  ? 'var(--accent-amber)'
                                  : 'var(--accent-rose)',
                            }}
                          >
                            {Math.round((cand.score || 0) * 100)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              No speech candidates were extracted from the audio stream.
            </p>
          )}
        </section>
      )}

      {/* Full-Screen Lightbox Modal for Frame Inspection */}
      {activeModalMatch && activeModalImage && (
        <div className="lightbox-backdrop" onClick={() => setLightboxIndex(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button
              className="lightbox-close-btn"
              onClick={() => setLightboxIndex(null)}
              title="Close (Esc)"
            >
              <X size={18} />
            </button>

            {/* Navigation buttons for multi-matches */}
            {displayMatches.length > 1 && (
              <>
                <button
                  className="lightbox-nav-btn prev"
                  onClick={() =>
                    setLightboxIndex((prev) => (prev - 1 + displayMatches.length) % displayMatches.length)
                  }
                  title="Previous Frame (Left Arrow)"
                >
                  <ChevronLeft size={24} />
                </button>
                <button
                  className="lightbox-nav-btn next"
                  onClick={() => setLightboxIndex((prev) => (prev + 1) % displayMatches.length)}
                  title="Next Frame (Right Arrow)"
                >
                  <ChevronRight size={24} />
                </button>
              </>
            )}

            <img
              src={activeModalImage}
              alt={`Full frame preview - ${activeModalMatch.timestamp}`}
              className="lightbox-img"
            />

            {/* Lightbox Footer Info & Actions */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                width: '100%',
                background: 'rgba(15, 23, 42, 0.85)',
                padding: '0.75rem 1.25rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Occurrence {lightboxIndex + 1} of {displayMatches.length} •{' '}
                </span>
                <strong style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                  {activeModalMatch.timestamp}
                </strong>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  {' '}(Frame #{activeModalMatch.frame_number})
                </span>
                <div style={{ fontSize: '0.85rem', color: '#ffffff', fontStyle: 'italic', marginTop: '0.2rem' }}>
                  "{activeModalMatch.text}"
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn-secondary" onClick={copyModalTimestamp}>
                  {modalCopied ? <Check size={14} color="var(--accent-emerald)" /> : <Copy size={14} />}
                  {modalCopied ? 'Copied Timestamp!' : 'Copy Timestamp'}
                </button>
                <a
                  href={activeModalImage}
                  download={`frame_${(activeModalMatch.timestamp || 'match').replace(/[:.]/g, '_')}.png`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary"
                >
                  <Download size={14} />
                  Download PNG
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
