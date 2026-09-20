import React, { useState, useRef, useCallback } from 'react';
import {
  Image as ImageIcon, X, ChevronDown, ChevronUp,
  Download, Palette, User, Plus, Minus
} from 'lucide-react';
import { api } from '../services/api';

export interface ReferenceImageState {
  path: string;
  thumbnailBase64: string;
  mode: 'style' | 'subject';
  strength: number;
  width: number;
  height: number;
}

interface ReferenceImagePanelProps {
  reference1: ReferenceImageState | null;
  setReference1: (ref: ReferenceImageState | null) => void;
  reference2: ReferenceImageState | null;
  setReference2: (ref: ReferenceImageState | null) => void;
}

function getStrengthLabel(strength: number): string {
  if (strength <= 0.35) return 'Subtle';
  if (strength <= 0.7) return 'Balanced (Recommended)';
  if (strength <= 1.0) return 'Strong Likeness';
  return 'Dominant';
}

function getStrengthColor(strength: number): string {
  if (strength <= 0.3) return 'var(--accent-cyan)';
  if (strength <= 0.7) return 'var(--accent-emerald)';
  if (strength <= 1.0) return 'var(--accent-amber)';
  return 'var(--accent-rose)';
}

export const ReferenceImagePanel: React.FC<ReferenceImagePanelProps> = ({
  reference1,
  setReference1,
  reference2,
  setReference2
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isEnabled, setIsEnabled] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadTarget, setUploadTarget] = useState<1 | 2>(1);
  const [showSecondRef, setShowSecondRef] = useState(false);
  const [ipStatus, setIpStatus] = useState<{
    style_weights_available: boolean;
    subject_weights_available: boolean;
    downloading: boolean;
    download_progress: number;
  } | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasAnyReference = reference1 !== null;

  // Toggle the reference image feature on/off
  const handleToggle = useCallback(async () => {
    const newEnabled = !isEnabled;
    setIsEnabled(newEnabled);

    if (newEnabled) {
      setIsOpen(true);
      // Check IP-Adapter status
      try {
        const status = await api.getIPAdapterStatus();
        setIpStatus(status);
      } catch {
        // Silently handle — status check is informational
      }
    } else {
      // Clear references when disabled
      setReference1(null);
      setReference2(null);
      setShowSecondRef(false);
    }
  }, [isEnabled, setReference1, setReference2]);

  // Handle file upload
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const result = await api.uploadReferenceImage(file);
      const target = uploadTarget;
      const defaultMode = target === 2 && reference1 ? (reference1.mode === 'style' ? 'subject' : 'style') : 'style';

      const refState: ReferenceImageState = {
        path: result.path,
        thumbnailBase64: result.thumbnail_base64,
        mode: defaultMode,
        strength: 0.6,
        width: result.width,
        height: result.height
      };

      if (target === 1) {
        setReference1(refState);
      } else {
        setReference2(refState);
      }
    } catch (err: any) {
      console.error('Upload failed:', err);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, [uploadTarget, reference1, setReference1, setReference2]);

  // Handle drag & drop
  const handleDrop = useCallback(async (e: React.DragEvent, target: 1 | 2) => {
    e.preventDefault();
    e.stopPropagation();

    const file = e.dataTransfer.files?.[0];
    if (!file || !file.type.startsWith('image/')) return;

    setIsUploading(true);
    try {
      const result = await api.uploadReferenceImage(file);
      const defaultMode = target === 2 && reference1 ? (reference1.mode === 'style' ? 'subject' : 'style') : 'style';

      const refState: ReferenceImageState = {
        path: result.path,
        thumbnailBase64: result.thumbnail_base64,
        mode: defaultMode,
        strength: 0.6,
        width: result.width,
        height: result.height
      };

      if (target === 1) {
        setReference1(refState);
      } else {
        setReference2(refState);
      }
    } catch (err: any) {
      console.error('Drop upload failed:', err);
    } finally {
      setIsUploading(false);
    }
  }, [reference1, setReference1, setReference2]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  // Download IP-Adapter weights
  const _handleDownloadWeights = useCallback(async (mode: string) => {
    setIsDownloading(true);
    try {
      await api.downloadIPAdapterWeights(mode);
      // Poll status until done
      const poll = setInterval(async () => {
        try {
          const status = await api.getIPAdapterStatus();
          setIpStatus(status);
          if (!status.downloading) {
            clearInterval(poll);
            setIsDownloading(false);
          }
        } catch {
          clearInterval(poll);
          setIsDownloading(false);
        }
      }, 2000);
    } catch {
      setIsDownloading(false);
    }
  }, []);

  // Render a single reference image slot
  const renderRefSlot = (
    ref: ReferenceImageState | null,
    setRef: (r: ReferenceImageState | null) => void,
    target: 1 | 2,
    label: string
  ) => (
    <div style={{
      background: 'var(--bg-input)',
      borderRadius: 'var(--radius-md)',
      border: '1px solid var(--border-subtle)',
      padding: '0.75rem',
      animation: 'fadeIn 0.3s ease'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '0.6rem'
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {label}
        </span>
        {ref && (
          <button
            onClick={() => setRef(null)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '2px',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center'
            }}
            title="Remove reference image"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {!ref ? (
        /* Drop zone */
        <div
          onDrop={(e) => handleDrop(e, target)}
          onDragOver={handleDragOver}
          onClick={() => {
            setUploadTarget(target);
            fileInputRef.current?.click();
          }}
          style={{
            border: '2px dashed var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '1.25rem 1rem',
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            minHeight: 80,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.4rem'
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--primary)';
            (e.currentTarget as HTMLElement).style.background = 'rgba(99, 102, 241, 0.05)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-subtle)';
            (e.currentTarget as HTMLElement).style.background = 'transparent';
          }}
        >
          {isUploading ? (
            <div className="spin" style={{ color: 'var(--primary)' }}>
              <ImageIcon size={20} />
            </div>
          ) : (
            <>
              <ImageIcon size={20} color="var(--text-muted)" />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Drop image or click to upload
              </span>
            </>
          )}
        </div>
      ) : (
        /* Uploaded reference preview + controls */
        <div>
          {/* Thumbnail */}
          <div style={{
            position: 'relative',
            borderRadius: 'var(--radius-sm)',
            overflow: 'hidden',
            marginBottom: '0.6rem',
            aspectRatio: '16/10',
            background: 'var(--bg-base)'
          }}>
            <img
              src={`data:image/jpeg;base64,${ref.thumbnailBase64}`}
              alt="Reference"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                display: 'block'
              }}
            />
            <div style={{
              position: 'absolute',
              bottom: 4,
              right: 4,
              fontSize: '0.65rem',
              padding: '1px 5px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(0,0,0,0.65)',
              color: '#ccc'
            }}>
              {ref.width}×{ref.height}
            </div>
          </div>

          {/* Mode Selector: Style vs Subject */}
          <div style={{ marginBottom: '0.6rem' }}>
            <div className="pill-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, width: '100%' }}>
              <button
                className={`pill-btn ${ref.mode === 'style' ? 'active' : ''}`}
                onClick={() => setRef({ ...ref, mode: 'style' })}
                style={{ fontSize: '0.72rem', padding: '0.3rem 0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem' }}
              >
                <Palette size={12} />
                Style
              </button>
              <button
                className={`pill-btn ${ref.mode === 'subject' ? 'active' : ''}`}
                onClick={() => setRef({ ...ref, mode: 'subject' })}
                style={{ fontSize: '0.72rem', padding: '0.3rem 0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.3rem' }}
              >
                <User size={12} />
                Subject
              </button>
            </div>
            <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', marginTop: '0.35rem', lineHeight: 1.35 }}>
              {ref.mode === 'subject' ? (
                <span>👤 <strong>Subject:</strong> Injects face & identity. The prompt sets the pose & framing (e.g. <em>"full body shot"</em>).</span>
              ) : (
                <span>🎨 <strong>Style:</strong> Transfers colors, lighting, mood, and aesthetic across the scene.</span>
              )}
            </div>
          </div>

          {/* Strength Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                Influence:
              </span>
              <span style={{
                fontSize: '0.68rem',
                fontWeight: 700,
                color: getStrengthColor(ref.strength)
              }}>
                {Math.round(ref.strength * 100)}% — {getStrengthLabel(ref.strength)}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={1.5}
              step={0.05}
              value={ref.strength}
              onChange={(e) => setRef({ ...ref, strength: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: getStrengthColor(ref.strength) }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: 2 }}>
              <span>Prompt controls pose</span>
              <span>50-70% ideal</span>
              <span>Strong likeness</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="glass-panel" style={{
      padding: '1rem 1.25rem',
      marginTop: '0.75rem',
      transition: 'all 0.25s ease'
    }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          userSelect: 'none'
        }}
        onClick={() => {
          if (!isEnabled) {
            handleToggle();
          } else {
            setIsOpen(!isOpen);
          }
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ImageIcon size={16} color={isEnabled ? 'var(--primary-light)' : 'var(--text-muted)'} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Reference Image</span>
          {hasAnyReference && (
            <span className="badge badge-indigo" style={{ fontSize: '0.65rem' }}>
              {reference2 ? '2 refs' : reference1?.mode === 'style' ? 'Style' : 'Subject'}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          {/* Toggle Switch */}
          <div
            onClick={(e) => {
              e.stopPropagation();
              handleToggle();
            }}
            style={{
              width: 36,
              height: 20,
              borderRadius: 10,
              background: isEnabled
                ? 'linear-gradient(135deg, var(--primary) 0%, #8b5cf6 100%)'
                : 'var(--bg-surface-hover)',
              cursor: 'pointer',
              position: 'relative',
              transition: 'background 0.25s ease',
              border: '1px solid ' + (isEnabled ? 'transparent' : 'var(--border-subtle)')
            }}
          >
            <div style={{
              width: 16,
              height: 16,
              borderRadius: '50%',
              background: '#fff',
              position: 'absolute',
              top: 1,
              left: isEnabled ? 18 : 1,
              transition: 'left 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              boxShadow: '0 1px 4px rgba(0,0,0,0.3)'
            }} />
          </div>

          {isEnabled && (isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />)}
        </div>
      </div>

      {/* Expanded Content */}
      {isEnabled && isOpen && (
        <div style={{
          marginTop: '1rem',
          paddingTop: '0.75rem',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
          animation: 'fadeIn 0.3s ease'
        }}>
          {/* Download indicator if weights are missing */}
          {ipStatus && !ipStatus.style_weights_available && !ipStatus.subject_weights_available && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.6rem 0.8rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              fontSize: '0.75rem',
              color: 'var(--primary-light)'
            }}>
              <Download size={14} />
              <div style={{ flex: 1 }}>
                {isDownloading ? (
                  <span>Downloading IP-Adapter weights... {Math.round((ipStatus.download_progress || 0) * 100)}%</span>
                ) : (
                  <span>IP-Adapter weights will be downloaded automatically when you add a reference image (~2GB one-time download).</span>
                )}
              </div>
              {isDownloading && (
                <div style={{
                  width: '100%',
                  height: 3,
                  background: 'var(--bg-surface)',
                  borderRadius: 2,
                  overflow: 'hidden',
                  marginTop: 4
                }}>
                  <div style={{
                    width: `${(ipStatus.download_progress || 0) * 100}%`,
                    height: '100%',
                    background: 'var(--primary)',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              )}
            </div>
          )}

          {/* Primary Reference Slot */}
          {renderRefSlot(reference1, setReference1, 1, 'Reference 1')}

          {/* Second Reference Toggle */}
          {reference1 && !showSecondRef && (
            <button
              onClick={() => setShowSecondRef(true)}
              className="btn btn-secondary"
              style={{
                fontSize: '0.72rem',
                padding: '0.35rem 0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                alignSelf: 'flex-start'
              }}
            >
              <Plus size={12} />
              Add second reference
            </button>
          )}

          {/* Second Reference Slot */}
          {showSecondRef && (
            <div>
              {renderRefSlot(reference2, setReference2, 2, 'Reference 2')}
              <button
                onClick={() => {
                  setReference2(null);
                  setShowSecondRef(false);
                }}
                className="btn btn-secondary"
                style={{
                  fontSize: '0.68rem',
                  padding: '0.25rem 0.6rem',
                  marginTop: '0.4rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.3rem'
                }}
              >
                <Minus size={11} />
                Remove second reference
              </button>
            </div>
          )}

          {/* IP-Adapter mode description */}
          {reference1 && (
            <div style={{
              fontSize: '0.68rem',
              color: 'var(--text-muted)',
              lineHeight: 1.5,
              padding: '0.3rem 0'
            }}>
              {reference1.mode === 'style' ? (
                <>💫 <strong>Style mode</strong>: Adopts the reference's aesthetic, color palette, and mood. Content is generated independently.</>
              ) : (
                <>👤 <strong>Subject mode</strong>: Extracts the face/object from the reference and places it into the generated scene.</>
              )}
            </div>
          )}
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />
    </div>
  );
};
