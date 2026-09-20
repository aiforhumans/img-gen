import React, { useState } from 'react';
import {
  Sparkles, Camera, Palette, Type, Edit3, Wand2, XCircle, ChevronDown, ChevronUp, Shuffle, Zap, RotateCcw
} from 'lucide-react';
import { GenerationMode, StylePreset } from '../types';
import { api } from '../services/api';

interface PromptBarProps {
  prompt: string;
  setPrompt: (p: string) => void;
  negativePrompt: string;
  setNegativePrompt: (np: string) => void;
  mode: GenerationMode;
  setMode: (m: GenerationMode) => void;
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
  mode,
  setMode,
  selectedStyle,
  setSelectedStyle,
  styles,
  isGenerating,
  onGenerate,
  onCancel,
  currentStep = 0,
  totalSteps = 20,
  steps = 8,
  setSteps
}) => {
  const [showNegative, setShowNegative] = useState(false);
  const [isPolishing, setIsPolishing] = useState(false);
  const [lastOriginalPrompt, setLastOriginalPrompt] = useState<string | null>(null);
  const [polishNotice, setPolishNotice] = useState<string | null>(null);

  const modes: { id: GenerationMode; label: string; icon: any }[] = [
    { id: 'auto', label: 'Auto Engine', icon: Wand2 },
    { id: 'photo', label: 'Photo', icon: Camera },
    { id: 'creative', label: 'Creative', icon: Palette },
    { id: 'design', label: 'Design & Text', icon: Type },
    { id: 'edit', label: 'Edit', icon: Edit3 },
  ];

  const handleRandomSample = () => {
    const pick = SAMPLE_PROMPTS[Math.floor(Math.random() * SAMPLE_PROMPTS.length)];
    setPrompt(pick);
  };

  const handleMagicPolish = async () => {
    if (!prompt.trim() || isPolishing) return;
    try {
      setIsPolishing(true);
      setPolishNotice(null);
      const res = await api.polishPrompt(prompt, selectedStyle);
      setLastOriginalPrompt(prompt);
      setPrompt(res.polished);
      setPolishNotice(`Polished (${res.diff_summary} via ${res.provider === 'lm_studio' ? 'LM Studio' : 'Local Engine'})`);
      setTimeout(() => setPolishNotice(null), 6000);
    } catch (err: any) {
      alert('Prompt polish failed: ' + (err.message || err));
    } finally {
      setIsPolishing(false);
    }
  };

  const handleUndoPolish = () => {
    if (lastOriginalPrompt) {
      setPrompt(lastOriginalPrompt);
      setLastOriginalPrompt(null);
      setPolishNotice(null);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      {/* Mode Selector & Style Dropdown */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
        marginBottom: '1rem'
      }}>
        {/* Mode Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Mode:
          </span>
          <div className="pill-group">
            {modes.map((m) => {
              const Icon = m.icon;
              const isActive = mode === m.id;
              return (
                <button
                  key={m.id}
                  className={`pill-btn ${isActive ? 'active' : ''}`}
                  onClick={() => setMode(m.id)}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <Icon size={14} />
                  <span>{m.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Style Preset Selector & Random Inspirer & Magic Polish */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={handleRandomSample}
            className="btn btn-secondary"
            style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
            title="Load sample prompt"
          >
            <Shuffle size={14} />
            <span>Random Idea</span>
          </button>

          <button
            onClick={handleMagicPolish}
            disabled={isPolishing || !prompt.trim()}
            className="btn btn-secondary"
            style={{
              padding: '0.4rem 0.75rem',
              fontSize: '0.8rem',
              borderColor: 'rgba(168, 85, 247, 0.4)',
              background: 'rgba(168, 85, 247, 0.12)',
              color: '#d8b4fe'
            }}
            title="Enrich & expand prompt using LM Studio / Local Intelligence"
          >
            <Wand2 size={14} color="#c084fc" className={isPolishing ? 'spin' : ''} />
            <span>{isPolishing ? 'Polishing...' : 'Magic Polish'}</span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Style:
            </span>
            <select
              className="select-input"
              value={selectedStyle || 'none'}
              onChange={(e) => setSelectedStyle(e.target.value === 'none' ? '' : e.target.value)}
              style={{ minWidth: 150 }}
            >
              <option value="none">None (Raw)</option>
              {styles.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>
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

          {/* Polish Notice with Undo */}
          {polishNotice && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.75rem',
              color: '#c084fc',
              animation: 'fadeIn 0.2s ease'
            }}>
              <span>{polishNotice}</span>
              {lastOriginalPrompt && (
                <button
                  onClick={handleUndoPolish}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.2rem',
                    fontSize: '0.7rem'
                  }}
                  title="Undo polish"
                >
                  <RotateCcw size={11} />
                  <span>Undo</span>
                </button>
              )}
            </div>
          )}
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
          <span>Negative Prompt</span>
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
