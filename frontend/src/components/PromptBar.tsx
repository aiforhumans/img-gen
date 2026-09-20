import React, { useState } from 'react';
import {
  Sparkles, XCircle, ChevronDown, ChevronUp, Shuffle
} from 'lucide-react';
import { StylePreset } from '../types';

interface PromptBarProps {
  prompt: string;
  setPrompt: (p: string) => void;
  negativePrompt: string;
  setNegativePrompt: (np: string) => void;
  selectedStyle?: string;
  setSelectedStyle: (s: string) => void;
  styles: StylePreset[];
  isGenerating: boolean;
  onGenerate: () => void;
  onCancel: () => void;
  currentStep?: number;
  totalSteps?: number;
  steps?: number;
  setSteps?: (s: number) => void;
}

const SAMPLE_PROMPTS = [
  "A cinematic photograph of an abandoned 1980s arcade at night, wet floor, neon signs saying ARCADE 84.",
  "Professional portrait photograph of a woman in a studio, 85mm lens, soft Rembrandt lighting, ultra detailed skin texture.",
  "Poster saying GRAND OPENING with futuristic typography, bold neon gradient, award winning graphic design.",
  "Fantasy landscape with massive floating cities, cascading waterfalls into clouds, majestic golden hour sky, epic scale.",
  "Editorial fashion photography in a minimalist brutalist courtyard, striking model pose, high contrast monochrome."
];

export const PromptBar: React.FC<PromptBarProps> = ({
  prompt,
  setPrompt,
  negativePrompt,
  setNegativePrompt,
  selectedStyle,
  setSelectedStyle,
  styles,
  isGenerating,
  onGenerate,
  onCancel,
  currentStep = 0,
  totalSteps = 8,
  steps = 8,
  setSteps
}) => {
  const [showNegative, setShowNegative] = useState(false);

  const handleRandomSample = () => {
    const pick = SAMPLE_PROMPTS[Math.floor(Math.random() * SAMPLE_PROMPTS.length)];
    setPrompt(pick);
  };

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      {/* Top Controls: Style Presets & Random Idea */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
        marginBottom: '0.85rem'
      }}>
        {/* Style Preset Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
            Style Preset:
          </span>
          <select
            className="select-input"
            value={selectedStyle || 'none'}
            onChange={(e) => setSelectedStyle(e.target.value === 'none' ? '' : e.target.value)}
            style={{ minWidth: 170 }}
          >
            <option value="none">None (Raw Photorealism)</option>
            {styles.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {/* Quick Sample / Inspiration */}
        <button
          onClick={handleRandomSample}
          className="btn btn-secondary"
          style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
          title="Load sample prompt"
        >
          <Shuffle size={14} />
          <span>Random Idea</span>
        </button>
      </div>

      {/* Turbo Step Preset Selector Strip */}
      {setSteps && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '0.75rem',
          padding: '0.4rem 0.75rem',
          background: 'rgba(255, 255, 255, 0.02)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid rgba(255, 255, 255, 0.04)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
              TURBO STEPS:
            </span>
            <div className="pill-group" style={{ background: 'transparent' }}>
              {[
                { s: 2, label: '⚡ 2-Step (0.8s)' },
                { s: 4, label: '⚡ 4-Step (1.5s)' },
                { s: 8, label: '⚡ 8-Step (2.5s)' }
              ].map((item) => (
                <button
                  key={item.s}
                  type="button"
                  className={`pill-btn ${steps === item.s ? 'active' : ''}`}
                  onClick={() => setSteps(item.s)}
                  style={{
                    fontSize: '0.725rem',
                    padding: '0.2rem 0.6rem',
                    background: steps === item.s ? 'var(--primary)' : 'rgba(255,255,255,0.05)'
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Juggernaut-XL SDXL-Lightning
          </span>
        </div>
      )}

      {/* Main Prompt Input Area */}
      <div style={{ position: 'relative', marginBottom: '1rem' }}>
        <textarea
          className="input-textarea"
          rows={3}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe whatever you want to see... (e.g. 'A cinematic photograph of an abandoned 1980s arcade at night, neon signs saying ARCADE 84.')"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              e.preventDefault();
              if (!isGenerating && prompt.trim()) onGenerate();
            }
          }}
        />
      </div>

      {/* Negative Prompt Drawer */}
      {showNegative && (
        <div style={{ marginBottom: '1rem', animation: 'fadeIn 0.2s ease' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: 600 }}>
            Negative Concepts to Exclude:
          </div>
          <input
            type="text"
            className="input-text"
            style={{ width: '100%' }}
            value={negativePrompt}
            onChange={(e) => setNegativePrompt(e.target.value)}
            placeholder="blurry, distorted, oversaturated, bad anatomy, deformed eyes..."
          />
        </div>
      )}

      {/* Bottom Action Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem'
      }}>
        <button
          onClick={() => setShowNegative(!showNegative)}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-secondary)',
            fontSize: '0.8rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            cursor: 'pointer'
          }}
        >
          {showNegative ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          <span>{showNegative ? 'Hide Negative Prompt' : 'Add Negative Prompt'}</span>
        </button>

        {/* Generate / Cancel Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {isGenerating && (
            <button
              onClick={onCancel}
              className="btn btn-danger"
              style={{ padding: '0.75rem 1.25rem' }}
            >
              <XCircle size={18} />
              <span>Cancel</span>
            </button>
          )}

          <button
            onClick={onGenerate}
            disabled={isGenerating || !prompt.trim()}
            className="btn-generate"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.625rem',
              cursor: isGenerating || !prompt.trim() ? 'not-allowed' : 'pointer'
            }}
          >
            <Sparkles size={20} />
            <span>
              {isGenerating
                ? `GENERATING (${currentStep}/${totalSteps})`
                : 'GENERATE'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};
