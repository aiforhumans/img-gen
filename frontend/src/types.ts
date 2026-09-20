export type GenerationMode = 'auto' | 'photo' | 'creative' | 'design' | 'edit';
export type QualityLevel = 'fast' | 'balanced' | 'quality' | 'maximum';
export type AspectRatio = '1:1' | '16:9' | '9:16' | '3:4' | '21:9' | 'custom';
export type VRAMStrategy = 'FULL_GPU' | 'BALANCED' | 'LOW_VRAM' | 'CPU_OFFLOAD';

export interface JobMetrics {
  model_load_time: number;
  prompt_processing_time: number;
  generation_time: number;
  decode_time: number;
  save_time: number;
  total_time: number;
  peak_vram_mb: number;
  images_per_minute: number;
}

export interface GenerationJob {
  id: string;
  created_at: string;
  prompt: string;
  negative_prompt: string;
  model: string;
  mode: GenerationMode;
  aspect_ratio: string;
  quality: QualityLevel;
  width: number;
  height: number;
  steps: number;
  guidance: number;
  seed: number;
  loras: Array<{ path: string; weight: number }>;
  state: 'waiting' | 'loading_model' | 'preparing' | 'generating' | 'decoding' | 'saving' | 'complete' | 'failed' | 'cancelled';
  progress: number;
  current_step: number;
  total_steps: number;
  preview_base64?: string;
  output_image_path?: string;
  output_image_url?: string;
  metrics: JobMetrics;
  error_message?: string;
  routing_reason?: string;
  enhanced_prompt?: string;
  vram_strategy_used: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  architecture: string;
  is_loaded: boolean;
  loaded_device: string;
  estimated_vram_gb: number;
  precision: string;
  quantization: string;
  capabilities: string[];
  recommended_settings: {
    steps: number;
    guidance: number;
    sampler: string;
    scheduler: string;
    optimal_aspect_ratio: string;
  };
  supported_resolutions: Array<{
    label: string;
    width: number;
    height: number;
    aspect_ratio: string;
  }>;
}

export interface GalleryItem {
  id: string;
  created_at: string;
  prompt: string;
  enhanced_prompt: string;
  negative_prompt: string;
  model: string;
  model_version: string;
  seed: number;
  steps: number;
  guidance: number;
  sampler: string;
  scheduler: string;
  width: number;
  height: number;
  generation_time: number;
  peak_vram_mb: number;
  vram_strategy: string;
  gpu_name: string;
  image_path: string;
  thumbnail_path: string;
  is_favorite: number;
  rating: number;
  tags: string;
}

export interface GPUInfo {
  has_cuda: boolean;
  gpu_name: string;
  vram_total_mb: number;
  vram_allocated_mb: number;
  vram_reserved_mb: number;
  vram_free_mb: number;
  vram_strategy: string;
  cuda_version: string;
  torch_version: string;
  driver_version: string;
}

export interface SystemStatus {
  gpu: GPUInfo;
  python_version: string;
  platform: string;
  active_model?: string;
  vram_strategy: string;
  settings: any;
}

export interface RoutingDecision {
  task: string;
  category: string;
  text_rendering: boolean;
  editing: boolean;
  model: string;
  width: number;
  height: number;
  steps: number;
  guidance: number;
  aspect_ratio: string;
  seed: number;
  reason: string;
}

export interface StylePreset {
  id: string;
  name: string;
  category: string;
  prompt_template: string;
  negative_prompt: string;
  recommended_aspect_ratio: string;
  recommended_model: string;
  default?: boolean;
}

export interface LoRAInfo {
  id: string;
  name: string;
  filename: string;
  path: string;
  base_architecture: string;
  trigger_words: string[];
  file_size_mb: number;
  default_strength: number;
  is_favorite: boolean;
}
