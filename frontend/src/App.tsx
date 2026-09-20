import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { GeneratePage } from './pages/GeneratePage';
import { EditPage } from './pages/EditPage';
import { GalleryPage } from './pages/GalleryPage';
import { ModelsPage } from './pages/ModelsPage';
import { LoRAPage } from './pages/LoRAPage';
import { SystemPage } from './pages/SystemPage';
import { SettingsPage } from './pages/SettingsPage';
import {
  GenerationJob, ModelInfo, GalleryItem, SystemStatus,
  StylePreset, GenerationMode, QualityLevel, AspectRatio,
  VRAMStrategy, LoRAInfo
} from './types';
import { api } from './services/api';

export const App: React.FC = () => {
  // Navigation
  const [activeTab, setActiveTab] = useState<string>('generate');

  // Generation Parameters
  const [prompt, setPrompt] = useState<string>(
    'A cinematic photograph of an abandoned 1980s arcade at night, wet floor, neon signs saying ARCADE 84.'
  );
  const [negativePrompt, setNegativePrompt] = useState<string>('');
  const [mode, setMode] = useState<GenerationMode>('auto');
  const [selectedStyle, setSelectedStyle] = useState<string>('cinematic');
  const [selectedModel, setSelectedModel] = useState<string>('auto');
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [width, setWidth] = useState<number>(1280);
  const [height, setHeight] = useState<number>(720);
  const [quality, setQuality] = useState<QualityLevel>('balanced');
  const [steps, setSteps] = useState<number>(8);
  const [guidance, setGuidance] = useState<number>(1.5);
  const [seed, setSeed] = useState<number>(-1);
  const [sampler, setSampler] = useState<string>('Default (Recommended)');
  const [vramStrategy, setVRAMStrategy] = useState<VRAMStrategy>('FULL_GPU');

  // Active LoRAs for Generation
  const [activeLoras, setActiveLoras] = useState<Array<{ id: string; name: string; path: string; weight: number }>>([]);

  // Server Data
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [styles, setStyles] = useState<StylePreset[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | undefined>(undefined);

  // Job Queue & Live Generation State
  const [currentJob, setCurrentJob] = useState<GenerationJob | null>(null);
  const [lastCompletedJob, setLastCompletedJob] = useState<GenerationJob | null>(null);
  const pollTimeoutRef = useRef<number | null>(null);

  // Edit Tab State
  const [editImageSrc, setEditImageSrc] = useState<string>('');
  const [editPrompt, setEditPrompt] = useState<string>('');

  // Initial Data Fetching
  const fetchInitialData = async () => {
    try {
      const [modelsData, stylesData, sysData] = await Promise.all([
        api.getModels(),
        api.getStyles(),
        api.getSystemStatus()
      ]);
      setModels(modelsData.models);
      setStyles(stylesData);
      setSystemStatus(sysData);
      if (sysData.vram_strategy) {
        setVRAMStrategy(sysData.vram_strategy as VRAMStrategy);
      }
    } catch (err) {
      console.error('Failed to initialize server data:', err);
    }
  };

  useEffect(() => {
    fetchInitialData();
    // Background polling for GPU VRAM & status
    const sysInterval = window.setInterval(async () => {
      try {
        const sysData = await api.getSystemStatus();
        setSystemStatus(sysData);
      } catch {
        // Ignore background polling network glitches
      }
    }, 4000);

    return () => {
      clearInterval(sysInterval);
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  // Job Execution & Adaptive Polling (Phase 14 & 15)
  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }

    try {
      const res = await api.submitGeneration({
        prompt,
        original_prompt: prompt,
        negative_prompt: negativePrompt,
        model: selectedModel,
        mode,
        style: selectedStyle,
        aspect_ratio: aspectRatio,
        quality,
        width,
        height,
        steps,
        guidance,
        seed,
        sampler,
        vram_strategy: vramStrategy,
        loras: activeLoras
      });

      // Adaptive polling function: 250ms for active generation, 600ms for preparation, stop on terminal state
      const checkJob = async () => {
        try {
          const job = await api.getJob(res.job_id);
          setCurrentJob(job);

          if (job.state === 'complete') {
            setLastCompletedJob(job);
            setCurrentJob(null);
            return;
          } else if (job.state === 'cancelled') {
            // Immediate clean reset on cancellation without alert (Phase 3)
            setCurrentJob(null);
            return;
          } else if (job.state === 'failed') {
            alert(job.error_message || 'Generation failed.');
            setCurrentJob(null);
            return;
          }

          // Schedule next poll adaptively
          const intervalMs = (job.state === 'generating' || job.state === 'decoding' || job.state === 'saving') ? 250 : 600;
          pollTimeoutRef.current = window.setTimeout(checkJob, intervalMs);
        } catch (err) {
          console.error('Job poll error:', err);
          pollTimeoutRef.current = window.setTimeout(checkJob, 1000);
        }
      };

      pollTimeoutRef.current = window.setTimeout(checkJob, 250);
    } catch (err: any) {
      alert(err.message || 'Failed to submit generation');
    }
  };

  const handleCancel = async () => {
    if (currentJob) {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
        pollTimeoutRef.current = null;
      }
      try {
        await api.cancelJob(currentJob.id);
      } catch (err) {
        console.warn('Cancellation error:', err);
      }
      setCurrentJob(null);
    }
  };

  const handleDeleteJob = (id: string) => {
    if (lastCompletedJob?.id === id) setLastCompletedJob(null);
    if (currentJob?.id === id) setCurrentJob(null);
  };

  // Cross-tab workflows
  const handleSendToEdit = (imgSrc: string, p: string) => {
    setEditImageSrc(imgSrc);
    setEditPrompt(p);
    setActiveTab('edit');
  };

  // Full Reuse Settings (Phase 2, 5, 14)
  const handleReuseSettings = (item: GalleryItem) => {
    setPrompt(item.original_prompt || item.prompt);
    setNegativePrompt(item.negative_prompt || '');
    if (item.model) setSelectedModel(item.model);
    if (item.mode) setMode(item.mode);
    if (item.style) setSelectedStyle(item.style);
    if (item.aspect_ratio) setAspectRatio(item.aspect_ratio);
    if (item.quality) setQuality(item.quality);
    if (item.sampler) setSampler(item.sampler);
    if (item.vram_strategy) setVRAMStrategy(item.vram_strategy as VRAMStrategy);
    if (item.loras && Array.isArray(item.loras)) {
      setActiveLoras(item.loras as any);
    }
    setWidth(item.width);
    setHeight(item.height);
    setSteps(item.steps);
    setGuidance(item.guidance);
    setSeed(item.seed);
    setActiveTab('generate');
  };

  const handleReuseJob = (job: GenerationJob) => {
    setPrompt(job.original_prompt || job.prompt);
    setNegativePrompt(job.negative_prompt || '');
    if (job.model) setSelectedModel(job.model);
    if (job.mode) setMode(job.mode);
    if (job.style) setSelectedStyle(job.style);
    if (job.aspect_ratio) setAspectRatio(job.aspect_ratio as AspectRatio);
    if (job.quality) setQuality(job.quality);
    if (job.sampler) setSampler(job.sampler);
    if (job.vram_strategy) setVRAMStrategy(job.vram_strategy as VRAMStrategy);
    if (job.loras && Array.isArray(job.loras)) {
      setActiveLoras(job.loras as any);
    }
    setWidth(job.width);
    setHeight(job.height);
    setSteps(job.steps);
    setGuidance(job.guidance);
    setSeed(job.seed);
    setActiveTab('generate');
  };

  // LoRA Management callbacks
  const handleToggleLoRA = (lora: LoRAInfo, weight: number) => {
    setActiveLoras(prev => {
      const exists = prev.some(l => l.id === lora.id || l.path === lora.path);
      if (exists) {
        return prev.filter(l => l.id !== lora.id && l.path !== lora.path);
      } else {
        return [...prev, { id: lora.id, name: lora.name, path: lora.path, weight }];
      }
    });
  };

  const handleUpdateLoRAWeight = (loraId: string, weight: number) => {
    setActiveLoras(prev => prev.map(l => (l.id === loraId || l.path === loraId) ? { ...l, weight } : l));
  };

  const handleRemoveLoRA = (idOrPath: string) => {
    setActiveLoras(prev => prev.filter(l => l.id !== idOrPath && l.path !== idOrPath));
  };

  return (
    <div className="app-shell">
      {/* Universal Top Header Navigation */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        activeModel={models.find(m => m.is_loaded)?.name || selectedModel}
        isGenerating={currentJob?.state === 'generating' || currentJob?.state === 'loading_model'}
      />

      {/* Main Tab Content */}
      <main className="main-content">
        {activeTab === 'generate' && (
          <GeneratePage
            prompt={prompt}
            setPrompt={setPrompt}
            negativePrompt={negativePrompt}
            setNegativePrompt={setNegativePrompt}
            mode={mode}
            setMode={setMode}
            selectedStyle={selectedStyle}
            setSelectedStyle={setSelectedStyle}
            styles={styles}
            models={models}
            currentJob={currentJob}
            lastCompletedJob={lastCompletedJob}
            onGenerate={handleGenerate}
            onCancel={handleCancel}
            onSendToEdit={handleSendToEdit}
            onSendToInpaint={handleSendToEdit}
            onSendToOutpaint={handleSendToEdit}
            onDeleteJob={handleDeleteJob}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            aspectRatio={aspectRatio}
            setAspectRatio={setAspectRatio}
            width={width}
            setWidth={setWidth}
            height={height}
            setHeight={setHeight}
            quality={quality}
            setQuality={setQuality}
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
            activeLoras={activeLoras}
            onRemoveLoRA={handleRemoveLoRA}
            onReuseJob={handleReuseJob}
          />
        )}

        {activeTab === 'edit' && (
          <EditPage
            initialImageSrc={editImageSrc}
            initialPrompt={editPrompt}
            onGenerationComplete={() => {}}
          />
        )}

        {activeTab === 'gallery' && (
          <GalleryPage
            onReuseSettings={handleReuseSettings}
            onSendToEditor={handleSendToEdit}
          />
        )}

        {activeTab === 'models' && (
          <ModelsPage
            models={models}
            activeModelId={models.find(m => m.is_loaded)?.id}
            onRefreshModels={fetchInitialData}
            vramStrategy={vramStrategy}
          />
        )}

        {activeTab === 'loras' && (
          <LoRAPage
            activeLoras={activeLoras}
            onToggleLoRA={handleToggleLoRA}
            onUpdateWeight={handleUpdateLoRAWeight}
          />
        )}

        {activeTab === 'system' && (
          <SystemPage
            systemStatus={systemStatus}
            onRefresh={fetchInitialData}
            vramStrategy={vramStrategy}
            setVRAMStrategy={setVRAMStrategy}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsPage settings={systemStatus?.settings} />
        )}
      </main>
    </div>
  );
};

export default App;
