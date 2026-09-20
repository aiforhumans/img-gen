import React, { useState } from 'react';
import {
  Upload, Wand2, Brush, Maximize2, Sparkles,
  Sliders, Eye
} from 'lucide-react';
import { InpaintCanvas } from '../components/InpaintCanvas';
import { OutpaintControls } from '../components/OutpaintControls';
import { api } from '../services/api';

interface EditPageProps {
  initialImageSrc?: string;
  initialPrompt?: string;
  onGenerationComplete: () => void;
}

export const EditPage: React.FC<EditPageProps> = ({
  initialImageSrc,
  initialPrompt = '',
  onGenerationComplete
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'inpaint' | 'outpaint' | 'img2img' | 'instruct'>('inpaint');
  const [imageSrc, setImageSrc] = useState<string>(initialImageSrc || '');
  const [maskBase64, setMaskBase64] = useState<string>('');
  const [prompt, setPrompt] = useState<string>(initialPrompt);
  const [strength, setStrength] = useState<number>(0.7);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [resultImageSrc, setResultImageSrc] = useState<string | null>(null);

  // Outpaint state
  const [expandLeft, setExpandLeft] = useState<number>(0);
  const [expandRight, setExpandRight] = useState<number>(0);
  const [expandTop, setExpandTop] = useState<number>(0);
  const [expandBottom, setExpandBottom] = useState<number>(0);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        setImageSrc(reader.result as string);
        setResultImageSrc(null);
      };
      reader.readAsDataURL(file);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          const reader = new FileReader();
          reader.onload = () => {
            setImageSrc(reader.result as string);
            setResultImageSrc(null);
          };
          reader.readAsDataURL(file);
        }
      }
    }
  };

  const handleExecuteEdit = async () => {
    if (!imageSrc || !prompt.trim()) return;

    try {
      setIsProcessing(true);
      // Submit generation job with edit parameters
      const res = await api.submitGeneration({
        prompt: prompt,
        mode: 'edit',
        edit_mode: activeSubTab,
        init_image: imageSrc,
        mask_image: (activeSubTab === 'inpaint' || activeSubTab === 'outpaint') ? maskBase64 : undefined,
        strength: strength,
        expand_left: expandLeft,
        expand_right: expandRight,
        expand_top: expandTop,
        expand_bottom: expandBottom,
        steps: 25,
        guidance: 5.0
      });

      // Poll until complete
      const poll = setInterval(async () => {
        const job = await api.getJob(res.job_id);
        if (job.state === 'complete') {
          clearInterval(poll);
          setIsProcessing(false);
          if (job.output_image_url) {
            setResultImageSrc(`http://127.0.0.1:7860${job.output_image_url}`);
          }
          onGenerationComplete();
        } else if (job.state === 'failed' || job.state === 'cancelled') {
          clearInterval(poll);
          setIsProcessing(false);
          if (job.state === 'failed') {
            alert(job.error_message || 'Edit operation failed.');
          }
        }
      }, 500);
    } catch (err: any) {
      setIsProcessing(false);
      alert(err.message || 'Failed to submit edit job');
    }
  };

  const handleApplyPreset = (presetKey: string) => {
    if (presetKey === 'square_to_landscape') {
      setExpandLeft(192); setExpandRight(192); setExpandTop(0); setExpandBottom(0);
    } else if (presetKey === 'square_to_portrait') {
      setExpandLeft(0); setExpandRight(0); setExpandTop(128); setExpandBottom(128);
    } else if (presetKey === 'landscape_to_phone') {
      setExpandLeft(0); setExpandRight(0); setExpandTop(280); setExpandBottom(280);
    } else if (presetKey === 'portrait_to_cinema') {
      setExpandLeft(320); setExpandRight(320); setExpandTop(0); setExpandBottom(0);
    }
  };

  return (
    <div onPaste={handlePaste} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Subtabs Selector */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div className="pill-group">
          <button
            className={`pill-btn ${activeSubTab === 'inpaint' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('inpaint')}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Brush size={15} />
            <span>Inpainting</span>
          </button>
          <button
            className={`pill-btn ${activeSubTab === 'outpaint' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('outpaint')}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Maximize2 size={15} />
            <span>Outpainting</span>
          </button>
          <button
            className={`pill-btn ${activeSubTab === 'img2img' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('img2img')}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Sliders size={15} />
            <span>Image-to-Image</span>
          </button>
          <button
            className={`pill-btn ${activeSubTab === 'instruct' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('instruct')}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Wand2 size={15} />
            <span>Instruction Edit</span>
          </button>
        </div>

        {/* Upload Button */}
        <div>
          <label className="btn btn-secondary" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Upload size={15} />
            <span>Load Image (or Paste / Drag)</span>
            <input type="file" accept="image/*" onChange={handleFileUpload} style={{ display: 'none' }} />
          </label>
        </div>
      </div>

      {/* Editor Content Body */}
      {!imageSrc ? (
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) {
              const reader = new FileReader();
              reader.onload = () => setImageSrc(reader.result as string);
              reader.readAsDataURL(file);
            }
          }}
          className="glass-panel"
          style={{
            minHeight: 460,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            border: '2px dashed var(--border-subtle)',
            gap: '1rem',
            padding: '2rem'
          }}
        >
          <div style={{
            width: 70,
            height: 70,
            borderRadius: '50%',
            background: 'var(--bg-surface-elevated)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Upload size={30} color="var(--primary-light)" />
          </div>
          <div style={{ textAlign: 'center' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Drop an image here to start editing</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Supports JPG, PNG, WEBP. You can also paste directly (Ctrl+V) or click Load Image above.
            </p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(420px, 1.3fr) minmax(380px, 1fr)', gap: '1.5rem' }}>
          {/* Left: Canvas / Image Area */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {activeSubTab === 'inpaint' && (
              <InpaintCanvas
                imageSrc={imageSrc}
                onApplyMask={(b64) => setMaskBase64(b64)}
              />
            )}

            {activeSubTab === 'outpaint' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{
                  background: 'var(--bg-input)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <img src={imageSrc} alt="Source" style={{ maxHeight: 380, objectFit: 'contain', borderRadius: 8 }} />
                </div>
                <OutpaintControls
                  expandLeft={expandLeft}
                  setExpandLeft={setExpandLeft}
                  expandRight={expandRight}
                  setExpandRight={setExpandRight}
                  expandTop={expandTop}
                  setExpandTop={setExpandTop}
                  expandBottom={expandBottom}
                  setExpandBottom={setExpandBottom}
                  onApplyPreset={handleApplyPreset}
                />
              </div>
            )}

            {(activeSubTab === 'img2img' || activeSubTab === 'instruct') && (
              <div style={{
                background: 'var(--bg-input)',
                borderRadius: 'var(--radius-md)',
                padding: '1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <img src={imageSrc} alt="Source" style={{ maxHeight: 440, objectFit: 'contain', borderRadius: 8 }} />
              </div>
            )}
          </div>

          {/* Right: Controls & Result Preview */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>
                {activeSubTab === 'inpaint' && 'Inpaint Instruction'}
                {activeSubTab === 'outpaint' && 'Outpaint Description'}
                {activeSubTab === 'img2img' && 'Image-to-Image Prompt'}
                {activeSubTab === 'instruct' && 'Instruction to Apply'}
              </h3>

              <textarea
                className="input-textarea"
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={
                  activeSubTab === 'instruct'
                    ? "e.g. 'change her jacket to red', 'add neon sunglasses'..."
                    : "Describe what should be generated in the modified area..."
                }
              />

              {/* Strength slider for Img2Img */}
              {activeSubTab === 'img2img' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600 }}>
                    <span style={{ color: 'var(--text-muted)' }}>Denoising Strength:</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{strength.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min={0.1}
                    max={0.95}
                    step={0.05}
                    value={strength}
                    onChange={(e) => setStrength(parseFloat(e.target.value))}
                    style={{ width: '100%', marginTop: 4, accentColor: 'var(--primary)' }}
                  />
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    Lower values preserve original composition; higher values allow more creative transformation.
                  </div>
                </div>
              )}

              <button
                onClick={handleExecuteEdit}
                disabled={isProcessing || !prompt.trim()}
                className="btn-generate"
                style={{ width: '100%', marginTop: '0.5rem' }}
              >
                <Sparkles size={18} />
                <span>{isProcessing ? 'PROCESSING EDIT...' : 'APPLY MODIFICATION'}</span>
              </button>
            </div>

            {/* Before / After Comparison Result */}
            {resultImageSrc && (
              <div className="glass-panel" style={{ padding: '1rem', animation: 'fadeIn 0.3s ease' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Eye size={16} />
                  <span>Modified Result:</span>
                </div>
                <img
                  src={resultImageSrc}
                  alt="Result"
                  style={{ width: '100%', maxHeight: 340, objectFit: 'contain', borderRadius: 8, boxShadow: '0 4px 20px rgba(0,0,0,0.5)' }}
                />
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                  <button
                    onClick={() => setImageSrc(resultImageSrc)}
                    className="btn btn-secondary"
                    style={{ flex: 1, fontSize: '0.8rem' }}
                  >
                    <span>Use as New Base</span>
                  </button>
                  <a
                    href={resultImageSrc}
                    download="edited_output.png"
                    className="btn btn-primary"
                    style={{ textDecoration: 'none', fontSize: '0.8rem' }}
                  >
                    Download
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
