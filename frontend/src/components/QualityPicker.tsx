import React from 'react';
import { Zap, Scale, Crown, Flame } from 'lucide-react';
import { QualityLevel } from '../types';

interface QualityPickerProps {
  quality: QualityLevel;
  setQuality: (q: QualityLevel) => void;
  setSteps: (s: number) => void;
}

export const QualityPicker: React.FC<QualityPickerProps> = ({
  quality,
  setQuality,
  setSteps
}) => {
  const options: { id: QualityLevel; label: string; desc: string; icon: any; steps: number }[] = [
    { id: 'fast', label: 'Fast', desc: 'Prioritize speed (8-15 steps)', icon: Zap, steps: 12 },
    { id: 'balanced', label: 'Balanced', desc: 'Default optimal quality (20 steps)', icon: Scale, steps: 20 },
    { id: 'quality', label: 'Quality', desc: 'Higher detail & refinement (28 steps)', icon: Crown, steps: 28 },
    { id: 'maximum', label: 'Maximum', desc: 'Highest practical fidelity (40 steps)', icon: Flame, steps: 40 },
  ];

  const handleSelect = (opt: typeof options[0]) => {
    setQuality(opt.id);
    setSteps(opt.steps);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Quality Level
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '0.5rem' }}>
        {options.map((opt) => {
          const Icon = opt.icon;
          const isSelected = quality === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => handleSelect(opt)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.625rem 0.5rem',
                borderRadius: 'var(--radius-md)',
                background: isSelected ? 'var(--bg-surface-elevated)' : 'var(--bg-input)',
                border: isSelected ? '1px solid var(--primary-light)' : '1px solid var(--border-subtle)',
                color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <Icon size={16} color={isSelected ? 'var(--primary-light)' : 'currentColor'} />
              <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{opt.label}</span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                {opt.steps} steps
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
