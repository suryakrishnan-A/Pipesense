import { useEffect, useRef, useState } from 'react';
import { useScroll } from 'framer-motion';
import OverlayPanels from './OverlayPanels';

const TOTAL_FRAMES = 300;

export default function HeroSequence({ onInspect }: { onInspect: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  const [images, setImages] = useState<HTMLImageElement[]>([]);
  const [loaded, setLoaded] = useState(false);
  const currentFrameRef = useRef<number>(-1);

  useEffect(() => {
    let loadedCount = 0;
    const imgs: HTMLImageElement[] = [];
    for (let i = 1; i <= TOTAL_FRAMES; i++) {
      const img = new Image();
      const frameStr = i.toString().padStart(3, '0');
      img.src = `/frames/ezgif-frame-${frameStr}.webp`;
      img.onload = async () => {
        try {
          await img.decode();
        } catch(e) {}
        loadedCount++;
        if (loadedCount === TOTAL_FRAMES) {
          setLoaded(true);
        }
      };
      imgs.push(img);
    }
    setImages(imgs);
  }, []);

  const drawFrame = (v: number, force = false) => {
    let frameIndex = Math.floor(v * (TOTAL_FRAMES - 1));
    if (frameIndex < 0) frameIndex = 0;
    if (frameIndex >= TOTAL_FRAMES) frameIndex = TOTAL_FRAMES - 1;
    
    if (!force && frameIndex === currentFrameRef.current) return;
    currentFrameRef.current = frameIndex;
    
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d', { alpha: false });
    
    if (canvas && ctx && images[frameIndex]) {
      const img = images[frameIndex];
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      
      // 'contain' logic for wide cinematic aspect ratio to render sharp at full device resolution
      const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
      const x = (canvas.width / 2) - (img.width / 2) * scale;
      const y = (canvas.height / 2) - (img.height / 2) * scale;
      
      ctx.fillStyle = '#050505'; // base dark color for letterbox
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, Math.round(x), Math.round(y), Math.round(img.width * scale), Math.round(img.height * scale));
    }
  };

  useEffect(() => {
    if (!loaded) return;
    
    let rafId: number;
    const unsubscribe = scrollYProgress.onChange((v) => {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => drawFrame(v));
    });
    
    drawFrame(scrollYProgress.get(), true);
    
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      unsubscribe();
    };
  }, [loaded, images, scrollYProgress]);

  useEffect(() => {
    const handleResize = () => {
      if (canvasRef.current) {
        // Native device pixel ratio for 4K crispness
        const dpr = window.devicePixelRatio || 1;
        canvasRef.current.width = window.innerWidth * dpr;
        canvasRef.current.height = window.innerHeight * dpr;
        
        if (loaded) {
          drawFrame(scrollYProgress.get(), true);
        }
      }
    };
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, [loaded]);

  return (
    <div ref={containerRef} className="relative w-full" style={{ height: '800vh' }}>
      <div className="sticky top-0 w-full h-screen overflow-hidden bg-[#050505]">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
        
        {/* VIGNETTE OVERLAY */}
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,_transparent_40%,_rgba(5,5,5,0.95)_100%)]" />
        
        {/* Subtle gradients */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#050505]/60 via-transparent to-transparent pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#050505]/40 via-transparent to-transparent pointer-events-none" />

        {!loaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#050505] z-50">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-pipesense-cyan border-t-transparent rounded-full animate-spin mb-4 shadow-[0_0_15px_rgba(0,240,255,0.5)]" />
              <p className="font-mono text-pipesense-cyan tracking-[0.2em] text-sm text-glow-cyan">ASSEMBLING 4K CINEMATIC ENGINE...</p>
            </div>
          </div>
        )}

        <OverlayPanels scrollProgress={scrollYProgress} onInspect={onInspect} />
      </div>
    </div>
  );
}
