import React from 'react';
import {
  Sparkles, Sliders, Image as ImageIcon, Cpu, Layers, Settings,
  Activity, Zap, HardDrive, RefreshCw
} from 'lucide-react';
import { SystemStatus } from '../types';
import { api } from '../services/api';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  systemStatus?: SystemStatus;
  activeModel?: string;
  isGenerating?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  systemStatus,
  activeModel,
  isGenerating
}) => {
  const tabs = [
    { id: 'generate', label: 'Generate', icon: Sparkles },
    { id: 'edit', label: 'Edit & Inpaint', icon: Sliders },
    { id: 'gallery', label: 'Gallery', icon: ImageIcon },
    { id: 'models', label: 'Models', icon: HardDrive },
    { id: 'loras', label: 'LoRAs', icon: Layers },
    { id: 'system', label: 'System', icon: Cpu },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const gpu = systemStatus?.gpu;
  const vramTotal = gpu?.vram_total_mb || 16303;
  const vramAlloc = gpu?.vram_allocated_mb || 0;
  const vramPercent = Math.min(100, Math.round((vramAlloc / vramTotal) * 100));

  return (
    <header style={{
      background: 'rgba(11, 15, 24, 0.85)',
      backdropFilter: 'blur(20px)',
      borderBottom: '1px solid var(--border-subtle)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      padding: '0.75rem 1.5rem'
    }}>
      <div style={{
        maxWidth: 1600,
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        {/* Brand & Active Model */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.625rem',
            cursor: 'pointer'
          }} onClick={() => setActiveTab('generate')}>
            <div style={{
              width: 38,
              height: 38,
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #d946ef 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(99, 102, 241, 0.45)'
            }}>
              <Sparkles size={20} color="#fff" />
            </div>
            <div>
              <div style={{
                fontFamily: 'var(--font-heading)',
                fontWeight: 800,
                fontSize: '1.2rem',
                letterSpacing: '-0.02em',
                background: 'linear-gradient(90deg, #ffffff, #c7d2fe)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                ANTIGRAVITY
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em' }}>
                DIFFUSION STUDIO
              </div>
            </div>
          </div>

          {/* Active Model Indicator */}
          {activeModel && (
            <div className="badge badge-indigo" style={{ padding: '0.25rem 0.65rem' }}>
              <Zap size={13} />
              <span>{activeModel.toUpperCase()}</span>
            </div>
          )}
        </div>

        {/* Navigation Tabs */}
        <nav className="pill-group" style={{ background: 'rgba(15, 21, 34, 0.9)' }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                className={`pill-btn ${isActive ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                  padding: '0.45rem 0.95rem'
                }}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Live GPU VRAM Monitor Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              background: 'var(--bg-surface)',
              border: `1px solid ${vramPercent > 90 ? 'rgba(244,63,94,0.4)' : (vramPercent > 75 ? 'rgba(245,158,11,0.4)' : 'var(--border-subtle)')}`,
              borderRadius: 'var(--radius-md)',
              padding: '0.35rem 0.75rem',
              transition: 'all 0.2s'
            }}
          >
            <div
              onClick={() => setActiveTab('system')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                cursor: 'pointer'
              }}
              title="Click to view full System Monitor"
            >
              <div style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: vramPercent > 90 ? 'var(--accent-rose)' : (vramPercent > 75 ? 'var(--accent-amber)' : 'var(--accent-emerald)'),
                boxShadow: vramPercent > 90 ? '0 0 10px var(--accent-rose)' : '0 0 8px var(--accent-emerald)'
              }} />
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span>{gpu?.gpu_name?.includes('5080') ? 'RTX 5080' : (gpu?.gpu_name || 'GPU')}</span>
                  <span style={{
                    fontSize: '0.65rem',
                    padding: '0.05rem 0.35rem',
                    borderRadius: 4,
                    background: vramPercent > 90 ? 'rgba(244,63,94,0.2)' : (vramPercent > 75 ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)'),
                    color: vramPercent > 90 ? 'var(--accent-rose)' : (vramPercent > 75 ? 'var(--accent-amber)' : 'var(--accent-emerald)')
                  }}>
                    {vramPercent}%
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div style={{
                    width: 65,
                    height: 5,
                    background: 'rgba(255,255,255,0.1)',
                    borderRadius: 3,
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${vramPercent}%`,
                      height: '100%',
                      background: vramPercent > 90 ? 'var(--accent-rose)' : (vramPercent > 75 ? 'var(--accent-amber)' : 'linear-gradient(90deg, #6366f1, #06b6d4)'),
                      transition: 'width 0.3s'
                    }} />
                  </div>
                  <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    {(vramAlloc / 1024).toFixed(1)}/{(vramTotal / 1024).toFixed(0)}G
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Purge VRAM Cache Button */}
            <button
              onClick={async (e) => {
                e.stopPropagation();
                try {
                  await api.clearGPUCache();
                } catch (err) {
                  console.error('Failed to purge cache', err);
                }
              }}
              title="Purge GPU VRAM Cache & Reclaim Memory"
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: 'none',
                borderRadius: '4px',
                padding: '0.25rem',
                cursor: 'pointer',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <RefreshCw size={13} />
            </button>
          </div>

          {/* Generating pulse badge */}
          {isGenerating && (
            <div className="badge badge-cyan pulse-glow" style={{ padding: '0.35rem 0.65rem' }}>
              <Activity size={14} className="spin" />
              <span>GENERATING</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
