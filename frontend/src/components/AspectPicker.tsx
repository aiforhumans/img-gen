import React from 'react';
import { Square, RectangleVertical, RectangleHorizontal, Smartphone, Film, Sliders } from 'lucide-react';
import { AspectRatio } from '../types';

interface AspectPickerProps {
  aspectRatio: AspectRatio;
  setAspectRatio: (ar: AspectRatio) => void;
  width: number;
  height: number;
  setWidth: (w: number) => void;
  setHeight: (h: number) => void;
}

export const AspectPicker: React.FC<AspectPickerProps> = ({
  aspectRatio,
  setAspectRatio,
  width,
  height,
  setWidth,
  setHeight
}) => {
  const options: { id: AspectRatio; label: string; ratio: string; icon: any; defW: number; defH: number }[] = [
    { id: '1:1', label: 'Square', ratio: '1:1', icon: Square, defW: 1024, defH: 1024 },
    { id: '3:4', label: 'Portrait', ratio: '3:4', icon: RectangleVertical, defW: 896, defH: 1152 },
    { id: '16:9', label: 'Landscape', ratio: '16:9', icon: RectangleHorizontal, defW: 1280, defH: 720 },
    { id: '9:16', label: 'Phone', ratio: '9:16', icon: Smartphone, defW: 720, defH: 1280 },
    { id: '21:9', label: 'Cinema', ratio: '21:9', icon: Film, defW: 1344, defH: 576 },
    { id: 'custom', label: 'Custom', ratio: 'custom', icon: Sliders, defW: width, defH: height },
  ];

  const handleSelect = (opt: typeof options[0]) => {
    setAspectRatio(opt.id);
    if (opt.id !== 'custom') {
      setWidth(opt.defW);
      setHeight(opt.defH);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Aspect Ratio
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '0.5rem' }}>
        {options.map((opt) => {
          const Icon = opt.icon;
          const isSelected = aspectRatio === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => handleSelect(opt)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.625rem 0.5rem',
                borderRadius: 'var(--radius-md)',
                background: isSelected ? 'var(--bg-surface-elevated)' : 'var(--bg-input)',
                border: isSelected ? '1px solid var(--primary-light)' : '1px solid var(--border-subtle)',
                color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <Icon size={18} color={isSelected ? 'var(--primary-light)' : 'currentColor'} />
              <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{opt.label}</span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {opt.id === 'custom' ? `${width}x${height}` : opt.ratio}
              </span>
            </button>
          );
        })}
      </div>

      {aspectRatio === 'custom' && (
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Width (px)</label>
            <input
              type="number"
              className="input-text"
              style={{ width: '100%', marginTop: 2 }}
              value={width}
              step={64}
              min={256}
              max={2048}
              onChange={(e) => setWidth(parseInt(e.target.value) || 1024)}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Height (px)</label>
            <input
              type="number"
              className="input-text"
              style={{ width: '100%', marginTop: 2 }}
              value={height}
              step={64}
              min={256}
              max={2048}
              onChange={(e) => setHeight(parseInt(e.target.value) || 1024)}
            />
          </div>
        </div>
      )}
    </div>
  );
};
