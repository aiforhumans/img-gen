import React, { useState } from 'react';
import {
  Zap, Trash2, FileText, Copy, Check,
  RefreshCw
} from 'lucide-react';
import { SystemStatus, VRAMStrategy } from '../types';
import { api } from '../services/api';

interface SystemPageProps {
  systemStatus?: SystemStatus;
  onRefresh: () => void;
  vramStrategy: VRAMStrategy;
  setVRAMStrategy: (s: VRAMStrategy) => void;
}

export const SystemPage: React.FC<SystemPageProps> = ({
  systemStatus,
  onRefresh,
  vramStrategy,
  setVRAMStrategy
}) => {
  const [copied, setCopied] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  const [diagnosticsData, setDiagnosticsData] = useState<any>(null);
  const [loadingDiag, setLoadingDiag] = useState(false);

  const gpu = systemStatus?.gpu;
  const totalMB = gpu?.vram_total_mb || 16303;
  const allocMB = gpu?.vram_allocated_mb || 0;
  const resMB = gpu?.vram_reserved_mb || 0;
  const freeMB = Math.max(0, totalMB - resMB);

  const allocPercent = Math.min(100, Math.round((allocMB / totalMB) * 100));
  const resPercent = Math.min(100, Math.round((resMB / totalMB) * 100));

  const handleClearCache = async () => {
    try {
      setClearingCache(true);
      await api.clearGPUCache();
      onRefresh();
    } catch (err) {
      console.error(err);
    } finally {
      setClearingCache(false);
    }
  };

  const handleStrategyChange = async (strat: VRAMStrategy) => {
    try {
      await api.updateVRAMStrategy(strat);
      setVRAMStrategy(strat);
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleFetchDiagnostics = async () => {
    try {
      setLoadingDiag(true);
      const data = await api.getDiagnostics();
      setDiagnosticsData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDiag(false);
    }
  };

  const handleCopyDiagnostics = () => {
    if (!diagnosticsData) return;
    navigator.clipboard.writeText(JSON.stringify(diagnosticsData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Overview Header */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Hardware & System Telemetry</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Real-time monitoring of NVIDIA GeForce RTX 5080 (16GB VRAM), PyTorch CUDA acceleration, and memory strategies.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handleClearCache}
              disabled={clearingCache}
              className="btn btn-secondary"
            >
              <Trash2 size={15} />
              <span>{clearingCache ? 'Flushing...' : 'Flush CUDA Cache'}</span>
            </button>
            <button onClick={onRefresh} className="btn btn-secondary">
              <RefreshCw size={15} />
              <span>Refresh Stats</span>
            </button>
          </div>
        </div>
      </div>

      {/* VRAM Allocation Gauge */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Zap size={18} color="var(--primary-light)" />
            <span>RTX 5080 VRAM Memory Allocation</span>
          </h3>
          <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
            Allocated: <strong>{(allocMB / 1024).toFixed(2)} GB</strong> / Reserved: {(resMB / 1024).toFixed(2)} GB / Total: {(totalMB / 1024).toFixed(1)} GB
          </span>
        </div>

        {/* Visual Stacked Bar */}
        <div style={{ width: '100%', height: 24, background: 'var(--bg-input)', borderRadius: 12, overflow: 'hidden', display: 'flex', position: 'relative' }}>
          <div
            style={{
              width: `${allocPercent}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #6366f1, #8b5cf6)',
              transition: 'width 0.3s'
            }}
            title={`Allocated: ${allocMB} MB`}
          />
          <div
            style={{
              width: `${Math.max(0, resPercent - allocPercent)}%`,
              height: '100%',
              background: 'rgba(99, 102, 241, 0.25)',
              transition: 'width 0.3s'
            }}
            title={`Reserved Overhead: ${resMB - allocMB} MB`}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#6366f1' }} /> Active Model Memory ({allocPercent}%)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'rgba(99, 102, 241, 0.25)' }} /> PyTorch Cache
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--border-subtle)' }} /> Free Headroom: {(freeMB / 1024).toFixed(1)} GB
            </span>
          </div>
        </div>
      </div>

      {/* Hardware & Software Details Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
        {/* GPU Specs */}
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-secondary)' }}>NVIDIA GPU Specs</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Device Name:</span>
              <strong style={{ color: 'var(--accent-emerald)' }}>{gpu?.gpu_name}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>VRAM Capacity:</span>
              <span>{(totalMB / 1024).toFixed(1)} GB GDDR7</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>NVIDIA Driver:</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{gpu?.driver_version}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>CUDA Architecture:</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>Compute Capability 12.0 (sm_120)</span>
            </div>
          </div>
        </div>

        {/* Runtime Stack */}
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-secondary)' }}>PyTorch & Environment</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>PyTorch Version:</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{gpu?.torch_version}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>CUDA Version:</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>CUDA {gpu?.cuda_version}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Python Host:</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>Python {systemStatus?.python_version} (64-bit)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Operating System:</span>
              <span>{systemStatus?.platform}</span>
            </div>
          </div>
        </div>

        {/* VRAM Strategy Mode */}
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-secondary)' }}>VRAM Management Strategy</h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Adjust how aggressively model weights and attention layers are offloaded:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {(['FULL_GPU', 'BALANCED', 'LOW_VRAM', 'CPU_OFFLOAD'] as VRAMStrategy[]).map((strat) => (
              <label
                key={strat}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.4rem 0.6rem',
                  borderRadius: 6,
                  background: vramStrategy === strat ? 'var(--bg-surface-elevated)' : 'transparent',
                  border: vramStrategy === strat ? '1px solid var(--primary-light)' : '1px solid transparent',
                  cursor: 'pointer',
                  fontSize: '0.8rem'
                }}
              >
                <input
                  type="radio"
                  name="vram_strat"
                  checked={vramStrategy === strat}
                  onChange={() => handleStrategyChange(strat)}
                />
                <strong>{strat}</strong>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Built-in Diagnostics Report Generator */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={18} color="var(--accent-cyan)" />
              <span>Diagnostic System Report</span>
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Generates a privacy-safe technical report without private prompt strings or generated image contents.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handleFetchDiagnostics}
              disabled={loadingDiag}
              className="btn btn-secondary"
            >
              <span>{loadingDiag ? 'Generating...' : 'Run Diagnostics'}</span>
            </button>

            {diagnosticsData && (
              <button
                onClick={handleCopyDiagnostics}
                className="btn btn-secondary"
              >
                {copied ? <Check size={15} color="var(--accent-emerald)" /> : <Copy size={15} />}
                <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
              </button>
            )}
          </div>
        </div>

        {diagnosticsData && (
          <pre style={{
            background: 'var(--bg-input)',
            padding: '1rem',
            borderRadius: 'var(--radius-md)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.75rem',
            overflowX: 'auto',
            maxHeight: 300,
            border: '1px solid var(--border-subtle)'
          }}>
            {JSON.stringify(diagnosticsData, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};
