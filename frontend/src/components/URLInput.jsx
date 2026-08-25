import React from 'react';
import { Link2, Clipboard, Video } from 'lucide-react';

export default function URLInput({ value, onChange, disabled, onSelectSample }) {
  const sampleLinks = [
    {
      label: '🎬 Sherlock ("My mind rebels at stagnation")',
      url: 'https://www.youtube.com/watch?v=248244667877',
      phrase: 'My mind rebels at stagnation',
    },
    {
      label: '🔍 Sherlock ("Data, data, data")',
      url: 'https://www.youtube.com/watch?v=248244667877',
      phrase: 'I can not make bricks without clay',
    },
    {
      label: '🎵 Rick Astley',
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      phrase: 'Never gonna give you up',
    },
  ];

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        onChange(text.trim());
      }
    } catch (err) {
      console.warn('Clipboard access denied or unavailable', err);
    }
  };

  return (
    <div className="form-group">
      <div className="form-label">
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Video size={16} color="var(--accent-primary)" />
          Video Source (URL or Path)
        </span>
        <span className="label-hint">YouTube, direct MP4, ok.ru, or server path</span>
      </div>

      <div className="input-wrapper">
        <div className="input-icon">
          <Link2 size={18} />
        </div>
        <input
          type="text"
          className="form-input"
          placeholder="e.g. https://www.youtube.com/watch?v=... or local video path"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          required
        />
        <button
          type="button"
          className="input-action-btn"
          onClick={handlePaste}
          disabled={disabled}
          title="Paste from clipboard"
        >
          <Clipboard size={13} />
          Paste
        </button>
      </div>

      <div className="quick-samples">
        <span className="samples-label">Quick Presets:</span>
        {sampleLinks.map((s, idx) => (
          <button
            key={idx}
            type="button"
            className="sample-chip"
            onClick={() => onSelectSample && onSelectSample(s.url, s.phrase)}
            disabled={disabled}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
