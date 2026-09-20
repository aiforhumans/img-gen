import {
  GenerationJob, ModelInfo, GalleryItem, SystemStatus,
  RoutingDecision, StylePreset, LoRAInfo, VRAMStrategy,
  UpscaleParams, UpscaleResult
} from '../types';

const API_BASE = 'http://127.0.0.1:7860';

export const api = {
  // Generation & Queue
  async submitGeneration(params: {
    prompt: string;
    original_prompt?: string;
    negative_prompt?: string;
    model?: string;
    mode?: string;
    style?: string;
    aspect_ratio?: string;
    quality?: string;
    width?: number;
    height?: number;
    steps?: number;
    guidance?: number;
    seed?: number;
    sampler?: string;
    scheduler?: string;
    vram_strategy?: string;
    precision?: string;
    loras?: Array<{ path: string; weight: number; id?: string }>;
    edit_mode?: string;
    init_image?: string;
    mask_image?: string;
    strength?: number;
    expand_left?: number;
    expand_right?: number;
    expand_top?: number;
    expand_bottom?: number;
    reference_image_path?: string;
    reference_mode?: string;
    reference_strength?: number;
    reference_image_path_2?: string;
    reference_mode_2?: string;
    reference_strength_2?: number;
  }): Promise<{ job_id: string; state: string }> {
    const res = await fetch(`${API_BASE}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to submit generation');
    }
    return res.json();
  },

  async analyzePrompt(prompt: string, mode: string = 'auto'): Promise<RoutingDecision> {
    const res = await fetch(`${API_BASE}/api/analyze-prompt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, mode })
    });
    if (!res.ok) throw new Error('Failed to analyze prompt');
    return res.json();
  },

  async polishPrompt(prompt: string, style?: string): Promise<{
    original: string;
    polished: string;
    provider: string;
    diff_summary: string;
  }> {
    const res = await fetch(`${API_BASE}/api/prompt/polish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, style })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to polish prompt');
    }
    return res.json();
  },

  async upscaleImage(params: UpscaleParams): Promise<UpscaleResult> {
    const res = await fetch(`${API_BASE}/api/upscale`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to upscale image');
    }
    return res.json();
  },

  async getJobs(): Promise<GenerationJob[]> {
    const res = await fetch(`${API_BASE}/api/jobs`);
    if (!res.ok) throw new Error('Failed to fetch jobs');
    return res.json();
  },

  async getJob(id: string): Promise<GenerationJob> {
    const res = await fetch(`${API_BASE}/api/jobs/${id}`);
    if (!res.ok) throw new Error('Failed to fetch job');
    return res.json();
  },

  async cancelJob(id: string): Promise<boolean> {
    const res = await fetch(`${API_BASE}/api/jobs/${id}/cancel`, { method: 'POST' });
    return res.ok;
  },

  async clearCompletedJobs(): Promise<void> {
    await fetch(`${API_BASE}/api/jobs/clear`, { method: 'POST' });
  },

  // Models
  async getModels(): Promise<{
    models: ModelInfo[];
    active_model_id?: string;
    current_vram_strategy: string;
  }> {
    const res = await fetch(`${API_BASE}/api/models`);
    if (!res.ok) throw new Error('Failed to fetch models');
    return res.json();
  },

  async loadModel(modelId: string, strategy?: VRAMStrategy): Promise<void> {
    const res = await fetch(`${API_BASE}/api/models/${modelId}/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vram_strategy: strategy })
    });
    if (!res.ok) throw new Error('Failed to load model');
  },

  async unloadModel(modelId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/models/${modelId}/unload`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to unload model');
  },

  async downloadModel(modelId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/models/${modelId}/download`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to initiate model download');
    return res.json();
  },

  async getDownloadStatus(modelId: string): Promise<{
    status: string;
    progress: number;
    downloaded_mb: number;
    total_mb: number;
    speed_mbps: number;
    error: string | null;
  }> {
    const res = await fetch(`${API_BASE}/api/models/${modelId}/download-status`);
    if (!res.ok) throw new Error('Failed to get download status');
    return res.json();
  },

  async validateModel(modelId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/models/${modelId}/validate`);
    if (!res.ok) throw new Error('Failed to validate model');
    return res.json();
  },

  async deleteModel(modelId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/models/${modelId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete model');
    return res.json();
  },

  async getSamplers(modelId: string, steps: number = 8): Promise<{
    model_id: string;
    architecture: string;
    steps: number;
    samplers: string[];
    default: string;
  }> {
    const res = await fetch(`${API_BASE}/api/models/${modelId}/samplers?steps=${steps}`);
    if (!res.ok) throw new Error('Failed to fetch samplers');
    return res.json();
  },

  // Reference Images & IP-Adapter
  async uploadReferenceImage(file: File): Promise<{
    path: string;
    thumbnail_base64: string;
    width: number;
    height: number;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/reference/upload`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to upload reference image');
    }
    return res.json();
  },

  async getIPAdapterStatus(): Promise<{
    style_weights_available: boolean;
    subject_weights_available: boolean;
    clip_encoder_loaded: boolean;
    active_mode: string | null;
    downloading: boolean;
    download_progress: number;
  }> {
    const res = await fetch(`${API_BASE}/api/ip-adapter/status`);
    if (!res.ok) throw new Error('Failed to fetch IP-Adapter status');
    return res.json();
  },

  async downloadIPAdapterWeights(mode: string): Promise<{ started: boolean }> {
    const res = await fetch(`${API_BASE}/api/ip-adapter/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode })
    });
    if (!res.ok) throw new Error('Failed to start IP-Adapter download');
    return res.json();
  },

  // Gallery
  async getGallery(params: {
    limit?: number;
    offset?: number;
    favorite_only?: boolean;
    model?: string;
    search?: string;
  } = {}): Promise<{ items: GalleryItem[]; total: number }> {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', params.limit.toString());
    if (params.offset) q.set('offset', params.offset.toString());
    if (params.favorite_only) q.set('favorite_only', 'true');
    if (params.model) q.set('model', params.model);
    if (params.search) q.set('search', params.search);

    const res = await fetch(`${API_BASE}/api/gallery?${q.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch gallery items');
    return res.json();
  },

  getImageUrl(id: string): string {
    return `${API_BASE}/api/gallery/image/${id}`;
  },

  getThumbUrl(id: string): string {
    return `${API_BASE}/api/gallery/thumb/${id}`;
  },

  async toggleFavorite(id: string): Promise<boolean> {
    const res = await fetch(`${API_BASE}/api/gallery/${id}/favorite`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to toggle favorite');
    const data = await res.json();
    return data.is_favorite;
  },

  async deleteGeneration(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/gallery/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete image');
  },

  // Styles
  async getStyles(): Promise<StylePreset[]> {
    const res = await fetch(`${API_BASE}/api/styles`);
    if (!res.ok) throw new Error('Failed to fetch styles');
    const data = await res.json();
    return data.styles;
  },

  // LoRAs
  async getLoRAs(): Promise<LoRAInfo[]> {
    const res = await fetch(`${API_BASE}/api/loras`);
    if (!res.ok) throw new Error('Failed to fetch LoRAs');
    const data = await res.json();
    return data.loras;
  },

  async rescanLoRAs(): Promise<LoRAInfo[]> {
    const res = await fetch(`${API_BASE}/api/loras/scan`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to rescan LoRAs');
    const data = await res.json();
    return data.loras;
  },

  // System & VRAM
  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetch(`${API_BASE}/api/system`);
    if (!res.ok) throw new Error('Failed to fetch system status');
    return res.json();
  },

  async updateVRAMStrategy(strategy: VRAMStrategy): Promise<void> {
    const res = await fetch(`${API_BASE}/api/system/vram-strategy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strategy })
    });
    if (!res.ok) throw new Error('Failed to update VRAM strategy');
  },

  async clearGPUCache(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/system/clear-cache`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to clear cache');
    return res.json();
  },

  async getDiagnostics(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/system/diagnostics`);
    if (!res.ok) throw new Error('Failed to get diagnostics');
    return res.json();
  }
};
