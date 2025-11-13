import React from 'react';
import {
  useCurrentFrame,
  interpolate,
  AbsoluteFill,
  spring,
  useVideoConfig,
  Img,
  staticFile,
  Html5Audio,
  Sequence,
  Video
} from 'remotion';
import { fontFamily } from './load-fonts';

export const FilterTikTokSlide: React.FC<{
  title: string;
  description: string;
  duration: number;
  imagePath?: string;
  videoPath?: string;
  titleStartTime?: number;
  soundEffect?: string;
}> = ({
  title,
  description,
  duration,
  imagePath = 'openai.png',
  videoPath,
  titleStartTime,
  soundEffect
}) => {
  const SOUND_EFFECT_VOLUME = 1.8;
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  const totalFrames = duration * fps;

  // Calculate title timing
  const titleStartFrame = titleStartTime
    ? Math.floor((titleStartTime / 1000) * fps)
    : title
    ? Math.floor(totalFrames * 0.5)
    : Math.floor(totalFrames * 0.3);
  const titleEndFrame = Math.min(titleStartFrame + Math.floor(totalFrames * 0.1), totalFrames);

  const descriptionStartFrame = titleEndFrame;
  const descriptionEndFrame = Math.min(descriptionStartFrame + Math.floor(totalFrames * 0.1), totalFrames);

  const safeTitleStartFrame = Math.max(0, titleStartFrame);
  const safeTitleEndFrame = Math.max(safeTitleStartFrame + 1, titleEndFrame);
  const safeDescriptionStartFrame = Math.max(safeTitleEndFrame, descriptionStartFrame);
  const safeDescriptionEndFrame = Math.max(safeDescriptionStartFrame + 1, descriptionEndFrame);

  // Dynamic font sizing
  const targetWidth = width * 0.8;
  const estimatedCharWidth = 0.6;
  const titleFontSize = Math.min(Math.floor(targetWidth / (title.length * estimatedCharWidth)), 120);
  const descriptionFontSize = Math.floor(titleFontSize * 0.5);

  // Animations
  const imageOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const imageScale = spring({
    fps,
    frame: Math.max(0, frame - 10),
    config: { damping: 200 },
    from: 0.95,
    to: 1,
  });

  const descriptionOpacity = interpolate(frame, [safeDescriptionStartFrame, safeDescriptionEndFrame], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const descriptionTranslateY = interpolate(frame, [safeDescriptionStartFrame, safeDescriptionEndFrame], [30, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const titleOpacity = interpolate(frame, [safeTitleStartFrame, safeTitleEndFrame], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const titleScale = spring({
    fps,
    frame: Math.max(0, frame - safeTitleStartFrame),
    config: { damping: 200 },
    from: 0.9,
    to: 1,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: fontFamily,
        padding: '40px',
      }}
    >
      {/* Background Video (if provided) */}
      {videoPath ? (
        <AbsoluteFill>
          <Video
            src={staticFile(`assets/${videoPath}`)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </AbsoluteFill>
      ) : (
        <>
          {/* Fallback background */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'linear-gradient(135deg, #000000 0%, #1a1a1a 100%)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background:
                'radial-gradient(circle at 20% 80%, rgba(255,255,255,0.05) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(255,255,255,0.05) 0%, transparent 50%)',
            }}
          />
        </>
      )}

      {/* Enlarged Center Image */}
      <div
        style={{
          position: 'absolute',
          top: '0%', // starts from top
          left: '50%',
          transform: `translateX(-50%) scale(${imageScale})`,
          opacity: imageOpacity,
          zIndex: 1,
          width: '90%',  // 90% screen width
          height: '50%', // occupy upper half
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Img
          src={staticFile(`assets/${imagePath}`)}
          alt={title}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            borderRadius: '0px',
            display: 'block',
          }}
        />
      </div>

      {/* Text content */}
      <div
        style={{
          position: 'absolute',
          top: '65%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
          zIndex: 2,
          maxWidth: '90vw',
        }}
      >
        {title && (
          <h1
            style={{
              opacity: titleOpacity,
              transform: `scale(${titleScale})`,
              fontSize: `${titleFontSize}px`,
              fontWeight: '900',
              color: 'white',
              margin: '0 0 12px 0',
              lineHeight: '1.0',
              letterSpacing: '-0.02em',
              filter:
                'drop-shadow(0 0 0 #000000) drop-shadow(-2px -2px 0 #000000) drop-shadow(2px -2px 0 #000000) drop-shadow(-2px 2px 0 #000000) drop-shadow(2px 2px 0 #000000)',
              WebkitTextStroke: 'none',
              textShadow: 'none',
            }}
          >
            {title}
          </h1>
        )}

        {description && (
          <p
            style={{
              opacity: descriptionOpacity,
              transform: `translateY(${descriptionTranslateY}px)`,
              fontSize: `${descriptionFontSize}px`,
              lineHeight: '1.2',
              margin: '0',
              fontWeight: '600',
              color: 'white',
              filter:
                'drop-shadow(0 0 0 #000000) drop-shadow(-1px -1px 0 #000000) drop-shadow(1px -1px 0 #000000) drop-shadow(-1px 1px 0 #000000) drop-shadow(1px 1px 0 #000000)',
              WebkitTextStroke: 'none',
              textShadow: 'none',
            }}
          >
            {description}
          </p>
        )}
      </div>

      {/* Sound effect */}
      {soundEffect && (
        <Sequence from={safeTitleStartFrame}>
          <Html5Audio src={staticFile(soundEffect)} volume={SOUND_EFFECT_VOLUME} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};
