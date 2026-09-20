import React, { useState, useEffect } from 'react';
import { Layers, RefreshCw, Heart, Tag, Sliders, Check } from 'lucide-react';
import { LoRAInfo } from '../types';
import { api } from '../services/api';

export const LoRAPage: React.FC = () => {
  const [loras, setLoras] = useState<LoRAInfo[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [strengths, setStrengths] = useState<Record<string, number>>({});

  const fetchLoras = async () => {
    try {
      setIsLoading(true);
      const data = await api.getLoRAs();
      setLoras(data);
      const strMap: Record<string, number> = {};
      data.forEach(l => { strMap[l.id] = l.default_strength; });
      setStrengths(strMap);
    } catch (err) {
      console.error('Failed to load LoRAs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLoras();
  }, []);

  const handleRescan = async () => {
    try {
      setIsLoading(true);
      const data = await api.rescanLoRAs();
      setLoras(data);
    } catch (err) {
      console.error('Failed to rescan:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>LoRA Ecosystem Manager</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Scan local Safetensors LoRAs from <code>models/loras</code>. Incompatible architecture pairings are prevented automatically.
            </p>
          </div>
          <button onClick={handleRescan} className="btn btn-secondary">
            <RefreshCw size={15} />
            <span>Scan LoRA Folder</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Scanning LoRA models...
        </div>
      ) : loras.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          No LoRAs found in <code>models/loras</code>.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {loras.map((lora) => (
            <div
              key={lora.id}
              className="glass-panel"
              style={{
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>{lora.name}</h3>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {lora.filename} ({lora.file_size_mb} MB)
                  </div>
                </div>
                <div className="badge badge-indigo">
                  {lora.base_architecture.toUpperCase()}
                </div>
              </div>

              {/* Trigger Words */}
              <div>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                  <Tag size={12} /> Trigger Words:
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                  {lora.trigger_words.map((tw) => (
                    <span
                      key={tw}
                      style={{
                        background: 'var(--bg-input)',
                        padding: '0.2rem 0.5rem',
                        borderRadius: 4,
                        fontSize: '0.7rem',
                        color: 'var(--accent-cyan)'
                      }}
                    >
                      {tw}
                    </span>
                  ))}
                </div>
              </div>

              {/* Strength Slider */}
              <div style={{ background: 'var(--bg-input)', padding: '0.65rem', borderRadius: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Adapter Strength:</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>
                    {(strengths[lora.id] ?? lora.default_strength).toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min={0.1}
                  max={1.5}
                  step={0.05}
                  value={strengths[lora.id] ?? lora.default_strength}
                  onChange={(e) => setStrengths({ ...strengths, [lora.id]: parseFloat(e.target.value) })}
                  style={{ width: '100%', marginTop: 4, accentColor: 'var(--primary)' }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
