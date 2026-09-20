import React, { useState, useEffect } from 'react';
import { PromptBar } from '../components/PromptBar';
import { AspectPicker } from '../components/AspectPicker';
import { QualityPicker } from '../components/QualityPicker';
import { AdvancedSettingsDrawer } from '../components/AdvancedSettingsDrawer';
import { GenerationAnalysisDrawer } from '../components/GenerationAnalysisDrawer';
import { ImagePreview } from '../components/ImagePreview';
import {
  GenerationJob, ModelInfo, StylePreset, GenerationMode,
  QualityLevel, AspectRatio, VRAMStrategy, RoutingDecision
} from '../types';
import { api } from '../services/api';

interface GeneratePageProps {
  prompt: string;
  setPrompt: (p: string) => void;
  negativePrompt: string;
  setNegativePrompt: (np: string) => void;
  mode: GenerationMode;
  setMode: (m: GenerationMode) => void;
  selectedStyle: string;
  setSelectedStyle: (s: string) => void;
  styles: StylePreset[];
  models: ModelInfo[];
  currentJob: GenerationJob | null;
  lastCompletedJob: GenerationJob | null;
  onGenerate: () => void;
  onCancel: () => void;
  onSendToEdit: (imageSrc: string, prompt: string) => void;
  onSendToInpaint: (imageSrc: string, prompt: string) => void;
  onSendToOutpaint: (imageSrc: string, prompt: string) => void;
  onDeleteJob: (id: string) => void;
  selectedModel: string;
  setSelectedModel: (m: string) => void;
  aspectRatio: AspectRatio;
  setAspectRatio: (ar: AspectRatio) => void;
  width: number;
  setWidth: (w: number) => void;
  height: number;
  setHeight: (h: number) => void;
  quality: QualityLevel;
  setQuality: (q: QualityLevel) => void;
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
  activeLoras?: Array<{ id?: string; name?: string; path: string; weight: number }>;
  onRemoveLoRA?: (idOrPath: string) => void;
  onReuseJob?: (job: GenerationJob) => void;
}

export const GeneratePage: React.FC<GeneratePageProps> = ({
  prompt,
  setPrompt,
  negativePrompt,
  setNegativePrompt,
  mode,
  setMode,
  selectedStyle,
  setSelectedStyle,
  styles,
  models,
  currentJob,
  lastCompletedJob,
  onGenerate,
  onCancel,
  onSendToEdit,
  onSendToInpaint,
  onSendToOutpaint,
  onDeleteJob,
  selectedModel,
  setSelectedModel,
  aspectRatio,
  setAspectRatio,
  width,
  setWidth,
  height,
  setHeight,
  quality,
  setQuality,
  steps,
  setSteps,
  guidance,
  setGuidance,
  seed,
  setSeed,
  sampler,
  setSampler,
  vramStrategy,
  setVRAMStrategy,
  activeLoras = [],
  onRemoveLoRA,
  onReuseJob
}) => {
  const [isAdvOpen, setIsAdvOpen] = useState(false);
  const [analysisDecision, setAnalysisDecision] = useState<RoutingDecision | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const isGenerating = currentJob?.state === 'generating' || currentJob?.state === 'loading_model' || currentJob?.state === 'preparing';

  // Debounced Auto Engine analysis
  useEffect(() => {
    if (!prompt.trim() || mode !== 'auto') {
      setAnalysisDecision(null);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        setIsAnalyzing(true);
        const res = await api.analyzePrompt(prompt, mode);
        setAnalysisDecision(res);
      } catch (err) {
        console.error('Prompt analysis error:', err);
      } finally {
        setIsAnalyzing(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [prompt, mode]);

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
          mode={mode}
          setMode={setMode}
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

        {/* Aspect Ratio & Quality Grid */}
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <AspectPicker
            aspectRatio={aspectRatio}
            setAspectRatio={setAspectRatio}
            width={width}
            height={height}
            setWidth={setWidth}
            setHeight={setHeight}
          />
          <QualityPicker
            quality={quality}
            setQuality={setQuality}
            setSteps={setSteps}
          />
        </div>

        {/* Auto Engine Generation Analysis Breakdown */}
        {mode === 'auto' && (
          <GenerationAnalysisDrawer
            decision={analysisDecision}
            isLoading={isAnalyzing}
          />
        )}

        {/* Active LoRA Chips */}
        {activeLoras.length > 0 && (
          <div className="glass-panel" style={{ padding: '0.75rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Active LoRAs:</span>
            {activeLoras.map((l) => (
              <span
                key={l.id || l.path}
                className="badge badge-indigo"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
              >
                <span>{l.name || l.id} ({l.weight.toFixed(2)})</span>
                {onRemoveLoRA && (
                  <button
                    onClick={() => onRemoveLoRA(l.id || l.path)}
                    style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, fontSize: '0.9rem', lineHeight: 1 }}
                    title="Remove LoRA from active generation"
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
          </div>
        )}

        {/* Advanced Model & Generation Controls Drawer */}
        <AdvancedSettingsDrawer
          isOpen={isAdvOpen}
          setIsOpen={setIsAdvOpen}
          models={models}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          steps={steps}
          setSteps={setSteps}
          guidance={guidance}
          setGuidance={setGuidance}
          seed={seed}
          setSeed={setSeed}
          sampler={sampler}
          setSampler={setSampler}
          vramStrategy={vramStrategy}
          setVRAMStrategy={setVRAMStrategy}
        />
      </div>

      {/* Right Column: Large Image Preview & Telemetry Toolbar */}
      <div>
        <ImagePreview
          currentJob={currentJob}
          lastCompletedJob={lastCompletedJob}
          onVary={handleVary}
          onEdit={(src, p) => onSendToEdit(src, p)}
          onInpaint={(src, p) => onSendToInpaint(src, p)}
          onOutpaint={(src, p) => onSendToOutpaint(src, p)}
          onReusePrompt={handleReusePrompt}
          onReuseSettings={onReuseJob}
          onDelete={onDeleteJob}
        />
      </div>
    </div>
  );
};
