import React, { useState } from 'react';
import { resolveImageUrl } from '../api';
import { Maximize2, Copy, Check, Download, Sparkles, Clock, Film, Quote } from 'lucide-react';

export default function FrameCard({ match, isPrimary, index, onOpenLightbox, fps }) {
  const [copied, setCopied] = useState(false);

  const {
    instance = index + 1,
    timestamp,
    timestamp_seconds,
    frame_number,
    text,
    confidence,
    image_url,
    image_path,
  } = match;

  const resolvedSrc = image_url || resolveImageUrl(image_path);
  const confidencePercent = Math.round((confidence || 0) * 100);

  const getConfidenceClass = (conf) => {
    if (conf >= 0.9) return 'confidence-high';
    if (conf >= 0.75) return 'confidence-medium';
    return 'confidence-low';
  };

  const copyTimestamp = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(timestamp);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const fallbackFrameCalc =
    frame_number !== undefined && frame_number !== null
      ? frame_number
      : timestamp_seconds && fps
      ? Math.round(timestamp_seconds * fps)
      : '-';

  return (
    <div className="frame-card">
      {/* Header */}
      <div className="frame-card-header">
        <span className={`instance-badge ${isPrimary ? 'primary' : ''}`}>
          {isPrimary ? (
            <>
              <Sparkles size={13} />
              Occurrence #{instance} (Primary Match)
            </>
          ) : (
            <>Occurrence #{instance}</>
          )}
        </span>

        <span
          className={`metric-pill-value ${getConfidenceClass(confidence)}`}
          style={{ fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
        >
          {confidencePercent}% Match
        </span>
      </div>

      {/* Frame Image with Zoom Preview */}
      <div className="frame-image-wrapper" onClick={() => onOpenLightbox(index)}>
        {resolvedSrc ? (
          <img
            src={resolvedSrc}
            alt={`Frame at ${timestamp} for: ${text}`}
            className="frame-img"
            loading="lazy"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        ) : (
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.85rem',
            }}
          >
            No frame image generated
          </div>
        )}

        <div className="frame-overlay-info">
          <span className="time-badge">
            <Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />
            {timestamp}
          </span>
          <span className="zoom-hint">
            <Maximize2 size={14} />
          </span>
        </div>
      </div>

      {/* Body Details */}
      <div className="frame-card-body">
        {/* Metric Pills */}
        <div className="metric-row">
          <div className="metric-pill">
            <span className="metric-pill-label">
              <Clock size={11} style={{ display: 'inline', marginRight: '3px' }} />
              Timestamp
            </span>
            <span className="metric-pill-value" style={{ color: 'var(--accent-cyan)' }}>
              {timestamp}
            </span>
            {timestamp_seconds !== undefined && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                ({Number(timestamp_seconds).toFixed(3)}s)
              </span>
            )}
          </div>

          <div className="metric-pill">
            <span className="metric-pill-label">
              <Film size={11} style={{ display: 'inline', marginRight: '3px' }} />
              Frame Index
            </span>
            <span className="metric-pill-value">#{fallbackFrameCalc}</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {fps ? `@ ${fps.toFixed(2)} fps` : 'Exact OpenCV seek'}
            </span>
          </div>
        </div>

        {/* Transcribed Quote */}
        {text && (
          <div className="transcript-quote-box">
            <Quote size={12} color="var(--accent-primary)" style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            "{text}"
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="frame-card-actions">
        <button
          type="button"
          className="btn-secondary"
          onClick={copyTimestamp}
          style={{ flex: 1, justifyContent: 'center' }}
          title="Copy timestamp to clipboard"
        >
          {copied ? <Check size={14} color="var(--accent-emerald)" /> : <Copy size={14} />}
          {copied ? 'Copied!' : 'Copy Timestamp'}
        </button>

        {resolvedSrc && (
          <a
            href={resolvedSrc}
            download={`frame_instance_${instance}_${(timestamp || 'match').replace(/[:.]/g, '_')}.png`}
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
            style={{ justifyContent: 'center' }}
            title="Download PNG snapshot"
            onClick={(e) => e.stopPropagation()}
          >
            <Download size={14} />
            PNG
          </a>
        )}
      </div>
    </div>
  );
}
