import React, {useCallback, useState} from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type CharacterOverlayLandscapeProps = {
  imagePath: string;
  imageIsVideo?: boolean;
  resizeRatio: number;
  position: {x: number; y: number};
  appear: boolean;
  appearFrom?: 'left' | 'right';
  duration: number;
  videoPath?: string;
};

export const CharacterOverlayLandscape: React.FC<CharacterOverlayLandscapeProps> = ({
  imagePath,
  imageIsVideo = false,
  resizeRatio,
  position,
  appear,
  appearFrom = 'left',
  duration,
  videoPath,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  const [videoErrored, setVideoErrored] = useState(false);

  const handleVideoError = useCallback((error: Error) => {
    console.warn('[CharacterOverlayLandscape] Background video failed to play:', error);
    setVideoErrored(true);
  }, []);

  const shouldShowVideo = Boolean(videoPath) && !videoErrored;

  const imageWidth = width * resizeRatio;
  const imageHeight = imageWidth;

  const imageX = width * position.x;
  const imageY = height * position.y;

  const slideAnimationFrames = 30;
  const slideStartOffset = appear ? (appearFrom === 'right' ? imageWidth : -imageWidth) : 0;
  const slideEndOffset = 0;

  const slideOffset = appear
    ? interpolate(
        frame,
        [0, slideAnimationFrames],
        [slideStartOffset, slideEndOffset],
        {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        },
      )
    : 0;

  const imageOpacity = appear
    ? interpolate(
        frame,
        [0, slideAnimationFrames],
        [0, 1],
        {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        },
      )
    : 1;

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'flex-start',
      }}
    >
      {shouldShowVideo ? (
        <AbsoluteFill>
          <OffthreadVideo
            src={staticFile(`assets/${videoPath}`)}
            muted
            onError={handleVideoError}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        </AbsoluteFill>
      ) : (
        <>
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'linear-gradient(135deg, #000000 0%, #1a1a1a 100%)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background:
                'radial-gradient(circle at 20% 80%, rgba(255,255,255,0.05) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(255,255,255,0.05) 0%, transparent 50%)',
            }}
          />
        </>
      )}

      <div
        style={{
          position: 'absolute',
          left: imageX,
          top: imageY,
          transform: `translateX(${slideOffset}px)`,
          opacity: imageOpacity,
          width: `${imageWidth}px`,
          height: `${imageHeight}px`,
          zIndex: 10,
        }}
      >
        {imageIsVideo ? (
          <OffthreadVideo
            src={staticFile(`assets/${imagePath}`)}
            muted
            transparent
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              backgroundColor: 'transparent',
            }}
          />
        ) : (
          <Img
            src={staticFile(`assets/${imagePath}`)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              display: 'block',
            }}
          />
        )}
      </div>
    </AbsoluteFill>
  );
};

export default CharacterOverlayLandscape;
