import React, { useState, useEffect, useCallback } from 'react';
import {
  Search, Heart, Sliders, Trash2,
  X, Download, Sparkles, RefreshCw
} from 'lucide-react';
import { GalleryItem } from '../types';
import { api } from '../services/api';

interface GalleryPageProps {
  onReuseSettings: (item: GalleryItem) => void;
  onSendToEditor: (imageSrc: string, prompt: string) => void;
}

export const GalleryPage: React.FC<GalleryPageProps> = ({
  onReuseSettings,
  onSendToEditor
}) => {
  const [items, setItems] = useState<GalleryItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [search, setSearch] = useState<string>('');
  const [modelFilter, setModelFilter] = useState<string>('');
  const [favoriteOnly, setFavoriteOnly] = useState<boolean>(false);
  const [selectedItem, setSelectedItem] = useState<GalleryItem | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchGallery = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await api.getGallery({
        search: search || undefined,
        model: modelFilter || undefined,
        favorite_only: favoriteOnly
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load gallery:', err);
    } finally {
      setIsLoading(false);
    }
  }, [search, modelFilter, favoriteOnly]);

  useEffect(() => {
    fetchGallery();
  }, [fetchGallery]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchGallery();
  };

  const handleToggleFavorite = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      const isFav = await api.toggleFavorite(id);
      setItems(items.map(item => item.id === id ? { ...item, is_favorite: isFav ? 1 : 0 } : item));
      if (selectedItem?.id === id) {
        setSelectedItem({ ...selectedItem, is_favorite: isFav ? 1 : 0 });
      }
    } catch (err) {
      console.error('Failed to toggle favorite:', err);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this generation from disk?')) return;
    try {
      await api.deleteGeneration(id);
      setItems(items.filter(item => item.id !== id));
      if (selectedItem?.id === id) setSelectedItem(null);
    } catch (err) {
      console.error('Failed to delete item:', err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Search & Filter Header Bar */}
      <div className="glass-panel" style={{ padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Search Input Form */}
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: 260 }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: 10, top: 10 }} />
            <input
              type="text"
              className="input-text"
              style={{ paddingLeft: 34, width: '100%' }}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search prompts, keywords..."
            />
          </div>
          <button type="submit" className="btn btn-secondary" style={{ padding: '0.5rem 0.85rem' }}>
            Search
          </button>
        </form>

        {/* Filter Badges & Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Favorites filter toggle */}
          <button
            onClick={() => setFavoriteOnly(!favoriteOnly)}
            className={`btn ${favoriteOnly ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.45rem 0.75rem', fontSize: '0.8rem' }}
          >
            <Heart size={14} fill={favoriteOnly ? 'currentColor' : 'none'} />
            <span>Favorites</span>
          </button>

          {/* Model Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Model:</span>
            <select
              className="select-input"
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
            >
              <option value="">All Models</option>
              <option value="flux-klein-4b">FLUX.2 Klein 4B</option>
              <option value="flux-klein-9b">FLUX.2 Klein 9B</option>
              <option value="zimage-turbo">Z-Image Turbo</option>
              <option value="qwen-image">Qwen Image</option>
              <option value="sdxl">SDXL</option>
            </select>
          </div>

          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500 }}>
            {total} {total === 1 ? 'item' : 'items'}
          </span>

          <button onClick={fetchGallery} className="btn btn-secondary" style={{ padding: '0.45rem 0.65rem' }} title="Refresh Gallery">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Grid of Images */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading saved creations...
        </div>
      ) : items.length === 0 ? (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--text-muted)' }}>
          <Sparkles size={40} color="var(--border-subtle)" style={{ marginBottom: '1rem' }} />
          <h3>No images in gallery</h3>
          <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
            Generate your first image to populate the gallery.
          </p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: '1rem'
        }}>
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => setSelectedItem(item)}
              style={{
                background: 'var(--bg-surface)',
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
                border: '1px solid var(--border-subtle)',
                cursor: 'pointer',
                transition: 'transform 0.2s, border-color 0.2s, box-shadow 0.2s',
                position: 'relative',
                display: 'flex',
                flexDirection: 'column'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-3px)';
                e.currentTarget.style.borderColor = 'var(--primary-light)';
                e.currentTarget.style.boxShadow = 'var(--shadow-card)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              {/* Thumbnail Container */}
              <div style={{ width: '100%', aspectRatio: '1/1', background: '#0a0d14', position: 'relative' }}>
                <img
                  src={api.getThumbUrl(item.id)}
                  alt={item.prompt}
                  loading="lazy"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />

                {/* Favorite Heart Badge */}
                <button
                  onClick={(e) => handleToggleFavorite(e, item.id)}
                  style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    background: 'rgba(0, 0, 0, 0.65)',
                    backdropFilter: 'blur(6px)',
                    border: 'none',
                    borderRadius: '50%',
                    width: 28,
                    height: 28,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: item.is_favorite ? 'var(--accent-rose)' : '#ffffff',
                    cursor: 'pointer'
                  }}
                >
                  <Heart size={14} fill={item.is_favorite ? 'currentColor' : 'none'} />
                </button>

                {/* Model Tag */}
                <div style={{
                  position: 'absolute',
                  bottom: 8,
                  left: 8,
                  background: 'rgba(15, 21, 34, 0.85)',
                  backdropFilter: 'blur(6px)',
                  padding: '0.15rem 0.45rem',
                  borderRadius: 4,
                  fontSize: '0.65rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--primary-light)',
                  border: '1px solid rgba(255,255,255,0.1)'
                }}>
                  {item.model.toUpperCase()}
                </div>
              </div>

              {/* Prompt Snippet */}
              <div style={{ padding: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary)', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div style={{
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  lineHeight: 1.4
                }}>
                  {item.prompt}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem', color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  <span>{item.width}x{item.height}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Inspect Metadata & Reuse Modal */}
      {selectedItem && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(12px)',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem'
        }} onClick={() => setSelectedItem(null)}>
          <div
            onClick={(e) => e.stopPropagation()}
            className="glass-panel"
            style={{
              maxWidth: 960,
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              display: 'grid',
              gridTemplateColumns: 'minmax(320px, 1fr) minmax(320px, 1fr)',
              borderRadius: 'var(--radius-lg)',
              overflow: 'hidden'
            }}
          >
            {/* Full Image */}
            <div style={{ background: '#070a10', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
              <img
                src={api.getImageUrl(selectedItem.id)}
                alt={selectedItem.prompt}
                style={{ maxWidth: '100%', maxHeight: '80vh', objectFit: 'contain', borderRadius: 8 }}
              />
            </div>

            {/* Details Panel */}
            <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Image Metadata</h3>
                <button
                  onClick={() => setSelectedItem(null)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                >
                  <X size={20} />
                </button>
              </div>

              {/* Prompt */}
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Prompt:</span>
                <div style={{ background: 'var(--bg-input)', padding: '0.65rem', borderRadius: 6, fontSize: '0.85rem', marginTop: 4, lineHeight: 1.4 }}>
                  {selectedItem.prompt}
                </div>
              </div>

              {selectedItem.negative_prompt && (
                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Negative:</span>
                  <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6, fontSize: '0.8rem', marginTop: 4 }}>
                    {selectedItem.negative_prompt}
                  </div>
                </div>
              )}

              {/* Specs Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem', fontSize: '0.8rem' }}>
                <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Model:</span>
                  <div style={{ fontWeight: 600 }}>{selectedItem.model.toUpperCase()}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Dimensions:</span>
                  <div style={{ fontWeight: 600 }}>{selectedItem.width} x {selectedItem.height}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Seed:</span>
                  <div style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{selectedItem.seed}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Steps / CFG:</span>
                  <div style={{ fontWeight: 600 }}>{selectedItem.steps} steps | {selectedItem.guidance}</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Generation Time:</span>
                  <div style={{ fontWeight: 600 }}>{selectedItem.generation_time}s</div>
                </div>
                <div style={{ background: 'var(--bg-input)', padding: '0.5rem', borderRadius: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Peak VRAM:</span>
                  <div style={{ fontWeight: 600 }}>{selectedItem.peak_vram_mb} MB</div>
                </div>
              </div>

              {/* Modal Actions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: 'auto' }}>
                <button
                  onClick={() => {
                    onReuseSettings(selectedItem);
                    setSelectedItem(null);
                  }}
                  className="btn btn-primary"
                  style={{ width: '100%' }}
                >
                  <Sparkles size={16} />
                  <span>Reuse Prompt & Settings</span>
                </button>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => {
                      onSendToEditor(api.getImageUrl(selectedItem.id), selectedItem.prompt);
                      setSelectedItem(null);
                    }}
                    className="btn btn-secondary"
                    style={{ flex: 1, fontSize: '0.8rem' }}
                  >
                    <Sliders size={14} />
                    <span>Send to Editor</span>
                  </button>

                  <a
                    href={api.getImageUrl(selectedItem.id)}
                    download={`antigravity_${selectedItem.id}.png`}
                    className="btn btn-secondary"
                    style={{ flex: 1, fontSize: '0.8rem', textDecoration: 'none' }}
                  >
                    <Download size={14} />
                    <span>Download PNG</span>
                  </a>

                  <button
                    onClick={(e) => handleDelete(e, selectedItem.id)}
                    className="btn btn-danger"
                    style={{ padding: '0.5rem 0.75rem' }}
                    title="Delete permanently"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
