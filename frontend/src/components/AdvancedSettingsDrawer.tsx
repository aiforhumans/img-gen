import React from 'react';
import { Settings2, Dices, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { ModelInfo, VRAMStrategy } from '../types';

interface AdvancedSettingsProps {
  isOpen: boolean;
  setIsOpen: (o: boolean) => void;
  models: ModelInfo[];
  selectedModel: string;
  setSelectedModel: (m: string) => void;
  steps: number;
  setSteps: (s: number) => void;
  guidance: number;
  setGuidance: (g: number) => void;
  seed: number;
  setSeed: (s: number) => void;
  sampler: string;
  setSampler: (s: string) => void;
  vramStrategy: VRAMStrategy;
  setVRAMStrategy: (s: VRAMStrategy) => void;
}

/**
 * Returns the step-aware sampler list for Z-Image Turbo (Lightning-distilled).
 * Lightning distillation has specific noise schedule requirements:
 * - 2-step: Only Euler (trailing) is safe
 * - 4-step: Euler + DPM++ 2M Karras
 * - 8-step: Full sampler menu
 */
function getStepAwareSamplers(model: string, steps: number): string[] {
  const m = model.toLowerCase();

  if (m.includes('flux')) {
    return ['Default (Recommended)', 'FlowMatch Euler'];
  }

  if (m.includes('zimage')) {
    if (steps <= 2) {
      return ['Default (Recommended)', 'Euler'];
    } else if (steps <= 4) {
      return ['Default (Recommended)', 'Euler', 'DPM++ 2M Karras'];
    } else {
      return ['Default (Recommended)', 'Euler', 'DPM++ 2M Karras', 'Euler Ancestral', 'DDIM'];
    }
  }

  if (m.includes('sdxl')) {
    return ['Default (Recommended)', 'Euler', 'Euler Ancestral', 'DPM++ 2M Karras', 'DDIM'];
  }

  if (m.includes('qwen')) {
    return ['Default (Recommended)', 'DPM++ 2M Karras', 'Euler'];
  }

  return [
    'Default (Recommended)',
    'Euler Ancestral',
    'Euler',
    'DPM++ 2M Karras',
    'FlowMatch Euler',
    'DDIM'
  ];
}

export const AdvancedSettingsDrawer: React.FC<AdvancedSettingsProps> = ({
  isOpen,
  setIsOpen,
  models,
  selectedModel,
  setSelectedModel,
  steps,
  setSteps,
  guidance,
  setGuidance,
  seed,
  setSeed,
  sampler,
  setSampler,
  vramStrategy,
  setVRAMStrategy
}) => {
  const [samplerToast, setSamplerToast] = React.useState<string | null>(null);
  const samplers = getStepAwareSamplers(selectedModel, steps);

  // When model or step count changes, validate the current sampler
  React.useEffect(() => {
    if (!samplers.includes(sampler)) {
      setSampler('Default (Recommended)');
      setSamplerToast(`Sampler adjusted for ${steps}-step mode`);
      const timer = setTimeout(() => setSamplerToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [selectedModel, steps]);

  return (
    <div className="glass-panel" style={{ padding: '1rem', marginTop: '1rem' }}>
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          userSelect: 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Settings2 size={16} color="var(--primary-light)" />
          <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Advanced Controls</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            (Manual Model, Steps, Guidance, Seed, VRAM Mode)
          </span>
        </div>
        {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </div>

      {isOpen && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1.25rem',
          marginTop: '1.25rem',
          paddingTop: '1rem',
          borderTop: '1px solid var(--border-subtle)'
        }}>
          {/* Model Override */}
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Model Backend Override:
            </label>
            <select
              className="select-input"
              style={{ width: '100%', marginTop: '0.35rem' }}
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              <option value="auto">Auto Engine (Smart Classification)</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.estimated_vram_gb} GB VRAM)
                </option>
              ))}
            </select>
          </div>

          {/* Steps Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600 }}>
              <span style={{ color: 'var(--text-muted)' }}>Inference Steps:</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{steps}</span>
            </div>
            <input
              type="range"
              min={2}
              max={50}
              step={1}
              value={steps}
              onChange={(e) => setSteps(parseInt(e.target.value))}
              style={{ width: '100%', marginTop: '0.5rem', accentColor: 'var(--primary)' }}
            />
          </div>

          {/* Guidance Scale (CFG) */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600 }}>
              <span style={{ color: 'var(--text-muted)' }}>Guidance Scale (CFG):</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{guidance.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min={1.0}
              max={15.0}
              step={0.5}
              value={guidance}
              onChange={(e) => setGuidance(parseFloat(e.target.value))}
              style={{ width: '100%', marginTop: '0.5rem', accentColor: 'var(--primary)' }}
            />
          </div>

          {/* Seed Input + Randomizer */}
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Seed (-1 for Random):
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.35rem' }}>
              <input
                type="number"
                className="input-text"
                style={{ flex: 1 }}
                value={seed}
                onChange={(e) => setSeed(parseInt(e.target.value) || -1)}
              />
              <button
                onClick={() => setSeed(-1)}
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.65rem' }}
                title="Reset to Random (-1)"
              >
                <Dices size={16} />
              </button>
            </div>
          </div>

          {/* Sampler Selector — Step-Aware */}
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Sampler / Scheduler:
            </label>
            <select
              className="select-input"
              style={{ width: '100%', marginTop: '0.35rem' }}
              value={sampler}
              onChange={(e) => setSampler(e.target.value)}
            >
              {samplers.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            {/* Step-aware sampler adjustment toast */}
            {samplerToast && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                marginTop: '0.4rem',
                padding: '0.3rem 0.6rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(245, 158, 11, 0.12)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                fontSize: '0.7rem',
                color: 'var(--accent-amber)',
                animation: 'fadeIn 0.25s ease'
              }}>
                <AlertTriangle size={12} />
                <span>{samplerToast}</span>
              </div>
            )}
          </div>

          {/* VRAM Strategy */}
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              RTX 5080 VRAM Strategy:
            </label>
            <select
              className="select-input"
              style={{ width: '100%', marginTop: '0.35rem' }}
              value={vramStrategy}
              onChange={(e) => setVRAMStrategy(e.target.value as VRAMStrategy)}
            >
              <option value="FULL_GPU">FULL_GPU (Fastest, &lt;12GB Models)</option>
              <option value="BALANCED">BALANCED (Optimal 16GB Strategy)</option>
              <option value="LOW_VRAM">LOW_VRAM (Sequential Offload)</option>
              <option value="CPU_OFFLOAD">CPU_OFFLOAD (Model Offload)</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
};
