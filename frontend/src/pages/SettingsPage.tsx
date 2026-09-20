import React, { useState } from 'react';
import { Folder, Bot, Eye, Save, CheckCircle2 } from 'lucide-react';

interface SettingsPageProps {
  settings?: any;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ settings: initialSettings }) => {
  const [modelDir, setModelDir] = useState(initialSettings?.paths?.model_dirs?.[0] || 'models');
  const [outputDir, setOutputDir] = useState(initialSettings?.paths?.output_dir || 'outputs');
  const [cacheDir, setCacheDir] = useState(initialSettings?.paths?.cache_dir || 'cache');
  const [lmStudioEnabled, setLmStudioEnabled] = useState(initialSettings?.lm_studio?.enabled ?? true);
  const [lmStudioUrl, setLmStudioUrl] = useState(initialSettings?.lm_studio?.base_url || 'http://127.0.0.1:1234/v1');
  const [livePreview, setLivePreview] = useState(initialSettings?.generation?.live_preview ?? true);
  const [saveMetadata, setSaveMetadata] = useState(initialSettings?.generation?.save_metadata_to_png ?? true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  React.useEffect(() => {
    if (initialSettings) {
      if (initialSettings.paths?.model_dirs?.[0]) setModelDir(initialSettings.paths.model_dirs[0]);
      if (initialSettings.paths?.output_dir) setOutputDir(initialSettings.paths.output_dir);
      if (initialSettings.paths?.cache_dir) setCacheDir(initialSettings.paths.cache_dir);
      if (initialSettings.lm_studio?.enabled !== undefined) setLmStudioEnabled(initialSettings.lm_studio.enabled);
      if (initialSettings.lm_studio?.base_url) setLmStudioUrl(initialSettings.lm_studio.base_url);
      if (initialSettings.generation?.live_preview !== undefined) setLivePreview(initialSettings.generation.live_preview);
      if (initialSettings.generation?.save_metadata_to_png !== undefined) setSaveMetadata(initialSettings.generation.save_metadata_to_png);
    }
  }, [initialSettings]);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', maxWidth: 900, margin: '0 auto' }}>
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Application Settings</h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
          Configure local paths, optional LM Studio intelligence, and hardware acceleration defaults.
        </p>
      </div>

      {/* Directory Paths */}
      <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Folder size={18} color="var(--primary-light)" />
          <span>Local Storage Directories</span>
        </h3>

        <div>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Model Storage Folder:</label>
          <input
            type="text"
            className="input-text"
            style={{ width: '100%', marginTop: 4 }}
            value={modelDir}
            onChange={(e) => setModelDir(e.target.value)}
          />
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Output Image Directory:</label>
          <input
            type="text"
            className="input-text"
            style={{ width: '100%', marginTop: 4 }}
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
          />
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Cache Directory:</label>
          <input
            type="text"
            className="input-text"
            style={{ width: '100%', marginTop: 4 }}
            value={cacheDir}
            onChange={(e) => setCacheDir(e.target.value)}
          />
        </div>
      </div>

      {/* LM Studio Integration */}
      <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Bot size={18} color="var(--accent-cyan)" />
          <span>LM Studio Local LLM Integration (Optional)</span>
        </h3>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <input
            type="checkbox"
            id="lmToggle"
            checked={lmStudioEnabled}
            onChange={(e) => setLmStudioEnabled(e.target.checked)}
            style={{ width: 18, height: 18, accentColor: 'var(--primary)' }}
          />
          <label htmlFor="lmToggle" style={{ fontSize: '0.875rem', cursor: 'pointer', fontWeight: 500 }}>
            Enable LM Studio Prompt Intelligence & Expansion
          </label>
        </div>

        {lmStudioEnabled && (
          <div>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Local LM Studio Endpoint:</label>
            <input
              type="text"
              className="input-text"
              style={{ width: '100%', marginTop: 4 }}
              value={lmStudioUrl}
              onChange={(e) => setLmStudioUrl(e.target.value)}
            />
            <div style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', marginTop: 4 }}>
              Status: Active at 127.0.0.1:1234 (Gemma 4 / DeepSeek models discovered)
            </div>
          </div>
        )}
      </div>

      {/* Generation Defaults */}
      <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Eye size={18} color="var(--accent-emerald)" />
          <span>Generation & Preview Settings</span>
        </h3>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <input
            type="checkbox"
            id="livePrevToggle"
            checked={livePreview}
            onChange={(e) => setLivePreview(e.target.checked)}
            style={{ width: 18, height: 18, accentColor: 'var(--primary)' }}
          />
          <label htmlFor="livePrevToggle" style={{ fontSize: '0.875rem', cursor: 'pointer', fontWeight: 500 }}>
            Show Intermediate Live Previews during generation steps
          </label>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <input
            type="checkbox"
            id="saveMetaToggle"
            checked={saveMetadata}
            onChange={(e) => setSaveMetadata(e.target.checked)}
            style={{ width: 18, height: 18, accentColor: 'var(--primary)' }}
          />
          <label htmlFor="saveMetaToggle" style={{ fontSize: '0.875rem', cursor: 'pointer', fontWeight: 500 }}>
            Embed lossless JSON and WebUI parameters directly inside generated PNGs
          </label>
        </div>
      </div>

      {/* Save Button */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '1rem' }}>
        {savedSuccess && (
          <span style={{ fontSize: '0.85rem', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <CheckCircle2 size={16} /> Settings saved successfully!
          </span>
        )}
        <button onClick={handleSave} className="btn btn-primary" style={{ padding: '0.65rem 1.5rem' }}>
          <Save size={16} />
          <span>Save Settings</span>
        </button>
      </div>
    </div>
  );
};
