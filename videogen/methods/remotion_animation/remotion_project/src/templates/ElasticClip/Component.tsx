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
  const zone = duration < 4 ? 1 : duration <= 8 ? 2 : 3;

  // Defaults
  const MAX_ZOOM_ZONE1 = 1.04;
  const Z2_MIN = 1.02;
  const Z2_MAX = 1.06;
  const Z3_END_MIN = 1.08;
  const Z3_END_MAX = 1.12;

  const videoSrc = staticFile(`assets/${videoPath}`);

  // Stable center inside middle region
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

  if (!videoPath) return <AbsoluteFill style={{background: 'black'}} />;

  // ---------------------------------------
  // 1) Zone 1: duration < 4s
  // ---------------------------------------
  if (zone === 1) {
    return (
      <AbsoluteFill>
        <Sequence from={0} durationInFrames={totalFrames}>
          <AbsoluteFill style={{transform: `scale(${MAX_ZOOM_ZONE1})`}}>
            <Video
              src={videoSrc}
              loop={false}   // IMPORTANT: prevent repeat!
              startFrom={0}
              endAt={Math.floor(duration * fps)} // trim to exact duration
              style={{width: '100%', height: '100%', objectFit: 'cover'}}
            />
          </AbsoluteFill>
        </Sequence>
      </AbsoluteFill>
    );
  }

  // ---------------------------------------
  // 2) Zone 2: 4s ≤ duration ≤ 8s
  // ---------------------------------------
  if (zone === 2) {
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
              loop={false}   // prevent second playback
              startFrom={0}
              endAt={Math.floor(originalLength * fps)} // original full video only once
              style={{width: '100%', height: '100%', objectFit: 'cover'}}
            />
          </AbsoluteFill>
        </Sequence>
      </AbsoluteFill>
    );
  }

  // ---------------------------------------
  // 3) Zone 3: duration > 8s
  // ---------------------------------------
  const firstFrames = Math.floor(totalFrames * 0.7);
  const lastFrames = totalFrames - firstFrames;

  const freezeFrame = Math.max(0, Math.floor(originalLength * fps) - 1);

  // Zoom animation for last 30%
  const localFrame = Math.max(0, frame - firstFrames);
  const endZoom = Z3_END_MIN + Math.random() * (Z3_END_MAX - Z3_END_MIN);

  const lastScale = interpolate(
    localFrame,
    [0, Math.max(1, lastFrames)],
    [1, endZoom],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  );

  const transformOrigin = `${Math.round(zoomCenter.x * 100)}% ${Math.round(
    zoomCenter.y * 100
  )}%`;

  return (
    <AbsoluteFill>
      {/* First 70% — play original video once */}
      <Sequence from={0} durationInFrames={firstFrames}>
        <AbsoluteFill>
          <Video
            src={videoSrc}
            loop={false}   // ❗ absolutely required to prevent replay
            startFrom={0}
            endAt={Math.floor(originalLength * fps)}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </AbsoluteFill>
      </Sequence>

      {/* Last 30% — freeze final frame & zoom */}
      <Sequence from={firstFrames} durationInFrames={lastFrames}>
        <AbsoluteFill
          style={{
            transform: `scale(${lastScale})`,
            transformOrigin,
          }}
        >
          <Video
            src={videoSrc}
            frame={freezeFrame}  // freeze
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
