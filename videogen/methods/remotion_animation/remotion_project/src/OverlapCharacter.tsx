import React, { useCallback, useState } from 'react';
import {
  useCurrentFrame,
  interpolate,
  AbsoluteFill,
  spring,
  useVideoConfig,
  Img,
  staticFile,
  OffthreadVideo,
} from 'remotion';

export const OverlapCharacter: React.FC<{
  imagePath: string;
  resizeRatio: number;
  position: { x: number; y: number };
  appear: boolean;
  duration: number;
  videoPath?: string;
}> = ({
  imagePath,
  resizeRatio,
  position,
  appear,
  duration,
  videoPath,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const totalFrames = duration * fps;

  const [videoErrored, setVideoErrored] = useState(false);

  const handleVideoError = useCallback((error: Error) => {
    console.warn('[OverlapCharacter] Background video failed to play:', error);
    setVideoErrored(true);
  }, []);

  const shouldShowVideo = Boolean(videoPath) && !videoErrored;

  // Calculate image dimensions based on resize ratio
  const imageWidth = width * resizeRatio;
  // We'll maintain aspect ratio, so we need to get the image's natural aspect ratio
  // For now, we'll use a default aspect ratio or calculate it from the image
  // Since we can't easily get image dimensions in Remotion, we'll use a square default
  // The actual aspect ratio will be maintained by objectFit: 'contain'
  const imageHeight = imageWidth; // Will be adjusted by objectFit

  // Calculate position in pixels
  const imageX = width * position.x;
  const imageY = height * position.y;

  // Slide animation from left if appear is true
  const slideAnimationFrames = 30; // 1 second at 30fps
  
  // Calculate slide animation: start from left (negative position) and slide to target position
  const slideStartOffset = appear ? -imageWidth : 0;
  const slideEndOffset = 0;

  const slideOffset = appear
    ? interpolate(
        frame,
        [0, slideAnimationFrames],
        [slideStartOffset, slideEndOffset],
        {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        }
      )
    : 0;

  // Optional: Add opacity animation when appearing
  const imageOpacity = appear
    ? interpolate(
        frame,
        [0, slideAnimationFrames],
        [0, 1],
        {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        }
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
      {/* Background Video */}
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

      {/* Character Image */}
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
        <Img
          src={staticFile(`assets/${imagePath}`)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            display: 'block',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

