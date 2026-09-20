import React, { useState, useEffect } from 'react';
import {
  HardDrive, Zap, CheckCircle2, Play, Square, ShieldCheck, Download,
  Trash2, RefreshCw, AlertCircle, Check
} from 'lucide-react';
import { ModelInfo, VRAMStrategy } from '../types';
import { api } from '../services/api';

interface ModelsPageProps {
  models: ModelInfo[];
  activeModelId?: string;
  onRefreshModels: () => void;
  vramStrategy: VRAMStrategy;
}

interface DownloadStatus {
  status: string;
  progress: number;
  downloaded_mb: number;
  total_mb: number;
  speed_mbps: number;
  error: string | null;
}

export const ModelsPage: React.FC<ModelsPageProps> = ({
  models,
  activeModelId,
  onRefreshModels,
  vramStrategy
}) => {
  const [loadingModelId, setLoadingModelId] = useState<string | null>(null);
  const [downloadStatuses, setDownloadStatuses] = useState<Record<string, DownloadStatus>>({});
  const [validations, setValidations] = useState<Record<string, any>>({});

  const checkAllStatuses = async () => {
    const statuses: Record<string, DownloadStatus> = {};
    for (const m of models) {
      try {
        const s = await api.getDownloadStatus(m.id);
        statuses[m.id] = s;
      } catch (e) {}
    }
    setDownloadStatuses(statuses);
  };

  useEffect(() => {
    checkAllStatuses();
    const interval = setInterval(checkAllStatuses, 3000);
    return () => clearInterval(interval);
  }, [models]);

  const handleLoad = async (modelId: string) => {
    try {
      setLoadingModelId(modelId);
      await api.loadModel(modelId, vramStrategy);
      onRefreshModels();
    } catch (err: any) {
      alert(err.message || 'Failed to load model');
    } finally {
      setLoadingModelId(null);
    }
  };

  const handleUnload = async (modelId: string) => {
    try {
      setLoadingModelId(modelId);
      await api.unloadModel(modelId);
      onRefreshModels();
    } catch (err: any) {
      alert(err.message || 'Failed to unload model');
    } finally {
      setLoadingModelId(null);
    }
  };

  const handleDownload = async (modelId: string) => {
    try {
      await api.downloadModel(modelId);
      checkAllStatuses();
    } catch (err: any) {
      alert(err.message || 'Failed to start download');
    }
  };

  const handleValidate = async (modelId: string) => {
    try {
      const res = await api.validateModel(modelId);
      setValidations(prev => ({ ...prev, [modelId]: res }));
      setTimeout(() => {
        setValidations(prev => {
          const next = { ...prev };
          delete next[modelId];
          return next;
        });
      }, 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to validate model');
    }
  };

  const handleDelete = async (modelId: string) => {
    if (!confirm(`Are you sure you want to delete downloaded weights for ${modelId}?`)) return;
    try {
      await api.deleteModel(modelId);
      checkAllStatuses();
      onRefreshModels();
    } catch (err: any) {
      alert(err.message || 'Failed to delete weights');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Model Backend Manager</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Download official Safetensors checkpoints or switch architectures in memory.
              Targeted for NVIDIA RTX 5080 (16GB VRAM) with automatic VRAM unloading.
            </p>
          </div>
          <button onClick={() => { onRefreshModels(); checkAllStatuses(); }} className="btn btn-secondary">
            <RefreshCw size={14} />
            <span>Rescan Status</span>
          </button>
        </div>
      </div>

      {/* Models Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1rem' }}>
        {models.map((m) => {
          const isLoaded = m.is_loaded;
          const isLoading = loadingModelId === m.id;
          const dlStatus = downloadStatuses[m.id];
          const isDownloading = dlStatus?.status === 'downloading';
          const isDownloaded = dlStatus?.status === 'complete';
          const valResult = validations[m.id];

          return (
            <div
              key={m.id}
              className="glass-panel"
              style={{
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
                border: isLoaded ? '1px solid var(--primary-light)' : '1px solid var(--border-subtle)',
                boxShadow: isLoaded ? '0 0 20px var(--primary-glow)' : 'none'
              }}
            >
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>{m.name}</h3>
                    {isLoaded && (
                      <span className="badge badge-emerald">
                        <CheckCircle2 size={12} /> In VRAM
                      </span>
                    )}
                    {isDownloaded && (
                      <span className="badge badge-cyan">
                        <Check size={12} /> Local Weights
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    Architecture: <strong style={{ color: 'var(--text-secondary)' }}>{m.architecture.toUpperCase()}</strong>
                  </div>
                </div>

                <div className="badge badge-indigo" style={{ fontFamily: 'var(--font-mono)' }}>
                  ~{m.estimated_vram_gb} GB VRAM
                </div>
              </div>

              {/* Download Progress Bar if downloading */}
              {isDownloading && dlStatus && (
                <div style={{ background: 'var(--bg-input)', padding: '0.65rem', borderRadius: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                    <span style={{ color: 'var(--accent-cyan)' }}>Downloading Checkpoints...</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>
                      {dlStatus.downloaded_mb.toFixed(0)} / {dlStatus.total_mb.toFixed(0)} MB ({dlStatus.progress.toFixed(0)}%)
                    </span>
                  </div>
                  <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${Math.max(5, dlStatus.progress)}%`, height: '100%', background: 'linear-gradient(90deg, #06b6d4, #6366f1)', transition: 'width 0.3s' }} />
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    Speed: {dlStatus.speed_mbps.toFixed(2)} MB/s
                  </div>
                </div>
              )}

              {/* Capabilities */}
              <div>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: 4 }}>
                  Capabilities:
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                  {m.capabilities.map((cap) => (
                    <span
                      key={cap}
                      style={{
                        background: 'var(--bg-input)',
                        padding: '0.2rem 0.5rem',
                        borderRadius: 4,
                        fontSize: '0.7rem',
                        color: 'var(--text-secondary)'
                      }}
                    >
                      {cap.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>

              {/* Recommended Settings */}
              <div style={{ background: 'var(--bg-input)', padding: '0.65rem', borderRadius: 6, fontSize: '0.75rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem' }}>
                <div>Steps: <strong>{m.recommended_settings.steps}</strong></div>
                <div>Guidance: <strong>{m.recommended_settings.guidance}</strong></div>
                <div style={{ gridColumn: 'span 2' }}>Sampler: <strong>{m.recommended_settings.sampler}</strong></div>
              </div>

              {/* Validation notification */}
              {valResult && (
                <div style={{
                  fontSize: '0.75rem',
                  padding: '0.4rem 0.6rem',
                  borderRadius: 6,
                  background: valResult.valid ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                  color: valResult.valid ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                  border: `1px solid ${valResult.valid ? 'var(--accent-emerald)' : 'var(--accent-rose)'}`
                }}>
                  {valResult.valid
                    ? `Validated: Found ${valResult.safetensors_count} safetensors files.`
                    : 'Not installed yet. Download weights below.'}
                </div>
              )}

              {/* Actions Toolbar */}
              <div style={{ display: 'flex', gap: '0.4rem', marginTop: 'auto', flexWrap: 'wrap' }}>
                {/* Download Button */}
                {!isDownloaded && !isDownloading && (
                  <button
                    onClick={() => handleDownload(m.id)}
                    className="btn btn-primary"
                    style={{ flex: 1, fontSize: '0.8rem' }}
                  >
                    <Download size={14} />
                    <span>Download (~{m.estimated_vram_gb}GB)</span>
                  </button>
                )}

                {/* Load / Unload Button */}
                {isLoaded ? (
                  <button
                    onClick={() => handleUnload(m.id)}
                    disabled={isLoading}
                    className="btn btn-secondary"
                    style={{ flex: 1, fontSize: '0.8rem' }}
                  >
                    <Square size={14} />
                    <span>{isLoading ? 'Unloading...' : 'Unload VRAM'}</span>
                  </button>
                ) : (
                  <button
                    onClick={() => handleLoad(m.id)}
                    disabled={isLoading || isDownloading}
                    className="btn btn-secondary"
                    style={{ flex: 1, fontSize: '0.8rem' }}
                  >
                    <Play size={14} fill="currentColor" />
                    <span>{isLoading ? 'Loading...' : 'Load to VRAM'}</span>
                  </button>
                )}

                {/* Validate */}
                <button
                  onClick={() => handleValidate(m.id)}
                  className="btn btn-secondary"
                  style={{ padding: '0.4rem 0.6rem' }}
                  title="Validate weights on disk"
                >
                  <ShieldCheck size={15} />
                </button>

                {/* Delete weights */}
                {isDownloaded && (
                  <button
                    onClick={() => handleDelete(m.id)}
                    className="btn btn-danger"
                    style={{ padding: '0.4rem 0.6rem' }}
                    title="Delete model from disk"
                  >
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
