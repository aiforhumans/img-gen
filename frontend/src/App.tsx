import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { GeneratePage } from './pages/GeneratePage';
import { EditPage } from './pages/EditPage';
import { GalleryPage } from './pages/GalleryPage';
import { ModelsPage } from './pages/ModelsPage';
import { LoRAPage } from './pages/LoRAPage';
import { SettingsPage } from './pages/SettingsPage';
import { SystemPage } from './pages/SystemPage';

import {
  GenerationJob, ModelInfo, StylePreset, GenerationMode,
  QualityLevel, AspectRatio, VRAMStrategy, SystemStatus, GalleryItem
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

  // Server Data
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [styles, setStyles] = useState<StylePreset[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | undefined>(undefined);

  // Job Queue & Live Generation State
  const [currentJob, setCurrentJob] = useState<GenerationJob | null>(null);
  const [lastCompletedJob, setLastCompletedJob] = useState<GenerationJob | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

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
      } catch (e) {}
    }, 4000);

    return () => clearInterval(sysInterval);
  }, []);

  // Job Execution & Polling
  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    try {
      const res = await api.submitGeneration({
        prompt,
        negative_prompt: negativePrompt,
        model: selectedModel,
        mode,
        aspect_ratio: aspectRatio,
        quality,
        width,
        height,
        steps,
        guidance,
        seed
      });

      // Start rapid polling
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const job = await api.getJob(res.job_id);
          setCurrentJob(job);

          if (job.state === 'complete') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            setLastCompletedJob(job);
            setCurrentJob(null);
          } else if (job.state === 'failed' || job.state === 'cancelled') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (job.state === 'failed') {
              alert(job.error_message || 'Generation failed.');
            }
            setCurrentJob(null);
          }
        } catch (err) {
          console.error('Job poll error:', err);
        }
      }, 250);
    } catch (err: any) {
      alert(err.message || 'Failed to submit generation');
    }
  };

  const handleCancel = async () => {
    if (currentJob) {
      await api.cancelJob(currentJob.id);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
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

  const handleReuseSettings = (item: GalleryItem) => {
    setPrompt(item.prompt);
    setNegativePrompt(item.negative_prompt || '');
    if (item.model) setSelectedModel(item.model);
    setWidth(item.width);
    setHeight(item.height);
    setSteps(item.steps);
    setGuidance(item.guidance);
    setSeed(item.seed);
    setActiveTab('generate');
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
          <LoRAPage />
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
