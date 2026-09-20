import React, { useState } from 'react';
import {
  X, Sparkles, Download, Zap,
  Layers, UserCheck
} from 'lucide-react';
import { api } from '../services/api';
import { UpscaleEngineType, UpscaleResult } from '../types';

interface SuperResolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string;
  imagePath?: string;
  prompt?: string;
  originalWidth?: number;
  originalHeight?: number;
  onUpscaleComplete?: (result: UpscaleResult) => void;
}

export const SuperResolutionModal: React.FC<SuperResolutionModalProps> = ({
  isOpen,
  onClose,
  imageUrl,
  imagePath,
  prompt,
  originalWidth = 1024,
  originalHeight = 1024,
  onUpscaleComplete
}) => {
  const [scale, setScale] = useState<number>(2);
  const [engine, setEngine] = useState<UpscaleEngineType>('realesrgan_photo');
  const [enableFaceRestore, setEnableFaceRestore] = useState<boolean>(true);
  const [faceFidelity, setFaceFidelity] = useState<number>(0.7);
  const [enableDiffusionRefine, setEnableDiffusionRefine] = useState<boolean>(false);
  const [diffusionDenoise, setDiffusionDenoise] = useState<number>(0.25);

  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [result, setResult] = useState<UpscaleResult | null>(null);

  // Before/After comparison slider state (0 to 100 percentage)
  const [sliderPos, setSliderPos] = useState<number>(50);

  if (!isOpen) return null;

  const targetWidth = originalWidth * scale;
  const targetHeight = originalHeight * scale;

  const handleEnhance = async () => {
    setIsProcessing(true);
    setStatusMessage('Initializing neural engine on RTX 5080...');
    try {
      if (engine !== 'classic_lanczos') {
        setStatusMessage('Running Real-ESRGAN super-resolution pass...');
      } else {
        setStatusMessage('Running Lanczos resampling pass...');
      }

      const res = await api.upscaleImage({
        image_url: imageUrl,
        image_path: imagePath,
        scale,
        engine,
        enable_face_restore: enableFaceRestore,
        face_fidelity: faceFidelity,
        enable_diffusion_refine: enableDiffusionRefine,
        diffusion_denoise: diffusionDenoise,
        prompt
      });

      setResult(res);
      setStatusMessage('Enhancement complete!');
      if (onUpscaleComplete) {
        onUpscaleComplete(res);
      }
    } catch (err: any) {
      alert(`Upscaling failed: ${err.message || err}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const enhancedUrl = result ? `http://127.0.0.1:7860${result.output_url}` : null;
  const downloadFileName = result?.output_path
    ? result.output_path.split(/[\\/]/).pop()
    : `enhanced_${scale}x_image.png`;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(5, 8, 15, 0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
        animation: 'fadeIn 0.2s ease'
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: 1160,
          height: '86vh',
          maxHeight: 840,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid var(--border-subtle)',
          boxShadow: '0 25px 80px rgba(0, 0, 0, 0.85)',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem 1.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'rgba(11, 16, 26, 0.8)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(217, 70, 239, 0.2) 100%)',
                border: '1px solid rgba(99, 102, 241, 0.35)',
                color: 'var(--primary-light)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <Sparkles size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h2 style={{ fontSize: '1.05rem', fontWeight: 700, letterSpacing: '-0.01em', margin: 0 }}>
                  AI Latent Super-Resolution & Detailer
                </h2>
                <span className="badge badge-emerald" style={{ fontSize: '0.68rem', padding: '0.15rem 0.5rem' }}>
                  RTX 5080 Blackwell
                </span>
              </div>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
                PyTorch 2.14+cu130 • Real-ESRGAN • CodeFormer Face Restoration • Tiled 4K
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="btn btn-secondary"
            style={{ padding: '0.4rem 0.6rem' }}
            title="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Layout */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
          {/* Visual Comparison / Preview Area */}
          <div
            style={{
              flex: 1,
              background: 'rgba(8, 11, 17, 0.9)',
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '1.25rem',
              overflow: 'hidden',
              userSelect: 'none'
            }}
          >
            {enhancedUrl ? (
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  height: '100%',
                  maxWidth: 780,
                  maxHeight: '70vh',
                  borderRadius: 'var(--radius-md)',
                  overflow: 'hidden',
                  border: '1px solid var(--border-subtle)',
                  background: '#000',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 12px 40px rgba(0,0,0,0.6)'
                }}
              >
                {/* Enhanced Image (Base) */}
                <img
                  src={enhancedUrl}
                  alt="AI Enhanced"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
                    pointerEvents: 'none'
                  }}
                />

                {/* Original Image (Clipped Left Layer) */}
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    overflow: 'hidden',
                    pointerEvents: 'none',
                    clipPath: `inset(0 ${100 - sliderPos}% 0 0)`
                  }}
                >
                  <img
                    src={imageUrl}
                    alt="Original"
                    style={{
                      position: 'absolute',
                      inset: 0,
                      width: '100%',
                      height: '100%',
                      objectFit: 'contain'
                    }}
                  />
                </div>

                {/* Vertical Divider Line */}
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    bottom: 0,
                    left: `${sliderPos}%`,
                    width: 2,
                    background: 'var(--primary-light)',
                    boxShadow: '0 0 12px var(--primary-glow)',
                    zIndex: 10,
                    pointerEvents: 'none',
                    transform: 'translateX(-50%)'
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      background: 'var(--primary)',
                      border: '2px solid #ffffff',
                      boxShadow: '0 2px 10px rgba(0,0,0,0.6)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#ffffff',
                      fontSize: '0.75rem',
                      fontWeight: 'bold'
                    }}
                  >
                    ↔
                  </div>
                </div>

                {/* Interactive Slider Track Input */}
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={sliderPos}
                  onChange={(e) => setSliderPos(Number(e.target.value))}
                  style={{
                    position: 'absolute',
                    inset: 0,
                    opacity: 0,
                    cursor: 'ew-resize',
                    zIndex: 20,
                    width: '100%',
                    height: '100%',
                    margin: 0
                  }}
                  title="Drag left/right to compare Original vs Enhanced"
                />

                {/* Badges */}
                <div
                  style={{
                    position: 'absolute',
                    top: 12,
                    left: 12,
                    zIndex: 30,
                    padding: '0.25rem 0.6rem',
                    borderRadius: 6,
                    background: 'rgba(0, 0, 0, 0.75)',
                    backdropFilter: 'blur(8px)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)'
                  }}
                >
                  Original ({originalWidth}×{originalHeight})
                </div>

                <div
                  style={{
                    position: 'absolute',
                    top: 12,
                    right: 12,
                    zIndex: 30,
                    padding: '0.25rem 0.6rem',
                    borderRadius: 6,
                    background: 'rgba(99, 102, 241, 0.25)',
                    backdropFilter: 'blur(8px)',
                    border: '1px solid rgba(99, 102, 241, 0.5)',
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    color: '#e0e7ff'
                  }}
                >
                  AI Enhanced ({result?.width}×{result?.height})
                </div>
              </div>
            ) : (
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  height: '100%',
                  maxWidth: 780,
                  maxHeight: '70vh',
                  borderRadius: 'var(--radius-md)',
                  overflow: 'hidden',
                  border: '1px solid var(--border-subtle)',
                  background: '#000',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 12px 40px rgba(0,0,0,0.6)'
                }}
              >
                <img
                  src={imageUrl}
                  alt="Original Preview"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain'
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    top: 12,
                    left: 12,
                    padding: '0.25rem 0.6rem',
                    borderRadius: 6,
                    background: 'rgba(0, 0, 0, 0.75)',
                    backdropFilter: 'blur(8px)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)'
                  }}
                >
                  Ready to Enhance • {originalWidth}×{originalHeight}
                </div>
              </div>
            )}

            {/* In-Progress Loading Overlay */}
            {isProcessing && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'rgba(5, 7, 12, 0.8)',
                  backdropFilter: 'blur(10px)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 40,
                  gap: '1rem'
                }}
              >
                <div
                  className="spin"
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: '50%',
                    border: '3px solid rgba(99, 102, 241, 0.2)',
                    borderTopColor: 'var(--primary)'
                  }}
                />
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {statusMessage}
                  </p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    Processing on RTX 5080 (Blackwell 16GB)
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Right Parameters Drawer */}
          <div
            style={{
              width: 330,
              borderLeft: '1px solid var(--border-subtle)',
              background: 'rgba(11, 16, 26, 0.95)',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              overflowY: 'auto',
              gap: '1.25rem'
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Target Resolution */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    Target Resolution:
                  </label>
                  <span style={{ fontSize: '0.75rem', color: 'var(--primary-light)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                    {targetWidth} × {targetHeight} ({scale}x)
                  </span>
                </div>
                <div className="pill-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', width: '100%', gap: 4 }}>
                  <button
                    type="button"
                    onClick={() => setScale(2)}
                    className={`pill-btn ${scale === 2 ? 'active' : ''}`}
                    style={{ padding: '0.45rem', fontSize: '0.78rem' }}
                  >
                    2x Super-Sample
                  </button>
                  <button
                    type="button"
                    onClick={() => setScale(4)}
                    className={`pill-btn ${scale === 4 ? 'active' : ''}`}
                    style={{ padding: '0.45rem', fontSize: '0.78rem' }}
                  >
                    4x Ultra 4K
                  </button>
                </div>
              </div>

              {/* Neural Model Engine */}
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <Layers size={14} color="var(--primary)" />
                  Neural Model Engine:
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {[
                    { id: 'realesrgan_photo', label: 'Real-ESRGAN Photo', desc: 'Optimal for photorealism, skin, nature' },
                    { id: 'realesrgan_anime', label: 'Real-ESRGAN Anime 6B', desc: 'Tuned for illustration, 2D art, anime' },
                    { id: 'classic_lanczos', label: 'Classic Lanczos', desc: 'Fast mathematical interpolation' }
                  ].map((eng) => (
                    <button
                      key={eng.id}
                      type="button"
                      onClick={() => setEngine(eng.id as UpscaleEngineType)}
                      style={{
                        padding: '0.55rem 0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        textAlign: 'left',
                        border: engine === eng.id ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
                        background: engine === eng.id ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-surface)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ fontSize: '0.78rem', fontWeight: 600, color: engine === eng.id ? '#ffffff' : 'var(--text-primary)' }}>
                        {eng.label}
                      </div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 2 }}>
                        {eng.desc}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Face Restoration (CodeFormer) */}
              <div
                style={{
                  padding: '0.85rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <label
                    style={{
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      cursor: 'pointer'
                    }}
                    onClick={() => setEnableFaceRestore(!enableFaceRestore)}
                  >
                    <UserCheck size={15} color="#818cf8" />
                    Face Restoration (CodeFormer)
                  </label>
                  <input
                    type="checkbox"
                    checked={enableFaceRestore}
                    onChange={(e) => setEnableFaceRestore(e.target.checked)}
                    style={{ cursor: 'pointer', width: 16, height: 16, accentColor: 'var(--primary)' }}
                  />
                </div>

                {enableFaceRestore && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      <span>Identity Fidelity:</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--primary-light)', fontWeight: 600 }}>
                        {faceFidelity.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      value={faceFidelity}
                      onChange={(e) => setFaceFidelity(parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: 'var(--primary)', cursor: 'pointer' }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      <span>Max Enhance (0.1)</span>
                      <span>Balanced (0.7)</span>
                      <span>Strict (1.0)</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Generative Texture Refinement */}
              <div
                style={{
                  padding: '0.85rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <label
                    style={{
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      cursor: 'pointer'
                    }}
                    onClick={() => setEnableDiffusionRefine(!enableDiffusionRefine)}
                  >
                    <Zap size={15} color="#d946ef" />
                    Texture Refinement (Diffusion)
                  </label>
                  <input
                    type="checkbox"
                    checked={enableDiffusionRefine}
                    onChange={(e) => setEnableDiffusionRefine(e.target.checked)}
                    style={{ cursor: 'pointer', width: 16, height: 16, accentColor: '#d946ef' }}
                  />
                </div>

                {enableDiffusionRefine && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      <span>Denoise Strength:</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: '#f5d0fe', fontWeight: 600 }}>
                        {diffusionDenoise.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.1"
                      max="0.45"
                      step="0.02"
                      value={diffusionDenoise}
                      onChange={(e) => setDiffusionDenoise(parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: '#d946ef', cursor: 'pointer' }}
                    />
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      Re-synthesizes micro-skin and fabric textures without altering geometry.
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Actions */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginTop: '0.5rem' }}>
              <button
                type="button"
                onClick={handleEnhance}
                disabled={isProcessing}
                className="btn btn-generate"
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8
                }}
              >
                {isProcessing ? (
                  <>
                    <div className="spin" style={{ width: 16, height: 16, border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%' }} />
                    <span>Processing ({scale}x)...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>Enhance Image ({scale}x)</span>
                  </>
                )}
              </button>

              {result && (
                <a
                  href={enhancedUrl || '#'}
                  download={downloadFileName}
                  className="btn btn-secondary"
                  style={{
                    width: '100%',
                    padding: '0.55rem 1rem',
                    fontSize: '0.8rem',
                    textDecoration: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    border: '1px solid rgba(99, 102, 241, 0.4)'
                  }}
                >
                  <Download size={14} color="var(--primary-light)" />
                  <span>Save Enhanced PNG ({result.width}×{result.height})</span>
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
