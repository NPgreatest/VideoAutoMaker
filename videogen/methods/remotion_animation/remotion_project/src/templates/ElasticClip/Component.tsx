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
  const {fps, width, height} = useVideoConfig();

  const totalFrames = Math.max(1, Math.floor(duration * fps));

  // Zones
  const zone = duration < 4 ? 1 : duration <= 8 ? 2 : 3;

  // Common scales (chosen sane defaults)
  const MAX_ZOOM_ZONE1 = 1.04; // for <4s constant zoom

  // zone 2 zoom range endpoints (used to compute end scale)
  const Z2_MIN = 1.02;
  const Z2_MAX = 1.06;

  // zone 3 final zoom (freeze) end scale
  const Z3_END_MIN = 1.08;
  const Z3_END_MAX = 1.12;

  // Helpers
  const videoSrc = staticFile(`assets/${videoPath}`);

  // Randomized zoom center for zone 3 (freeze). Keep stable per videoPath.
  const zoomCenter = useMemo(() => {
    // Simple deterministic-ish seed from videoPath
    let seed = 0;
    for (let i = 0; i < (videoPath || '').length; i++) seed = (seed * 31 + videoPath.charCodeAt(i)) % 100000;
    const rnd = (n: number) => {
      seed = (seed * 1664525 + 1013904223) % 0xffffffff;
      return (seed % 1000) / 1000;
    };
    const x = 0.35 + rnd(1) * (0.65 - 0.35);
    const y = 0.35 + rnd(2) * (0.65 - 0.35);
    return {x, y};
  }, [videoPath]);

  if (!videoPath) {
    return <AbsoluteFill style={{background: 'black'}} />;
  }

  // Render per zone
  if (zone === 1) {
    // duration < 4: play original at natural speed, trim by Sequence length, constant max zoom
    return (
      <AbsoluteFill>
        <Sequence from={0} durationInFrames={totalFrames}>
          <AbsoluteFill style={{transform: `scale(${MAX_ZOOM_ZONE1})`}}>
            <Video
              src={videoSrc}
              style={{width: '100%', height: '100%', objectFit: 'cover'}}
            />
          </AbsoluteFill>
        </Sequence>
      </AbsoluteFill>
    );
  }

  if (zone === 2) {
    // 4-8s: play original video for entire duration (allow speed change), progressive zoom
    const playbackRate = originalLength / Math.max(0.0001, duration);

    // compute end scale proportional to duration within [4,8]
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

  // zone 3: duration > 8s
  // First 70%: play original normally. Last 30%: freeze final frame and zoom-in from ~1.0 to ~1.08-1.12
  const firstFrames = Math.floor(totalFrames * 0.7);
  const lastFrames = totalFrames - firstFrames;

  // choose end zoom in reasonable range
  const endZoom = Z3_END_MIN + Math.random() * (Z3_END_MAX - Z3_END_MIN);

  // last segment local frame
  const localFrame = Math.max(0, frame - firstFrames);

  const lastScale = interpolate(localFrame, [0, Math.max(1, lastFrames)], [1, endZoom], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const transformOrigin = `${Math.round(zoomCenter.x * 100)}% ${Math.round(zoomCenter.y * 100)}%`;

  return (
    <AbsoluteFill>
      {/* First segment: play original normally */}
      <Sequence from={0} durationInFrames={firstFrames}>
        <AbsoluteFill>
          <Video src={videoSrc} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </AbsoluteFill>
      </Sequence>

      {/* Last segment: show the final frame (freeze) and zoom-in */}
      <Sequence from={firstFrames} durationInFrames={lastFrames}>
        <AbsoluteFill
          style={{
            transform: `scale(${lastScale})`,
            transformOrigin,
          }}
        >
          {/* Show the video but pinned to its last frame by seeking near its end.
              We set playbackRate to 0 and startFrom to (originalLength - 1/fps) so the
              player renders the last frame during this sequence. */}
          <Video
            src={videoSrc}
            startFrom={Math.max(0, originalLength - 1 / fps)}
            playbackRate={0}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};

export default ElasticClip;
