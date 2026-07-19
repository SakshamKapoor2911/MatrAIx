import { useEffect, useRef } from "react";

/** Fibonacci sphere — even distribution of points on a unit sphere. */
function fibonacciSphere(n: number): Array<[number, number, number]> {
  const pts: Array<[number, number, number]> = [];
  const phi = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const theta = phi * i;
    pts.push([Math.cos(theta) * r, y, Math.sin(theta) * r]);
  }
  return pts;
}

const POINTS = fibonacciSphere(420);

function readRgbTriplet(token: string, fallback: [number, number, number]): [number, number, number] {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(token).trim();
  const parts = raw.split(/\s+/).map((part) => Number(part));
  if (parts.length === 3 && parts.every((n) => Number.isFinite(n))) {
    return [parts[0], parts[1], parts[2]];
  }
  return fallback;
}

export function DigitalGlobe({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let angleY = 0;
    let angleX = 0.32;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const draw = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const cx = w / 2;
      const cy = h / 2;
      const radius = Math.min(w, h) * 0.38;

      ctx.clearRect(0, 0, w, h);

      const [primaryR, primaryG, primaryB] = readRgbTriplet("--primary", [0, 118, 194]);
      const [primaryDimR, primaryDimG, primaryDimB] = readRgbTriplet("--primary-dim", [0, 92, 152]);
      const [primaryLightR, primaryLightG, primaryLightB] = readRgbTriplet("--primary-light", [56, 176, 224]);
      const [primaryGlowR, primaryGlowG, primaryGlowB] = readRgbTriplet("--primary-glow", [96, 200, 236]);

      // Atmosphere halo
      const halo = ctx.createRadialGradient(cx, cy, radius * 0.55, cx, cy, radius * 1.35);
      halo.addColorStop(0, `rgba(${primaryLightR}, ${primaryLightG}, ${primaryLightB}, 0.32)`);
      halo.addColorStop(0.45, `rgba(${primaryDimR}, ${primaryDimG}, ${primaryDimB}, 0.12)`);
      halo.addColorStop(1, `rgba(${Math.round(primaryR * 0.42)}, ${Math.round(primaryG * 0.42)}, ${Math.round(primaryB * 0.42)}, 0)`);
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.35, 0, Math.PI * 2);
      ctx.fill();

      const cosY = Math.cos(angleY);
      const sinY = Math.sin(angleY);
      const cosX = Math.cos(angleX);
      const sinX = Math.sin(angleX);

      const projected: Array<{ x: number; y: number; z: number; i: number }> = [];

      for (let i = 0; i < POINTS.length; i++) {
        const [x0, y0, z0] = POINTS[i];
        const x1 = x0 * cosY + z0 * sinY;
        const z1 = -x0 * sinY + z0 * cosY;
        const y2 = y0 * cosX - z1 * sinX;
        const z2 = y0 * sinX + z1 * cosX;
        projected.push({
          x: cx + x1 * radius,
          y: cy + y2 * radius,
          z: z2,
          i,
        });
      }

      projected.sort((a, b) => a.z - b.z);

      // Wireframe meridians
      ctx.strokeStyle = `rgba(${primaryR}, ${primaryG}, ${primaryB}, 0.12)`;
      ctx.lineWidth = 0.6;
      for (let m = 0; m < 8; m++) {
        const meridianAngle = (m / 8) * Math.PI * 2 + angleY * 0.5;
        ctx.beginPath();
        for (let t = 0; t <= 64; t++) {
          const lat = (t / 64) * Math.PI - Math.PI / 2;
          const x0 = Math.cos(lat) * Math.cos(meridianAngle);
          const y0 = Math.sin(lat);
          const z0 = Math.cos(lat) * Math.sin(meridianAngle);
          const x1 = x0 * cosY + z0 * sinY;
          const z1 = -x0 * sinY + z0 * cosY;
          const y2 = y0 * cosX - z1 * sinX;
          const z2 = y0 * sinX + z1 * cosX;
          if (z2 < -0.15) continue;
          const px = cx + x1 * radius;
          const py = cy + y2 * radius;
          if (t === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.stroke();
      }

      // Outer ring
      ctx.strokeStyle = `rgba(${primaryLightR}, ${primaryLightG}, ${primaryLightB}, 0.5)`;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.stroke();

      // Persona points
      for (const p of projected) {
        const depth = (p.z + 1) / 2;
        const size = 0.6 + depth * 1.8;
        const alpha = 0.15 + depth * 0.85;
        const pulse = 0.85 + 0.15 * Math.sin(frameRef.current * 0.02 + p.i * 0.15);

        ctx.beginPath();
        ctx.fillStyle = `rgba(${primaryLightR}, ${primaryLightG}, ${primaryLightB}, ${alpha * pulse})`;
        ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
        ctx.fill();

        if (depth > 0.72 && p.i % 17 === 0) {
          ctx.beginPath();
          ctx.fillStyle = `rgba(${primaryGlowR}, ${primaryGlowG}, ${primaryGlowB}, ${0.35 * pulse})`;
          ctx.arc(p.x, p.y, size * 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      angleY += 0.0032;
      frameRef.current += 1;
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={`h-full w-full ${className}`}
      aria-hidden
    />
  );
}
