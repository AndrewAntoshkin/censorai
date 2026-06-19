"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

/** Exact props from v7labs.com hero — ParticleFunnel component */
const V7 = {
  colorLine: 0x303030,
  colorSignal: 0xff6300,
  lineCount: 80,
  signalCount: 90,
  spreadHeight: 30,
  convergePointX: 50,
  curvePower: 0.82,
  waveSpeed: 2.4,
  waveHeight: 0.15,
  lineOpacity: 0.55,
  speedGlobal: 0.2,
  trailLength: 10,
  linePoints: 150,
  maxLines: 200,
  maxSignals: 200,
} as const;

type FunnelConfig = typeof V7;

type Signal = {
  mesh: THREE.Line;
  laneIndex: number;
  speed: number;
  progress: number;
  historyX: Float32Array;
  historyY: Float32Array;
  historyIdx: number;
  color: THREE.Color;
};

function samplePath(
  progress: number,
  laneIndex: number,
  time: number,
  config: FunnelConfig,
  visibleW: number,
  lineCount: number,
  target: THREE.Vector3,
) {
  const s = (config.convergePointX / 100) * visibleW;
  const l = -s + progress * visibleW;
  let u = 0;
  const d = (laneIndex / lineCount - 0.5) * 2;

  if (l < 0 && s > 0) {
    const t = (l + s) / s;
    let curve = (Math.cos(t * Math.PI) + 1) / 2;
    curve **= config.curvePower;
    u = d * config.spreadHeight * curve;
    u += Math.sin(time * config.waveSpeed + l * 0.1 + laneIndex) * config.waveHeight * curve;
  }

  target.set(l, u, 0);
}

export function HeroRays() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 1, 1000);
    camera.position.set(0, 0, 90);

    const fovRad = (45 * Math.PI) / 180;
    const visibleH = 2 * Math.tan(fovRad / 2) * 90;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    const lineMaterial = new THREE.LineBasicMaterial({
      color: V7.colorLine,
      transparent: true,
      opacity: V7.lineOpacity,
    });

    const signalMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    const lines: THREE.Line[] = [];
    for (let i = 0; i < V7.maxLines; i++) {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(V7.linePoints * 3), 3));
      const line = new THREE.Line(geometry, lineMaterial);
      line.visible = i < V7.lineCount;
      line.userData.id = i;
      group.add(line);
      lines.push(line);
    }

    const signals: Signal[] = [];
    const signalColor = new THREE.Color(V7.colorSignal);
    for (let i = 0; i < V7.maxSignals; i++) {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(150), 3));
      geometry.setAttribute("color", new THREE.BufferAttribute(new Float32Array(150), 3));
      const mesh = new THREE.Line(geometry, signalMaterial);
      mesh.visible = i < V7.signalCount;
      group.add(mesh);
      signals.push({
        mesh,
        laneIndex: Math.floor(Math.random() * V7.lineCount),
        speed: 0.2 + Math.random() * 0.5,
        progress: Math.random(),
        historyX: new Float32Array(50),
        historyY: new Float32Array(50),
        historyIdx: 0,
        color: signalColor.clone(),
      });
    }

    const clock = new THREE.Clock();
    const point = new THREE.Vector3();
    let visibleW = visibleH;
    let animationId = 0;
    let isVisible = true;

    const resize = () => {
      const width = container.clientWidth;
      const height = container.clientHeight;
      if (width === 0 || height === 0) return;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      visibleW = (width / height) * visibleH;
    };

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      if (!isVisible) return;

      const time = clock.getElapsedTime();
      const activeLines = V7.lineCount;

      group.position.x = visibleW * (V7.convergePointX / 100 - 0.5);

      for (let i = 0; i < V7.maxLines; i++) {
        const line = lines[i];
        const active = i < activeLines;
        line.visible = active;
        if (!active) continue;

        const positions = line.geometry.attributes.position.array as Float32Array;
        for (let p = 0; p < V7.linePoints; p++) {
          samplePath(p / (V7.linePoints - 1), i, time, V7, visibleW, activeLines, point);
          positions[p * 3] = point.x;
          positions[p * 3 + 1] = point.y;
          positions[p * 3 + 2] = point.z;
        }
        line.geometry.attributes.position.needsUpdate = true;
      }

      if (!reduced) {
        const activeSignals = V7.signalCount;
        const trailLen = V7.trailLength;

        for (let i = 0; i < V7.maxSignals; i++) {
          const signal = signals[i];
          const active = i < activeSignals;
          signal.mesh.visible = active;
          if (!active) continue;

          if (signal.laneIndex >= activeLines) {
            signal.laneIndex = Math.floor(Math.random() * activeLines);
          }

          signal.progress += signal.speed * 0.005 * V7.speedGlobal;
          if (signal.progress > 1) {
            signal.progress = 0;
            signal.historyIdx = 0;
          }

          samplePath(signal.progress, signal.laneIndex, time, V7, visibleW, activeLines, point);

          const slot = signal.historyIdx % 50;
          signal.historyX[slot] = point.x;
          signal.historyY[slot] = point.y;
          signal.historyIdx++;

          const count = Math.min(signal.historyIdx, trailLen);
          const positions = signal.mesh.geometry.attributes.position.array as Float32Array;
          const colors = signal.mesh.geometry.attributes.color.array as Float32Array;

          for (let t = 0; t < count; t++) {
            const idx = (signal.historyIdx - 1 - t + 50) % 50;
            positions[t * 3] = signal.historyX[idx];
            positions[t * 3 + 1] = signal.historyY[idx];
            positions[t * 3 + 2] = 0;
            const fade = 1 - t / trailLen;
            colors[t * 3] = signal.color.r * fade;
            colors[t * 3 + 1] = signal.color.g * fade;
            colors[t * 3 + 2] = signal.color.b * fade;
          }

          signal.mesh.geometry.setDrawRange(0, count);
          signal.mesh.geometry.attributes.position.needsUpdate = true;
          signal.mesh.geometry.attributes.color.needsUpdate = true;
        }
      }

      renderer.render(scene, camera);
    };

    resize();
    animate();

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);

    const intersectionObserver = new IntersectionObserver(
      (entries) => {
        isVisible = entries[0]?.isIntersecting ?? true;
      },
      { threshold: 0 },
    );
    intersectionObserver.observe(container);

    return () => {
      cancelAnimationFrame(animationId);
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      lines.forEach((line) => line.geometry.dispose());
      signals.forEach((signal) => signal.mesh.geometry.dispose());
      lineMaterial.dispose();
      signalMaterial.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      container.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden
    />
  );
}
