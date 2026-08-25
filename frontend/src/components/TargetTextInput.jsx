import React, { useState } from 'react';
import { Mic, X, Sliders, ChevronDown, ChevronUp, Cpu, Gauge } from 'lucide-react';

export default function TargetTextInput({
  value,
  onChange,
  disabled,
  modelSize,
  onChangeModelSize,
  threshold,
  onChangeThreshold,
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;

  return (
    <div className="form-group">
      <div className="form-label">
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Mic size={16} color="var(--accent-cyan)" />
          Target Spoken Dialogue Phrase
        </span>
        <span className="label-hint">
          {wordCount} word{wordCount !== 1 ? 's' : ''} detected
        </span>
      </div>

      <div className="input-wrapper">
        <div className="input-icon">
          <Mic size={18} />
        </div>
        <input
          type="text"
          className="form-input"
          placeholder="e.g. 'My mind rebells its stagnation' or 'elementary my dear watson'"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          required
        />
        {value && (
          <button
            type="button"
            className="input-action-btn"
            onClick={() => onChange('')}
            disabled={disabled}
            title="Clear phrase"
          >
            <X size={13} />
            Clear
          </button>
        )}
      </div>

      {/* Advanced Settings Toggle */}
      <div>
        <button
          type="button"
          className="advanced-toggle"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          <Sliders size={14} />
          <span>Advanced ASR & Matching Parameters</span>
          {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {showAdvanced && (
          <div className="advanced-panel">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Cpu size={14} color="var(--accent-purple)" />
                Whisper Model Engine:
              </label>
              <select
                className="select-input"
                value={modelSize}
                onChange={(e) => onChangeModelSize(e.target.value)}
                disabled={disabled}
              >
                <option value="tiny">Tiny (Fastest, low VRAM)</option>
                <option value="base">Base (Balanced - Recommended)</option>
                <option value="small">Small (High Accuracy)</option>
                <option value="medium">Medium (Very High Accuracy)</option>
                <option value="large">Large (Maximum Accuracy)</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Gauge size={14} color="var(--accent-emerald)" />
                  Fuzzy Match Threshold:
                </label>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                  {Math.round(threshold * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0.50"
                max="1.00"
                step="0.05"
                className="range-slider"
                value={threshold}
                onChange={(e) => onChangeThreshold(parseFloat(e.target.value))}
                disabled={disabled}
              />
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                Lower threshold (e.g. 70-80%) captures near-matches; higher (90%+) ensures strict accuracy.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
