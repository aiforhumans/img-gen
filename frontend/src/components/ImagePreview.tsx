import React, { useState, useRef, useEffect } from 'react';
import {
  Download, Trash2, Sliders, Brush, Maximize2, RefreshCw,
  Sparkles, Info, Check, Copy, Zap, X
} from 'lucide-react';
import { GenerationJob } from '../types';
import { api } from '../services/api';

interface ImagePreviewProps {
  currentJob: GenerationJob | null;
  lastCompletedJob: GenerationJob | null;
  onVary: (job: GenerationJob) => void;
  onEdit?: (imageUrl: string, prompt: string) => void;
  onInpaint?: (imageUrl: string, prompt: string) => void;
  onOutpaint?: (imageUrl: string, prompt: string) => void;
  onReusePrompt: (prompt: string, negPrompt: string) => void;
  onReuseSettings?: (job: GenerationJob) => void;
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
  onReuseSettings,
  onDelete
}) => {
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isUpscaling, setIsUpscaling] = useState(false);
  const [upscaleNotice, setUpscaleNotice] = useState<string | null>(null);
  const [upscaledUrl, setUpscaledUrl] = useState<string | null>(null);

  // Output Window Height Resizing
  const [viewportHeight, setViewportHeight] = useState<number>(() => {
    const saved = localStorage.getItem('studio_preview_height');
    return saved ? parseInt(saved, 10) : 640;
  });
  const [isResizingHeight, setIsResizingHeight] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const startYRef = useRef<number>(0);
  const startHeightRef = useRef<number>(640);

  const displayJob = currentJob || lastCompletedJob;

  // Preview image source: base64 preview while generating, or final output url
  let imageSrc: string | null = null;
  if (currentJob?.preview_base64) {
    imageSrc = `data:image/jpeg;base64,${currentJob.preview_base64}`;
  } else if (upscaledUrl) {
    imageSrc = `http://127.0.0.1:7860${upscaledUrl}`;
  } else if (displayJob?.output_image_url) {
    imageSrc = `http://127.0.0.1:7860${displayJob.output_image_url}`;
  }

  // Handle Height Resizing Drag
  const handleStartHeightResize = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizingHeight(true);
    startYRef.current = e.clientY;
    startHeightRef.current = viewportHeight === -1 ? window.innerHeight - 240 : viewportHeight;
  };

  useEffect(() => {
    if (!isResizingHeight) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaY = e.clientY - startYRef.current;
      const newHeight = Math.max(360, Math.min(1300, startHeightRef.current + deltaY));
      setViewportHeight(newHeight);
      localStorage.setItem('studio_preview_height', newHeight.toString());
    };

    const handleMouseUp = () => {
      setIsResizingHeight(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingHeight]);

  // Handle Escape Key for Lightbox
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsFullscreen(false);
        setShowInfoModal(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Reset upscaled URL whenever active generation changes
  useEffect(() => {
    setUpscaledUrl(null);
    setUpscaleNotice(null);
  }, [displayJob?.id]);

  const handleUpscale = async (scale: 2 | 4) => {
    const activeUrl = upscaledUrl || displayJob?.output_image_url;
    const activePath = displayJob?.output_image_path;
    if ((!activeUrl && !activePath) || isUpscaling) return;

    try {
      setIsUpscaling(true);
      setUpscaleNotice(`Upscaling ${scale}x in progress...`);
      const res = await api.upscaleImage({
        image_url: activeUrl || undefined,
        image_path: activePath || undefined,
        scale: scale
      });
      if (res.output_url) {
        setUpscaledUrl(res.output_url);
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

  const currentHeightStyle = viewportHeight === -1 ? 'calc(100vh - 220px)' : `${viewportHeight}px`;

  return (
    <div className="glass-panel" style={{
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      overflow: 'hidden',
      userSelect: isResizingHeight ? 'none' : 'auto'
    }}>
      {/* Output Window Header with Quick Size Selector & Maximize */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.65rem 1rem',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'rgba(15, 21, 34, 0.6)',
        fontSize: '0.8rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontWeight: 700, color: 'var(--text-secondary)' }}>OUTPUT WINDOW</span>
          {displayJob?.width && displayJob?.height && (
            <span className="badge badge-indigo" style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}>
              {displayJob.width} × {displayJob.height}
            </span>
          )}
        </div>

        {/* Size Presets & Fullscreen */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Height:</span>
          <div className="pill-group" style={{ background: 'rgba(0,0,0,0.3)', padding: 2 }}>
            {[
              { label: 'S', h: 480, title: 'Compact (480px)' },
              { label: 'M', h: 640, title: 'Default (640px)' },
              { label: 'L', h: 840, title: 'Large (840px)' },
              { label: 'Fit', h: -1, title: 'Fit Screen Height' }
            ].map((preset) => (
              <button
                key={preset.label}
                type="button"
                className={`pill-btn ${viewportHeight === preset.h ? 'active' : ''}`}
                onClick={() => {
                  setViewportHeight(preset.h);
                  localStorage.setItem('studio_preview_height', preset.h.toString());
                }}
                title={preset.title}
                style={{ padding: '0.15rem 0.5rem', fontSize: '0.7rem' }}
              >
                {preset.label}
              </button>
            ))}
          </div>

          {/* Fullscreen Lightbox Button */}
          {imageSrc && (
            <button
              onClick={() => setIsFullscreen(true)}
              className="btn btn-secondary"
              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 4 }}
              title="Full-Screen Lightbox View"
            >
              <Maximize2 size={13} />
              <span>Fullscreen</span>
            </button>
          )}
        </div>
      </div>

      {/* Viewport Area */}
      <div style={{
        height: currentHeightStyle,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(8, 11, 17, 0.95)',
        position: 'relative',
        overflow: 'hidden',
        padding: '0.75rem'
      }}>
        {imageSrc ? (
          <img
            src={imageSrc}
            alt="Generated Result"
            onClick={() => setIsFullscreen(true)}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
              borderRadius: 'var(--radius-md)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
              cursor: 'zoom-in',
              transition: 'transform 0.15s ease'
            }}
            title="Click to view full screen"
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
              background: 'var(--bg-input)',
              borderRadius: 3,
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${currentJob.progress}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #6366f1, #d946ef)',
                transition: 'width 0.15s ease'
              }} />
            </div>
          </div>
        )}
      </div>

      {/* Draggable Vertical Resize Bar */}
      <div
        onMouseDown={handleStartHeightResize}
        onDoubleClick={() => {
          setViewportHeight(640);
          localStorage.setItem('studio_preview_height', '640');
        }}
        title="Drag up/down to resize output window height (double-click to reset 640px)"
        style={{
          height: 14,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'row-resize',
          background: isResizingHeight ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.02)',
          borderTop: '1px solid var(--border-subtle)',
          borderBottom: '1px solid var(--border-subtle)',
          userSelect: 'none'
        }}
      >
        <div style={{
          width: 50,
          height: 3,
          borderRadius: 2,
          background: isResizingHeight ? 'var(--primary)' : 'rgba(255, 255, 255, 0.25)',
          boxShadow: isResizingHeight ? '0 0 8px var(--primary-glow)' : 'none',
          transition: 'background 0.2s, box-shadow 0.2s'
        }} />
      </div>

      {/* Action Toolbar */}
      {displayJob && imageSrc && (
        <div style={{
          padding: '0.75rem 1rem',
          borderTop: '1px solid var(--border-subtle)',
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

            {onEdit && (
              <button
                onClick={() => onEdit(imageSrc!, displayJob.prompt)}
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                title="Send to Editor"
              >
                <Sliders size={14} />
                <span>Edit</span>
              </button>
            )}

            {onInpaint && (
              <button
                onClick={() => onInpaint(imageSrc!, displayJob.prompt)}
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                title="Paint and modify a mask region"
              >
                <Brush size={14} />
                <span>Inpaint</span>
              </button>
            )}

            {onOutpaint && (
              <button
                onClick={() => onOutpaint(imageSrc!, displayJob.prompt)}
                className="btn btn-secondary"
                style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                title="Extend canvas in any direction"
              >
                <Maximize2 size={14} />
                <span>Outpaint</span>
              </button>
            )}

            <button
              onClick={() => {
                if (onReuseSettings) {
                  onReuseSettings(displayJob);
                } else {
                  onReusePrompt(displayJob.prompt, displayJob.negative_prompt);
                }
              }}
              className="btn btn-secondary"
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
              title="Copy prompt and full settings to generator"
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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Prompt:</span>
                <button
                  onClick={handleCopyPrompt}
                  className="btn btn-secondary"
                  style={{ padding: '0.15rem 0.45rem', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  {copied ? <Check size={11} color="#10b981" /> : <Copy size={11} />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <div style={{ background: 'var(--bg-input)', padding: '0.65rem', borderRadius: 6 }}>
                {displayJob.prompt}
              </div>
            </div>

            {displayJob.enhanced_prompt && (
              <div>
                <div style={{ color: 'var(--accent-cyan)', fontSize: '0.75rem', marginBottom: 2 }}>
                  Enhanced Prompt:
                </div>
                <div style={{ background: 'rgba(6, 182, 212, 0.08)', padding: '0.65rem', borderRadius: 6, border: '1px solid rgba(6, 182, 212, 0.2)' }}>
                  {displayJob.enhanced_prompt}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.5rem' }}>
              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Model:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.model.toUpperCase()}</div>
              </div>

              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Seed:</span>
                <div style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{displayJob.seed}</div>
              </div>

              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Resolution:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.width} × {displayJob.height}</div>
              </div>

              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Steps / CFG:</span>
                <div style={{ fontWeight: 600 }}>{displayJob.steps} steps / {displayJob.guidance}</div>
              </div>

              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Total Time:</span>
                <div style={{ fontWeight: 600, color: 'var(--primary-light)' }}>
                  {displayJob.metrics?.total_time || 0}s
                </div>
              </div>

              <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Peak VRAM:</span>
                <div style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>
                  {displayJob.metrics?.peak_vram_mb || 0} MB
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Full-Screen Lightbox Modal */}
      {isFullscreen && imageSrc && (
        <div
          onClick={() => setIsFullscreen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(5, 8, 14, 0.96)',
            backdropFilter: 'blur(20px)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem',
            animation: 'fadeIn 0.2s ease',
            cursor: 'zoom-out'
          }}
        >
          {/* Top Bar inside Lightbox */}
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              position: 'absolute',
              top: '1.5rem',
              right: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              cursor: 'default'
            }}
          >
            <button
              onClick={handleDownload}
              className="btn btn-primary"
              style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem' }}
            >
              <Download size={15} />
              <span>Download</span>
            </button>
            <button
              onClick={() => setIsFullscreen(false)}
              className="btn btn-secondary"
              style={{ padding: '0.45rem 0.65rem' }}
              title="Close (or press Esc)"
            >
              <X size={18} />
            </button>
          </div>

          <img
            src={imageSrc}
            alt="Fullscreen Preview"
            onClick={(e) => e.stopPropagation()}
            style={{
              maxWidth: '96vw',
              maxHeight: '94vh',
              objectFit: 'contain',
              borderRadius: 'var(--radius-md)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.9)',
              cursor: 'default'
            }}
          />
        </div>
      )}
    </div>
  );
};
