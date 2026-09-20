import React, { useState } from 'react';
import {
  Download, Trash2, Sliders, Brush, Maximize2, RefreshCw,
  Sparkles, Layers, Info, Check, Copy, ExternalLink, Activity, Zap
} from 'lucide-react';
import { GenerationJob } from '../types';
import { api } from '../services/api';

interface ImagePreviewProps {
  currentJob: GenerationJob | null;
  lastCompletedJob: GenerationJob | null;
  onVary: (job: GenerationJob) => void;
  onEdit: (imageUrl: string, prompt: string) => void;
  onInpaint: (imageUrl: string, prompt: string) => void;
  onOutpaint: (imageUrl: string, prompt: string) => void;
  onReusePrompt: (prompt: string, negPrompt: string) => void;
  onDelete: (id: string) => void;
}

export const ImagePreview: React.FC<ImagePreviewProps> = ({
  currentJob,
  lastCompletedJob,
  onVary,
  onEdit,
  onInpaint,
  onOutpaint,
  onReusePrompt,
  onDelete
}) => {
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isUpscaling, setIsUpscaling] = useState(false);
  const [upscaleNotice, setUpscaleNotice] = useState<string | null>(null);

  const displayJob = currentJob || lastCompletedJob;
  const isGenerating = currentJob && currentJob.state === 'generating';

  // Preview image source: base64 preview while generating, or final output url
  let imageSrc: string | null = null;
  if (currentJob?.preview_base64) {
    imageSrc = `data:image/jpeg;base64,${currentJob.preview_base64}`;
  } else if (displayJob?.output_image_url) {
    imageSrc = `http://127.0.0.1:7860${displayJob.output_image_url}`;
  }

  const handleUpscale = async (scale: 2 | 4) => {
    if (!displayJob?.output_image_url || isUpscaling) return;
    try {
      setIsUpscaling(true);
      setUpscaleNotice(`Upscaling ${scale}x in progress...`);
      const res = await api.upscaleImage({
        image_url: displayJob.output_image_url,
        scale: scale
      });
      if (res.output_url) {
        displayJob.output_image_url = res.output_url;
        displayJob.width = res.width;
        displayJob.height = res.height;
        setUpscaleNotice(`Upscaled to ${res.width}x${res.height}!`);
        setTimeout(() => setUpscaleNotice(null), 4000);
      }
    } catch (err: any) {
      alert('Upscaling failed: ' + (err.message || err));
      setUpscaleNotice(null);
    } finally {
      setIsUpscaling(false);
    }
  };

  const handleDownload = () => {
    if (!imageSrc) return;
    const a = document.createElement('a');
    a.href = imageSrc;
    a.download = `antigravity_${displayJob?.id || Date.now()}.png`;
    a.click();
  };

  const handleCopyPrompt = () => {
    if (!displayJob?.prompt) return;
    navigator.clipboard.writeText(displayJob.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-panel" style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: 520,
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Viewport Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(8, 11, 17, 0.95)',
        position: 'relative',
        minHeight: 420
      }}>
        {imageSrc ? (
          <img
            src={imageSrc}
            alt="Generated Result"
            style={{
              maxWidth: '100%',
              maxHeight: '620px',
              objectFit: 'contain',
              borderRadius: 'var(--radius-md)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
              transition: 'opacity 0.2s'
            }}
          />
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1rem',
            color: 'var(--text-muted)'
          }}>
            <div style={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              border: '2px dashed var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Sparkles size={36} color="var(--border-subtle)" />
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Your canvas is empty
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Enter a prompt and press Generate to begin
              </div>
            </div>
          </div>
        )}

        {/* Live Progress Bar Overlay */}
        {currentJob && currentJob.state !== 'complete' && currentJob.state !== 'failed' && (
          <div style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'rgba(15, 21, 34, 0.9)',
            backdropFilter: 'blur(10px)',
            padding: '0.75rem 1.25rem',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.35rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
              <span style={{ fontWeight: 600, color: 'var(--primary-light)', textTransform: 'capitalize' }}>
                {currentJob.state.replace('_', ' ')}...
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                {currentJob.current_step} / {currentJob.total_steps} steps ({currentJob.progress}%)
              </span>
            </div>
            <div style={{
              width: '100%',
              height: 6,
              background: 'rgba(255,255,255,0.1)',
              borderRadius: 3,
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${currentJob.progress}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #6366f1, #d946ef)',
                transition: 'width 0.2s linear'
              }} />
            </div>
          </div>
        )}
      </div>

      {/* Telemetry Strip */}
      {displayJob && displayJob.metrics.total_time > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.5rem 1rem',
          background: 'var(--bg-surface-elevated)',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)'
        }}>
          <div>
            <span>Model: <strong>{displayJob.model.toUpperCase()}</strong></span>
            <span style={{ margin: '0 0.5rem' }}>•</span>
            <span>{displayJob.width}x{displayJob.height}</span>
            <span style={{ margin: '0 0.5rem' }}>•</span>
            <span>{displayJob.steps} steps</span>
          </div>
          <div>
            <span>Total: <strong>{displayJob.metrics.total_time}s</strong></span>
            <span style={{ margin: '0 0.5rem' }}>•</span>
            <span>Speed: {displayJob.metrics.images_per_minute} img/min</span>
            <span style={{ margin: '0 0.5rem' }}>•</span>
            <span>VRAM: {displayJob.metrics.peak_vram_mb} MB</span>
          </div>
        </div>
      )}

      {/* Action Toolbar */}
      {displayJob && imageSrc && (
        <div style={{
          padding: '0.75rem 1rem',
          background: 'var(--bg-surface)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.5rem'
        }}>
          {/* Creative Actions */}
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => onVary(displayJob)}
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
              title="Generate a subtle variation"
            >
              <RefreshCw size={14} />
              <span>Vary</span>
            </button>

            <button
              onClick={() => onEdit(imageSrc!, displayJob.prompt)}
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
              title="Send to Editor"
            >
              <Sliders size={14} />
              <span>Edit</span>
            </button>

            <button
              onClick={() => onInpaint(imageSrc!, displayJob.prompt)}
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
              title="Paint and modify a mask region"
            >
              <Brush size={14} />
              <span>Inpaint</span>
            </button>

            <button
              onClick={() => onOutpaint(imageSrc!, displayJob.prompt)}
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
              title="Extend canvas in any direction"
            >
              <Maximize2 size={14} />
              <span>Outpaint</span>
            </button>

            <button
              onClick={() => onReusePrompt(displayJob.prompt, displayJob.negative_prompt)}
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
              title="Copy prompt and settings to generator"
            >
              <Sparkles size={14} />
              <span>Reuse</span>
            </button>

            {/* High-Resolution Upscalers */}
            <button
              onClick={() => handleUpscale(2)}
              disabled={isUpscaling}
              className="btn btn-secondary"
              style={{
                padding: '0.4rem 0.75rem',
                fontSize: '0.8rem',
                borderColor: 'rgba(99, 102, 241, 0.4)',
                background: 'rgba(99, 102, 241, 0.1)',
                color: '#c7d2fe'
              }}
              title="2x High-Fidelity Upscale (Lanczos + Detail Enhancement)"
            >
              <Zap size={14} color="#818cf8" className={isUpscaling ? 'spin' : ''} />
              <span>{isUpscaling ? '2x...' : 'Upscale 2x'}</span>
            </button>

            <button
              onClick={() => handleUpscale(4)}
              disabled={isUpscaling}
              className="btn btn-secondary"
              style={{
                padding: '0.4rem 0.75rem',
                fontSize: '0.8rem',
                borderColor: 'rgba(217, 70, 239, 0.4)',
                background: 'rgba(217, 70, 239, 0.1)',
                color: '#f5d0fe'
              }}
              title="4x Ultra-Sharp 4K Upscale"
            >
              <Zap size={14} color="#d946ef" className={isUpscaling ? 'spin' : ''} />
              <span>{isUpscaling ? '4K...' : 'Upscale 4K'}</span>
            </button>

            {upscaleNotice && (
              <div style={{
                fontSize: '0.75rem',
                color: '#818cf8',
                display: 'flex',
                alignItems: 'center',
                padding: '0 0.5rem',
                fontWeight: 600
              }}>
                {upscaleNotice}
              </div>
            )}
          </div>

          {/* Utility Actions */}
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <button
              onClick={() => setShowInfoModal(true)}
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.65rem' }}
              title="View full generation telemetry & metadata"
            >
              <Info size={15} />
            </button>

            <button
              onClick={handleDownload}
              className="btn btn-primary"
              style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem' }}
              title="Download full PNG with embedded metadata"
            >
              <Download size={15} />
              <span>Download</span>
            </button>

            <button
              onClick={() => onDelete(displayJob.id)}
              className="btn btn-danger"
              style={{ padding: '0.4rem 0.65rem' }}
              title="Delete generation"
            >
              <Trash2 size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Info / Telemetry Modal */}
      {showInfoModal && displayJob && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(8, 11, 17, 0.95)',
          backdropFilter: 'blur(16px)',
          zIndex: 60,
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Generation Parameters & Telemetry</h3>
            <button
              onClick={() => setShowInfoModal(false)}
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.75rem' }}
            >
              Close
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: 2 }}>Prompt:</div>
              <div style={{ background: 'var(--bg-input)', padding: '0.65rem', borderRadius: 6 }}>
                {displayJob.prompt}
              </div>
            </div>

            {displayJob.enhanced_prompt && (
              <div>
                <div style={{ color: 'var(--accent-cyan)', fontSize: '0.75rem', marginBottom: 2 }}>
                  Enhanced Prompt (LM Studio / Prompt Intelligence):
                </div>
                <div style={{ background: 'rgba(6, 182, 212, 0.08)', padding: '0.65rem', borderRadius: 6, border: '1px solid rgba(6, 182, 212, 0.2)' }}>
                  {displayJob.enhanced_prompt}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.5rem' }}>
              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Model:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.model}</div>
              </div>
              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Dimensions:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.width} x {displayJob.height}</div>
              </div>
              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Steps:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.steps}</div>
              </div>
              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Guidance:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.guidance}</div>
              </div>
              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Seed:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.seed}</div>
              </div>
              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>VRAM Strategy:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.vram_strategy_used}</div>
              </div>
            </div>

            {/* Timings Breakdown */}
            <div style={{ marginTop: '0.5rem' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: 4 }}>
                Performance Timings:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.5rem', fontFamily: 'var(--font-mono)' }}>
                <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.45rem', borderRadius: 6 }}>
                  Load: {displayJob.metrics.model_load_time}s
                </div>
                <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.45rem', borderRadius: 6 }}>
                  Prompt: {displayJob.metrics.prompt_processing_time}s
                </div>
                <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.45rem', borderRadius: 6 }}>
                  Generation: {displayJob.metrics.generation_time}s
                </div>
                <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.45rem', borderRadius: 6 }}>
                  Save: {displayJob.metrics.save_time}s
                </div>
                <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.45rem', borderRadius: 6 }}>
                  Peak VRAM: {displayJob.metrics.peak_vram_mb} MB
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
