import React from 'react';
import { ArrowLeft, ArrowRight, ArrowUp, ArrowDown, Expand, Maximize2 } from 'lucide-react';

interface OutpaintControlsProps {
  expandLeft: number;
  setExpandLeft: (v: number) => void;
  expandRight: number;
  setExpandRight: (v: number) => void;
  expandTop: number;
  setExpandTop: (v: number) => void;
  expandBottom: number;
  setExpandBottom: (v: number) => void;
  onApplyPreset: (presetKey: string) => void;
}

export const OutpaintControls: React.FC<OutpaintControlsProps> = ({
  expandLeft,
  setExpandLeft,
  expandRight,
  setExpandRight,
  expandTop,
  setExpandTop,
  expandBottom,
  setExpandBottom,
  onApplyPreset
}) => {
  const presets = [
    { id: 'square_to_portrait', label: 'Square → Portrait (3:4)' },
    { id: 'square_to_landscape', label: 'Square → Landscape (16:9)' },
    { id: 'landscape_to_phone', label: 'Landscape → Phone (9:16)' },
    { id: 'portrait_to_cinema', label: 'Portrait → Cinema (21:9)' },
  ];

  return (
    <div className="glass-panel" style={{ padding: '1rem' }}>
      <div style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Maximize2 size={16} color="var(--primary-light)" />
        <span>Canvas Extension & Aspect Ratio Presets</span>
      </div>

      {/* Conversion Presets */}
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem', fontWeight: 600 }}>
          Quick Aspect-Ratio Expansion:
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.5rem' }}>
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => onApplyPreset(p.id)}
              className="btn btn-secondary"
              style={{ fontSize: '0.8rem', padding: '0.45rem 0.75rem', textAlign: 'left' }}
            >
              <Expand size={14} />
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Directional Sliders */}
      <div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 600 }}>
          Directional Extension (Pixels):
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
          {/* Top */}
          <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <ArrowUp size={13} /> Top:
              </span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{expandTop}px</span>
            </div>
            <input
              type="range"
              min={0}
              max={512}
              step={32}
              value={expandTop}
              onChange={(e) => setExpandTop(parseInt(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--primary)', marginTop: 4 }}
            />
          </div>

          {/* Bottom */}
          <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <ArrowDown size={13} /> Bottom:
              </span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{expandBottom}px</span>
            </div>
            <input
              type="range"
              min={0}
              max={512}
              step={32}
              value={expandBottom}
              onChange={(e) => setExpandBottom(parseInt(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--primary)', marginTop: 4 }}
            />
          </div>

          {/* Left */}
          <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <ArrowLeft size={13} /> Left:
              </span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{expandLeft}px</span>
            </div>
            <input
              type="range"
              min={0}
              max={512}
              step={32}
              value={expandLeft}
              onChange={(e) => setExpandLeft(parseInt(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--primary)', marginTop: 4 }}
            />
          </div>

          {/* Right */}
          <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <ArrowRight size={13} /> Right:
              </span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{expandRight}px</span>
            </div>
            <input
              type="range"
              min={0}
              max={512}
              step={32}
              value={expandRight}
              onChange={(e) => setExpandRight(parseInt(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--primary)', marginTop: 4 }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
