import React from 'react';
import {
  AbsoluteFill,
  Html5Audio,
  Img,
  Sequence,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {fontFamily} from '../../load-fonts';

export type SlidePortraitProps = {
  title: string;
  description: string;
  duration: number;
  imagePath?: string;
  videoPath?: string;
  titleStartTime?: number;
  soundEffect?: string;
  appear?: boolean;

  imageMode?: 'top' | 'center' | 'cover';
};

export const SlidePortrait: React.FC<SlidePortraitProps> = ({
  title,
  description,
  duration,
  imagePath,
  videoPath,
  titleStartTime,
  soundEffect,
  appear = false,

  // 🔥 默认 top（与 Landscape 一致）
  imageMode = 'top',
}) => {
  const SOUND_EFFECT_VOLUME = 1.8;
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();

  const totalFrames = duration * fps;

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

  const targetWidth = width * 0.8;
  const estimatedCharWidth = 0.6;
  const titleFontSize = Math.min(Math.floor(targetWidth / (title.length * estimatedCharWidth)), 120);
  const descriptionFontSize = Math.floor(titleFontSize * 0.5);

  const imageOpacity = appear
    ? 1
    : interpolate(frame, [0, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const imageScale = appear
    ? 1
    : spring({
        fps,
        frame: Math.max(0, frame - 10),
        config: {damping: 200},
        from: 0.95,
        to: 1,
      });

  const descriptionOpacity = appear
    ? 1
    : interpolate(frame, [safeDescriptionStartFrame, safeDescriptionEndFrame], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  const descriptionTranslateY = appear
    ? 0
    : interpolate(frame, [safeDescriptionStartFrame, safeDescriptionEndFrame], [30, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  const titleOpacity = appear
    ? 1
    : interpolate(frame, [safeTitleStartFrame, safeTitleEndFrame], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  const titleScale = appear
    ? 1
    : spring({
        fps,
        frame: Math.max(0, frame - safeTitleStartFrame),
        config: {damping: 200},
        from: 0.9,
        to: 1,
      });

const getImageWrapperStyle = () => {
  if (!imagePath) return {};

  if (imageMode === 'cover') {
    return {
      position: 'absolute' as const,
      inset: 0,
      zIndex: 1,
      opacity: imageOpacity,
      transform: `scale(${imageScale})`,
    };
  }

  if (imageMode === 'center') {
    return {
      position: 'absolute' as const,
      top: '45%',
      left: '50%',
      transform: `translate(-50%, -50%) scale(${imageScale})`,
      opacity: imageOpacity,
      zIndex: 1,
      width: '90%',
      height: '65%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    };
  }

  // top
  return {
    position: 'absolute' as const,
    top: '0%',
    left: '50%',
    transform: `translateX(-50%) scale(${imageScale})`,
    opacity: imageOpacity,
    zIndex: 1,
    width: '90%',
    height: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };
};


    const getImageStyle = () => {
      if (imageMode === 'cover') {
        return {
          width: '100%',
          height: '100%',
          objectFit: 'cover' as const,   // ←🔥 必须加 as const
        };
      }

      return {
        width: '100%',
        height: '100%',
        objectFit: 'contain' as const,  // ←🔥 必须加 as const
        display: 'block',
      };
    };


  const getTextTopOffset = () => {
    if (!imagePath) return '50%';
    if (imageMode === 'center') return '80%';
    if (imageMode === 'cover') return '50%';
    return '65%'; // top
  };
  // =========================================================

  // @ts-ignore
    // @ts-ignore
    return (
    <AbsoluteFill
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily,
        padding: '40px',
      }}
    >
      {videoPath ? (
        <AbsoluteFill>
          <Video
            src={staticFile(`assets/${videoPath}`)}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </AbsoluteFill>
      ) : (
        <>
          <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(135deg,#000,#1a1a1a)'}} />
          <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(circle at 20% 80%, rgba(255,255,255,0.05), transparent 50%)'}} />
        </>
      )}

      {/* 🔥 图片 */}
      {imagePath && (
        <div style={getImageWrapperStyle()}>
          <Img src={staticFile(`assets/${imagePath}`)} alt={title} style={getImageStyle()} />
        </div>
      )}

      {/* 文案层 */}
      <div
        style={{
          position: 'absolute',
          top: getTextTopOffset(),
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
          zIndex: 3,
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
              margin: 0,
              fontWeight: '600',
              color: 'white',
            }}
          >
            {description}
          </p>
        )}
      </div>

      {soundEffect && (
        <Sequence from={safeTitleStartFrame}>
          <Html5Audio src={staticFile(soundEffect)} volume={SOUND_EFFECT_VOLUME} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

export default SlidePortrait;
