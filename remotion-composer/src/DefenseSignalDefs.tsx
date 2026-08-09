import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";

// ---------------------------------------------------------------------------
// 三维场景：军事战略信号可视化
// ---------------------------------------------------------------------------

const GridFloor: React.FC = () => (
  <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.2, 0]}>
    <planeGeometry args={[30, 18]} />
    <meshBasicMaterial color="#060b18" />
  </mesh>
);

const Stars: React.FC<{ count: number }> = ({ count }) => {
  const positions = React.useMemo(() => {
    const pts: number[] = [];
    for (let i = 0; i < count; i++) {
      pts.push((Math.random() - 0.5) * 24);
      pts.push((Math.random() - 0.5) * 8);
      pts.push((Math.random() - 0.5) * 12);
    }
    return new Float32Array(pts);
  }, [count]);
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#6aa8ff" size={0.06} transparent opacity={0.7} />
    </points>
  );
};

const SceneSignal: React.FC<{ color: string }> = ({ color }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const r = 0.9 + 0.25 * Math.sin(t * 1.6);
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[4, 6, 3]} intensity={1.5} />
      <Stars count={200} />
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[r, 40, 40]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.9} wireframe />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[r, 24, 24]} />
        <meshBasicMaterial color={color} wireframe transparent opacity={0.25} />
      </mesh>
    </>
  );
};

const SceneAnchors: React.FC<{ color: string }> = ({ color }) => {
  const frame = useCurrentFrame();
  const boxes: { x: number; c: string }[] = [
    { x: -1.8, c: "#3B82F6" },
    { x: 0, c: color },
    { x: 1.8, c: "#F59E0B" },
  ];
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[4, 6, 3]} intensity={1.4} />
      <GridFloor />
      {boxes.map((p, i) => {
        const appear = spring({
          frame: frame - i * 15,
          fps: 30,
          config: { damping: 14, stiffness: 80 },
        });
        if (frame - i * 15 < 0) return null;
        return (
          <mesh key={p.x} position={[p.x, 0, 0]} rotation={[Math.PI / 4, Math.PI / 4, 0]} scale={appear}>
            <boxGeometry args={[1.1, 1.1, 1.1]} />
            <meshStandardMaterial color={p.c} emissive={p.c} emissiveIntensity={0.3} />
          </mesh>
        );
      })}
    </>
  );
};

const SceneRadar: React.FC<{ color: string }> = ({ color }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const angle = t * 1.4;
  const proj = Math.min(t / 3, 1);
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[3, 5, 4]} intensity={1.2} />
      <GridFloor />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.18, 0]}>
        <ringGeometry args={[2.3, 2.5, 80]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, angle]} position={[0, -1.17, 0]}>
        <ringGeometry args={[0, 2.5, 100, 1, 0, Math.PI / 4]} />
        <meshBasicMaterial color={color} transparent opacity={0.7} />
      </mesh>
      <mesh position={[0, 0.6, Math.sin(proj * Math.PI) * 3 + 1.6]}>
        <sphereGeometry args={[0.28, 20, 20]} />
        <meshStandardMaterial color="#FACC15" emissive="#FACC15" emissiveIntensity={2} />
      </mesh>
      <mesh position={[0, 0.1, 0]}>
        <coneGeometry args={[0.9, 1.6, 5]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
      </mesh>
    </>
  );
};

const SceneMarch: React.FC<{ color: string }> = ({ color }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const pointCount = 120;
  const pts = Array.from({ length: pointCount }, (_, i) => {
    const a = i / (pointCount - 1);
    return [
      interpolate(a, [0, 1], [-4, 4]),
      0.4 + 0.4 * Math.sin(a * 6 + t),
      interpolate(a, [0, 0.4, 0.7, 1], [-3, -1, 1, 3]),
    ];
  });
  return (
    <>
      <ambientLight intensity={0.5} />
      <GridFloor />
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array(pts.flat()), 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial color={color} transparent opacity={0.9} />
      </line>
      <mesh position={[pts[pointCount - 1][0], pts[pointCount - 1][1] + 0.2, pts[pointCount - 1][2]]}>
        <sphereGeometry args={[0.14, 12, 12]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.5} />
      </mesh>
    </>
  );
};

const SceneEnd: React.FC<{ color: string }> = ({ color }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const r = 0.5 + 0.2 * Math.sin(t * 2);
  return (
    <>
      <ambientLight intensity={0.4} />
      <Stars count={160} />
      <mesh position={[0, 0, 0]}>
        <torusKnotGeometry args={[r, 0.22, 100, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} metalness={0.6} roughness={0.3} />
      </mesh>
    </>
  );
};

// ---------------------------------------------------------------------------
// 全中文角标覆盖层
// ---------------------------------------------------------------------------

const LowerThird: React.FC<{ text: string; sub?: string }> = ({ text, sub }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const appear = spring({ frame, fps, config: { damping: 16, stiffness: 90 } });
  const slide = interpolate(appear, [0, 1], [-30, 0]);
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "flex-start",
        padding: 50,
      }}
    >
      <div
        style={{
          transform: `translateY(${slide}px)`,
          opacity: appear,
          fontFamily: "Microsoft YaHei, Noto Sans SC, sans-serif",
          fontSize: 42,
          fontWeight: 800,
          color: "#F8FAFC",
          background: "rgba(8,15,38,0.78)",
          padding: "14px 26px",
          borderRadius: 10,
          maxWidth: 1300,
          lineHeight: 1.35,
        }}
      >
        {text}
      </div>
      {sub ? (
        <div
          style={{
            fontFamily: "Microsoft YaHei, Noto Sans SC, sans-serif",
            fontSize: 22,
            color: "#94A3B8",
            marginTop: 8,
            paddingLeft: 26,
            opacity: appear,
          }}
        >
          {sub}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// 主组件
// ---------------------------------------------------------------------------

export interface DefenseSegment {
  start: number;
  end: number;
  title: string;
  sub?: string;
}

export const DefenseSignalDefs: React.FC<{
  segments: DefenseSegment[];
  threeColor: string;
  audioSrc?: string;
}> = ({ segments, threeColor, audioSrc }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: "#05070f" }}>
      {segments.map((seg, i) => {
        const scene =
          i === 0 ? <SceneSignal color={threeColor} /> :
          i === 1 ? <SceneAnchors color={threeColor} /> :
          i === 2 ? <SceneRadar color={threeColor} /> :
          i === 3 ? <SceneMarch color={threeColor} /> :
          <SceneEnd color={threeColor} />;
        return (
          <Sequence
            key={i}
            from={Math.round(seg.start * fps)}
            durationInFrames={Math.round((seg.end - seg.start) * fps)}
          >
            <AbsoluteFill>
              <ThreeCanvas width={1920} height={1080} camera={{ position: [0, 2, 5], fov: 50 }}>
                {scene}
              </ThreeCanvas>
            </AbsoluteFill>
            <LowerThird text={seg.title} sub={seg.sub} />
          </Sequence>
        );
      })}
      {audioSrc ? <Audio src={audioSrc} /> : null}
    </AbsoluteFill>
  );
};