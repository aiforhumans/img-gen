import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { GeneratePage } from './pages/GeneratePage';
import { GalleryPage } from './pages/GalleryPage';
import {
  GenerationJob, GalleryItem, SystemStatus,
  StylePreset, AspectRatio, VRAMStrategy
} from './types';
import { ReferenceImageState } from './components/ReferenceImagePanel';
import { api } from './services/api';

export const App: React.FC = () => {
  // Navigation
  const [activeTab, setActiveTab] = useState<string>('generate');

  // Generation Parameters (Tuned for Turbo Photorealism)
  const [prompt, setPrompt] = useState<string>(
    'A cinematic photograph of an abandoned 1980s arcade at night, wet floor, neon signs saying ARCADE 84.'
  );
  const [negativePrompt, setNegativePrompt] = useState<string>('');
  const [selectedStyle, setSelectedStyle] = useState<string>('cinematic');
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [width, setWidth] = useState<number>(1280);
  const [height, setHeight] = useState<number>(720);
  const [steps, setSteps] = useState<number>(8);
  const [guidance, setGuidance] = useState<number>(1.5);
  const [seed, setSeed] = useState<number>(-1);
  const [sampler, setSampler] = useState<string>('Euler');
  const [vramStrategy, setVRAMStrategy] = useState<VRAMStrategy>('FULL_GPU');

  // Reference Image State
  const [reference1, setReference1] = useState<ReferenceImageState | null>(null);
  const [reference2, setReference2] = useState<ReferenceImageState | null>(null);

  // Server Data
  const [styles, setStyles] = useState<StylePreset[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | undefined>(undefined);

  // Job Queue & Live Generation State
  const [currentJob, setCurrentJob] = useState<GenerationJob | null>(null);
  const [lastCompletedJob, setLastCompletedJob] = useState<GenerationJob | null>(null);
  const pollTimeoutRef = useRef<number | null>(null);

  // Initial Data Fetching & Telemetry Polling
  useEffect(() => {
    let isSubscribed = true;

    Promise.all([
      api.getStyles(),
      api.getSystemStatus()
    ]).then(([stylesData, sysData]) => {
      if (isSubscribed) {
        setStyles(stylesData);
        setSystemStatus(sysData);
        if (sysData.vram_strategy) {
          setVRAMStrategy(sysData.vram_strategy as VRAMStrategy);
        }
      }
    }).catch((err) => {
      console.error('Failed to load initial studio data:', err);
    });

    // Background polling for GPU VRAM & status
    const sysInterval = window.setInterval(async () => {
      try {
        const sysData = await api.getSystemStatus();
        if (isSubscribed) {
          setSystemStatus(sysData);
        }
      } catch {
        // Ignore background network blips
      }
    }, 4000);

    return () => {
      isSubscribed = false;
      clearInterval(sysInterval);
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    };
  }, []);

  // Poll Job Status
  const pollJobStatus = async (jobId: string) => {
    try {
      const job = await api.getJob(jobId);
      setCurrentJob(job);

      if (job.state === 'complete') {
        setLastCompletedJob(job);
        setCurrentJob(null);
        return;
      }

      if (job.state === 'cancelled') {
        setCurrentJob(null);
        return;
      }

      if (job.state === 'failed') {
        alert(`Generation failed: ${job.error_message || 'Unknown error'}`);
        setCurrentJob(null);
        return;
      }

      // Fast polling interval: 80ms when generating to catch and show each step, 500ms when preparing/loading
      const delay = (job.state === 'generating') ? 80 : 500;
      pollTimeoutRef.current = window.setTimeout(() => pollJobStatus(jobId), delay);
    } catch (err) {
      console.error('Polling error:', err);
      setCurrentJob(null);
    }
  };

  // Submit Generation Job
  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    try {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);

      // Immediately set currentJob to show generation status and reset preview
      setCurrentJob({
        id: 'initiating',
        created_at: new Date().toISOString(),
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim(),
        model: 'zimage-turbo',
        mode: 'photo',
        style: selectedStyle,
        aspect_ratio: aspectRatio,
        quality: 'balanced',
        width,
        height,
        steps,
        guidance,
        seed,
        loras: [],
        state: 'waiting',
        progress: 0,
        current_step: 0,
        total_steps: steps,
        vram_strategy_used: vramStrategy,
        metrics: {
          model_load_time: 0,
          prompt_processing_time: 0,
          generation_time: 0,
          decode_time: 0,
          save_time: 0,
          total_time: 0,
          peak_vram_mb: 0,
          images_per_minute: 0
        }
      });

      const jobResponse = await api.submitGeneration({
        prompt: prompt.trim(),
        original_prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim(),
        model: 'zimage-turbo',
        mode: 'photo',
        style: selectedStyle,
        aspect_ratio: aspectRatio,
        width,
        height,
        steps,
        guidance,
        seed,
        sampler,
        scheduler: 'Default',
        vram_strategy: vramStrategy,
        precision: 'fp16',
        reference_image_path: reference1?.path,
        reference_mode: reference1?.mode,
        reference_strength: reference1?.strength,
        reference_image_path_2: reference2?.path,
        reference_mode_2: reference2?.mode,
        reference_strength_2: reference2?.strength
      });

      // Start responsive polling
      pollJobStatus(jobResponse.job_id);
    } catch (err: any) {
      alert(`Submission error: ${err.message || err}`);
    }
  };

  // Cancel Generation Job
  const handleCancel = async () => {
    if (!currentJob) return;
    try {
      await api.cancelJob(currentJob.id);
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
      setCurrentJob(null);
    } catch (err: any) {
      console.error('Cancellation request failed:', err);
    }
  };

  // Reuse Full Settings from Gallery Item
  const handleReuseSettings = (item: GalleryItem) => {
    setPrompt(item.prompt);
    if (item.negative_prompt) setNegativePrompt(item.negative_prompt);
    if (item.seed) setSeed(item.seed);
    if (item.style) setSelectedStyle(item.style);
    if (item.aspect_ratio) setAspectRatio(item.aspect_ratio as AspectRatio);
    if (item.width) setWidth(item.width);
    if (item.height) setHeight(item.height);
    if (item.steps) setSteps(item.steps);
    if (item.guidance) setGuidance(item.guidance);
    if (item.sampler) setSampler(item.sampler);
    if (item.vram_strategy) setVRAMStrategy(item.vram_strategy as VRAMStrategy);

    setActiveTab('generate');
  };

  // Reuse Full Settings from Previous Job
  const handleReuseJob = (job: GenerationJob) => {
    setPrompt(job.prompt);
    if (job.negative_prompt) setNegativePrompt(job.negative_prompt);
    if (job.seed) setSeed(job.seed);
    if (job.style) setSelectedStyle(job.style);
    if (job.aspect_ratio) setAspectRatio(job.aspect_ratio as AspectRatio);
    if (job.width) setWidth(job.width);
    if (job.height) setHeight(job.height);
    if (job.steps) setSteps(job.steps);
    if (job.guidance) setGuidance(job.guidance);
    if (job.sampler) setSampler(job.sampler);
    if (job.vram_strategy) setVRAMStrategy(job.vram_strategy as VRAMStrategy);

    setActiveTab('generate');
  };

  // Delete Job / Gallery Item
  const handleDeleteJob = async (id: string) => {
    if (!confirm('Are you sure you want to delete this image?')) return;
    try {
      await api.deleteGeneration(id);
      if (lastCompletedJob?.id === id) {
        setLastCompletedJob(null);
      }
    } catch (err) {
      console.error('Failed to delete image:', err);
    }
  };

  return (
    <div className="app-container">
      {/* Top Header with 2 Clean Tabs */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        activeModel="TURBO PHOTOREALISM"
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
            selectedStyle={selectedStyle}
            setSelectedStyle={setSelectedStyle}
            styles={styles}
            currentJob={currentJob}
            lastCompletedJob={lastCompletedJob}
            onGenerate={handleGenerate}
            onCancel={handleCancel}
            onDeleteJob={handleDeleteJob}
            aspectRatio={aspectRatio}
            setAspectRatio={setAspectRatio}
            width={width}
            setWidth={setWidth}
            height={height}
            setHeight={setHeight}
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
            onReuseJob={handleReuseJob}
            reference1={reference1}
            setReference1={setReference1}
            reference2={reference2}
            setReference2={setReference2}
          />
        )}

        {activeTab === 'gallery' && (
          <GalleryPage
            onReuseSettings={handleReuseSettings}
          />
        )}
      </main>
    </div>
  );
};

export default App;
