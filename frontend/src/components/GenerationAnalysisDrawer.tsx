import React from 'react';
import { Cpu, CheckCircle2, AlertCircle, Info, Sparkles } from 'lucide-react';
import { RoutingDecision } from '../types';

interface GenerationAnalysisProps {
  decision: RoutingDecision | null;
  isLoading: boolean;
}

export const GenerationAnalysisDrawer: React.FC<GenerationAnalysisProps> = ({
  decision,
  isLoading
}) => {
  if (!decision && !isLoading) return null;

  return (
    <div className="glass-panel" style={{ padding: '1rem', marginTop: '1rem', borderLeft: '3px solid var(--accent-cyan)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <Sparkles size={16} color="var(--accent-cyan)" />
        <span style={{ fontSize: '0.85rem', fontWeight: 700, letterSpacing: '0.02em', textTransform: 'uppercase', color: 'var(--accent-cyan)' }}>
          Auto Engine Generation Analysis
        </span>
      </div>

      {isLoading ? (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Analyzing prompt semantics locally...
        </div>
      ) : decision ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
          {/* Reason explanation */}
          <div style={{
            fontSize: '0.85rem',
            lineHeight: 1.4,
            color: 'var(--text-primary)',
            background: 'rgba(6, 182, 212, 0.08)',
            padding: '0.5rem 0.75rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid rgba(6, 182, 212, 0.2)'
          }}>
            <strong>Routing Reason:</strong> {decision.reason}
          </div>

          {/* Decision Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: '0.5rem',
            fontSize: '0.75rem'
          }}>
            <div style={{ background: 'var(--bg-input)', padding: '0.4rem 0.6rem', borderRadius: 6 }}>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Target Model:</span>
              <span style={{ fontWeight: 600, color: '#fff' }}>{decision.model.toUpperCase()}</span>
            </div>
            <div style={{ background: 'var(--bg-input)', padding: '0.4rem 0.6rem', borderRadius: 6 }}>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Detected Category:</span>
              <span style={{ fontWeight: 600, color: '#fff' }}>{decision.category}</span>
            </div>
            <div style={{ background: 'var(--bg-input)', padding: '0.4rem 0.6rem', borderRadius: 6 }}>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Text Rendering:</span>
              <span style={{ fontWeight: 600, color: decision.text_rendering ? 'var(--accent-emerald)' : 'var(--text-secondary)' }}>
                {decision.text_rendering ? 'Required (Accurate)' : 'Not detected'}
              </span>
            </div>
            <div style={{ background: 'var(--bg-input)', padding: '0.4rem 0.6rem', borderRadius: 6 }}>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Recommended Size:</span>
              <span style={{ fontWeight: 600, color: '#fff', fontFamily: 'var(--font-mono)' }}>
                {decision.width}x{decision.height} ({decision.aspect_ratio})
              </span>
            </div>
            <div style={{ background: 'var(--bg-input)', padding: '0.4rem 0.6rem', borderRadius: 6 }}>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Optimal Steps:</span>
              <span style={{ fontWeight: 600, color: '#fff' }}>{decision.steps} steps</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
