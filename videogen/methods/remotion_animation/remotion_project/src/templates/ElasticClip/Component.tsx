import React, {useMemo} from 'react';
import {
  AbsoluteFill,
  Sequence,
  Video,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type ElasticClipProps = {
  videoPath: string;
  duration: number; // seconds
  originalLength?: number; // seconds, default 5
};

export const ElasticClip: React.FC<ElasticClipProps> = ({
  videoPath,
  duration,
  originalLength = 5,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const totalFrames = Math.max(1, Math.floor(duration * fps));

  // Zones by duration
  const zone = duration < 4 ? 1 : duration <= 8 ? 2 : 3;

  // Constants
  const MAX_ZOOM_ZONE1 = 1.04;

  const Z2_MIN = 1.02;
  const Z2_MAX = 1.06;

  const Z3_END_MIN = 1.08;
  const Z3_END_MAX = 1.12;

  const videoSrc = staticFile(`assets/${videoPath}`);

  // Random zoom center (stable)
  const zoomCenter = useMemo(() => {
    let seed = 0;
    for (let i = 0; i < (videoPath || '').length; i++)
      seed = (seed * 31 + videoPath.charCodeAt(i)) % 100000;

    const rnd = () => {
      seed = (seed * 1664525 + 1013904223) % 0xffffffff;
      return (seed % 1000) / 1000;
    };
    return {
      x: 0.35 + rnd() * 0.30,
      y: 0.35 + rnd() * 0.30,
    };
  }, [videoPath]);

  if (!videoPath) {
    return <AbsoluteFill style={{background: 'black'}} />;
  }

  // ---------------------------------------
  // ZONE 1 (<4 seconds)
  // ---------------------------------------
  if (zone === 1) {
    return (
      <AbsoluteFill>
        <Sequence from={0} durationInFrames={totalFrames}>
          <AbsoluteFill
            style={{
              transform: `scale(${MAX_ZOOM_ZONE1})`,
            }}
          >
            <Video
              src={videoSrc}
              style={{width: '100%', height: '100%', objectFit: 'cover'}}
            />
          </AbsoluteFill>
        </Sequence>
      </AbsoluteFill>
    );
  }

  // ---------------------------------------
  // ZONE 2 (4-8 seconds)
  // ---------------------------------------
  if (zone === 2) {
    const playbackRate = originalLength / Math.max(0.0001, duration);

    const t = Math.min(1, Math.max(0, (duration - 4) / 4));
    const endScale = Z2_MIN + t * (Z2_MAX - Z2_MIN);

    const scale = interpolate(frame, [0, totalFrames], [1, endScale], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });

    return (
      <AbsoluteFill>
        <Sequence from={0} durationInFrames={totalFrames}>
          <AbsoluteFill style={{transform: `scale(${scale})`}}>
            <Video
              src={videoSrc}
              playbackRate={playbackRate}
              style={{width: '100%', height: '100%', objectFit: 'cover'}}
            />
          </AbsoluteFill>
        </Sequence>
      </AbsoluteFill>
    );
  }

  // ---------------------------------------
  // ZONE 3 (>8 seconds)
  // First 70% play normally, last 30% freeze & zoom
  // ---------------------------------------
  const firstFrames = Math.floor(totalFrames * 0.7);
  const lastFrames = totalFrames - firstFrames;

  // Final freeze frame index (last frame of original video)
  const freezeFrame = Math.max(0, Math.floor(originalLength * fps) - 1);

  const localFrame = Math.max(0, frame - firstFrames);
  const endZoom = Z3_END_MIN + Math.random() * (Z3_END_MAX - Z3_END_MIN);

  const lastScale = interpolate(localFrame, [0, Math.max(1, lastFrames)], [1, endZoom], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const transformOrigin = `${Math.round(zoomCenter.x * 100)}% ${Math.round(
    zoomCenter.y * 100
  )}%`;

  return (
    <AbsoluteFill>
      {/* First 70% */}
      <Sequence from={0} durationInFrames={firstFrames}>
        <AbsoluteFill>
          <Video
            src={videoSrc}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </AbsoluteFill>
      </Sequence>

      {/* Last 30% freeze */}
      <Sequence from={firstFrames} durationInFrames={lastFrames}>
        <AbsoluteFill
          style={{
            transform: `scale(${lastScale})`,
            transformOrigin,
          }}
        >
          <Video
            src={videoSrc}
            frame={freezeFrame} // ⭐ Freeze to this frame (safe)
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};

export default ElasticClip;
