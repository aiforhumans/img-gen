import React, { useState } from 'react';
import { PromptBar } from '../components/PromptBar';
import { AspectPicker } from '../components/AspectPicker';
import { ImagePreview } from '../components/ImagePreview';
import {
  GenerationJob, StylePreset, AspectRatio, VRAMStrategy
} from '../types';
import { Sliders, Shuffle } from 'lucide-react';

interface GeneratePageProps {
  prompt: string;
  setPrompt: (p: string) => void;
  negativePrompt: string;
  setNegativePrompt: (np: string) => void;
  selectedStyle: string;
  setSelectedStyle: (s: string) => void;
  styles: StylePreset[];
  currentJob: GenerationJob | null;
  lastCompletedJob: GenerationJob | null;
  onGenerate: () => void;
  onCancel: () => void;
  onDeleteJob: (id: string) => void;
  aspectRatio: AspectRatio;
  setAspectRatio: (ar: AspectRatio) => void;
  width: number;
  setWidth: (w: number) => void;
  height: number;
  setHeight: (h: number) => void;
  steps: number;
  setSteps: (s: number) => void;
  guidance: number;
  setGuidance: (g: number) => void;
  seed: number;
  setSeed: (s: number) => void;
  vramStrategy: VRAMStrategy;
  setVRAMStrategy: (s: VRAMStrategy) => void;
  onReuseJob?: (job: GenerationJob) => void;
}

export const GeneratePage: React.FC<GeneratePageProps> = ({
  prompt,
  setPrompt,
  negativePrompt,
  setNegativePrompt,
  selectedStyle,
  setSelectedStyle,
  styles,
  currentJob,
  lastCompletedJob,
  onGenerate,
  onCancel,
  onDeleteJob,
  aspectRatio,
  setAspectRatio,
  width,
  setWidth,
  height,
  setHeight,
  steps,
  setSteps,
  guidance,
  setGuidance,
  seed,
  setSeed,
  vramStrategy,
  setVRAMStrategy,
  onReuseJob
}) => {
  const [showFineTune, setShowFineTune] = useState(false);

  const isGenerating = currentJob?.state === 'generating' || currentJob?.state === 'loading_model' || currentJob?.state === 'preparing';

  const handleVary = (job: GenerationJob) => {
    setPrompt(job.prompt);
    setSeed(-1);
    onGenerate();
  };

  const handleReusePrompt = (p: string, np: string) => {
    setPrompt(p);
    setNegativePrompt(np);
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(420px, 1.2fr) minmax(400px, 1fr)', gap: '1.5rem', alignItems: 'start' }}>
      {/* Left Column: Prompt & Controls */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <PromptBar
          prompt={prompt}
          setPrompt={setPrompt}
          negativePrompt={negativePrompt}
          setNegativePrompt={setNegativePrompt}
          selectedStyle={selectedStyle}
          setSelectedStyle={setSelectedStyle}
          styles={styles}
          isGenerating={isGenerating}
          onGenerate={onGenerate}
          onCancel={onCancel}
          currentStep={currentJob?.current_step}
          totalSteps={currentJob?.total_steps}
          steps={steps}
          setSteps={setSteps}
        />

        {/* Aspect Ratio Picker Panel */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <AspectPicker
            aspectRatio={aspectRatio}
            setAspectRatio={setAspectRatio}
            width={width}
            height={height}
            setWidth={setWidth}
            setHeight={setHeight}
          />
        </div>

        {/* Minimal Collapsible Fine-Tune Settings Toggle */}
        <div className="glass-panel" style={{ padding: '1rem 1.25rem' }}>
          <div
            onClick={() => setShowFineTune(!showFineTune)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sliders size={16} color="var(--primary)" />
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Fine-Tune Parameters</span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {showFineTune ? 'Hide' : 'Seed, Guidance & VRAM'}
            </span>
          </div>

          {showFineTune && (
            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem', animation: 'fadeIn 0.2s ease' }}>
              {/* Seed Control */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    Seed (-1 = Random):
                  </label>
                  <button
                    type="button"
                    onClick={() => setSeed(-1)}
                    className="btn btn-secondary"
                    style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: 4 }}
                  >
                    <Shuffle size={12} />
                    <span>Randomize</span>
                  </button>
                </div>
                <input
                  type="number"
                  className="input-text"
                  style={{ width: '100%' }}
                  value={seed}
                  onChange={(e) => setSeed(parseInt(e.target.value) || -1)}
                />
              </div>

              {/* Guidance / CFG */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    Guidance Scale (CFG):
                  </label>
                  <span style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: 700 }}>
                    {guidance.toFixed(1)}
                  </span>
                </div>
                <input
                  type="range"
                  min={1.0}
                  max={4.0}
                  step={0.1}
                  value={guidance}
                  onChange={(e) => setGuidance(parseFloat(e.target.value))}
                  style={{ width: '100%' }}
                />
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                  Optimal for Juggernaut-XL Lightning: 1.5 - 2.0
                </div>
              </div>

              {/* VRAM Strategy Selector */}
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                  Hardware Memory Strategy:
                </label>
                <div className="pill-group" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 4 }}>
                  {[
                    { id: 'FULL_GPU', label: 'Full GPU (Fastest)' },
                    { id: 'BALANCED', label: 'Balanced' },
                    { id: 'LOW_VRAM', label: 'Low VRAM' },
                    { id: 'CPU_OFFLOAD', label: 'CPU Offload' }
                  ].map((strat) => (
                    <button
                      key={strat.id}
                      type="button"
                      className={`pill-btn ${vramStrategy === strat.id ? 'active' : ''}`}
                      onClick={() => setVRAMStrategy(strat.id as VRAMStrategy)}
                      style={{ fontSize: '0.75rem', padding: '0.35rem' }}
                    >
                      {strat.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Column: Image Preview & Generation Telemetry */}
      <div>
        <ImagePreview
          currentJob={currentJob}
          lastCompletedJob={lastCompletedJob}
          onVary={handleVary}
          onReusePrompt={handleReusePrompt}
          onReuseSettings={onReuseJob}
          onDelete={onDeleteJob}
        />
      </div>
    </div>
  );
};
