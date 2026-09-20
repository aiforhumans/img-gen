import React, { useRef, useEffect, useState } from 'react';
import {
  Paintbrush, Eraser, Undo, Redo, RotateCcw, ZoomIn, ZoomOut,
  ArrowRightLeft
} from 'lucide-react';

interface InpaintCanvasProps {
  imageSrc: string;
  onApplyMask: (maskBase64: string) => void;
}

export const InpaintCanvas: React.FC<InpaintCanvasProps> = ({
  imageSrc,
  onApplyMask
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageCanvasRef = useRef<HTMLCanvasElement>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement>(null);

  const [tool, setTool] = useState<'brush' | 'eraser'>('brush');
  const [brushSize, setBrushSize] = useState<number>(35);
  const [zoom, setZoom] = useState<number>(1.0);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [history, setHistory] = useState<ImageData[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);

  // Load image onto background canvas
  useEffect(() => {
    if (!imageSrc) return;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = imageSrc;
    img.onload = () => {
      const imgCanvas = imageCanvasRef.current;
      const maskCanvas = maskCanvasRef.current;
      if (!imgCanvas || !maskCanvas) return;

      imgCanvas.width = img.width;
      imgCanvas.height = img.height;
      maskCanvas.width = img.width;
      maskCanvas.height = img.height;

      const imgCtx = imgCanvas.getContext('2d');
      if (imgCtx) {
        imgCtx.drawImage(img, 0, 0);
      }

      // Initialize transparent mask
      const maskCtx = maskCanvas.getContext('2d');
      if (maskCtx) {
        maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
        // Save initial state
        const initialData = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
        setHistory([initialData]);
        setHistoryIndex(0);
      }
    };
  }, [imageSrc]);

  const saveHistoryState = () => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;
    const ctx = maskCanvas.getContext('2d');
    if (!ctx) return;

    const data = ctx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
    const newHist = history.slice(0, historyIndex + 1);
    newHist.push(data);
    setHistory(newHist);
    setHistoryIndex(newHist.length - 1);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      const newIdx = historyIndex - 1;
      const maskCanvas = maskCanvasRef.current;
      if (maskCanvas) {
        const ctx = maskCanvas.getContext('2d');
        ctx?.putImageData(history[newIdx], 0, 0);
        setHistoryIndex(newIdx);
      }
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const newIdx = historyIndex + 1;
      const maskCanvas = maskCanvasRef.current;
      if (maskCanvas) {
        const ctx = maskCanvas.getContext('2d');
        ctx?.putImageData(history[newIdx], 0, 0);
        setHistoryIndex(newIdx);
      }
    }
  };

  const handleClear = () => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;
    const ctx = maskCanvas.getContext('2d');
    if (ctx) {
      ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
      saveHistoryState();
    }
  };

  const handleInvert = () => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;
    const ctx = maskCanvas.getContext('2d');
    if (!ctx) return;

    const imgData = ctx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
    const data = imgData.data;
    for (let i = 0; i < data.length; i += 4) {
      const alpha = data[i + 3];
      if (alpha > 50) {
        data[i + 3] = 0; // Turn off
      } else {
        // Turn on with semi-transparent violet
        data[i] = 217;     // R
        data[i + 1] = 70;  // G
        data[i + 2] = 239; // B
        data[i + 3] = 180; // A
      }
    }
    ctx.putImageData(imgData, 0, 0);
    saveHistoryState();
  };

  // Drawing event handlers
  const getCanvasCoords = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = maskCanvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  };

  const startDraw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    draw(e);
  };

  const stopDraw = () => {
    if (isDrawing) {
      setIsDrawing(false);
      saveHistoryState();
      // Generate black/white mask for inpaint backend
      exportMask();
    }
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing && e.type !== 'mousedown') return;
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;
    const ctx = maskCanvas.getContext('2d');
    if (!ctx) return;

    const coords = getCanvasCoords(e);

    ctx.lineWidth = brushSize;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    if (tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.beginPath();
      ctx.arc(coords.x, coords.y, brushSize / 2, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = 'rgba(217, 70, 239, 0.7)'; // Glowing magenta mask color
      ctx.beginPath();
      ctx.arc(coords.x, coords.y, brushSize / 2, 0, Math.PI * 2);
      ctx.fill();
    }
  };

  const exportMask = () => {
    const maskCanvas = maskCanvasRef.current;
    if (!maskCanvas) return;

    // Create a temporary canvas to render binary B&W mask (255 where painted, 0 elsewhere)
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = maskCanvas.width;
    exportCanvas.height = maskCanvas.height;
    const expCtx = exportCanvas.getContext('2d');
    if (!expCtx) return;

    // Fill black background
    expCtx.fillStyle = '#000000';
    expCtx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);

    // Read mask alpha values
    const maskCtx = maskCanvas.getContext('2d');
    if (!maskCtx) return;
    const maskData = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
    const expData = expCtx.getImageData(0, 0, exportCanvas.width, exportCanvas.height);

    for (let i = 0; i < maskData.data.length; i += 4) {
      const alpha = maskData.data[i + 3];
      if (alpha > 30) {
        expData.data[i] = 255;
        expData.data[i + 1] = 255;
        expData.data[i + 2] = 255;
      }
    }
    expCtx.putImageData(expData, 0, 0);

    const maskBase64 = exportCanvas.toDataURL('image/png');
    onApplyMask(maskBase64);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Canvas Tool Controls */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.5rem',
        background: 'var(--bg-surface)',
        padding: '0.5rem 0.75rem',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)'
      }}>
        {/* Brush vs Eraser */}
        <div className="pill-group">
          <button
            className={`pill-btn ${tool === 'brush' ? 'active' : ''}`}
            onClick={() => setTool('brush')}
            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Paintbrush size={14} />
            <span>Brush</span>
          </button>
          <button
            className={`pill-btn ${tool === 'eraser' ? 'active' : ''}`}
            onClick={() => setTool('eraser')}
            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Eraser size={14} />
            <span>Erase</span>
          </button>
        </div>

        {/* Brush Size Slider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Size:</span>
          <input
            type="range"
            min={5}
            max={120}
            value={brushSize}
            onChange={(e) => setBrushSize(parseInt(e.target.value))}
            style={{ width: 100, accentColor: 'var(--primary)' }}
          />
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', minWidth: 24 }}>
            {brushSize}
          </span>
        </div>

        {/* Mask Operations: Invert, Clear, Undo, Redo */}
        <div style={{ display: 'flex', gap: '0.35rem' }}>
          <button
            onClick={handleInvert}
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            title="Invert painted mask"
          >
            <ArrowRightLeft size={13} />
            <span>Invert</span>
          </button>

          <button
            onClick={handleClear}
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            title="Clear all mask paint"
          >
            <RotateCcw size={13} />
            <span>Clear</span>
          </button>

          <button
            onClick={handleUndo}
            disabled={historyIndex <= 0}
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.55rem' }}
            title="Undo"
          >
            <Undo size={14} />
          </button>

          <button
            onClick={handleRedo}
            disabled={historyIndex >= history.length - 1}
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.55rem' }}
            title="Redo"
          >
            <Redo size={14} />
          </button>
        </div>

        {/* Zoom Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <button
            onClick={() => setZoom(Math.max(0.5, zoom - 0.2))}
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.55rem' }}
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom(Math.min(2.5, zoom + 0.2))}
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.55rem' }}
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>
        </div>
      </div>

      {/* Layered Canvas Container */}
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: 480,
          background: '#070a10',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          overflow: 'auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative'
        }}
      >
        <div style={{
          position: 'relative',
          transform: `scale(${zoom})`,
          transformOrigin: 'center center',
          transition: 'transform 0.1s ease',
          boxShadow: '0 4px 24px rgba(0,0,0,0.7)'
        }}>
          {/* Base image canvas */}
          <canvas
            ref={imageCanvasRef}
            style={{ display: 'block', maxWidth: '100%', pointerEvents: 'none' }}
          />

          {/* Interactive mask drawing canvas */}
          <canvas
            ref={maskCanvasRef}
            onMouseDown={startDraw}
            onMouseUp={stopDraw}
            onMouseLeave={stopDraw}
            onMouseMove={draw}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              cursor: tool === 'brush' ? 'crosshair' : 'cell'
            }}
          />
        </div>
      </div>

      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        Paint the region you wish to modify. The highlighted area will be regenerated based on your prompt.
      </div>
    </div>
  );
};
