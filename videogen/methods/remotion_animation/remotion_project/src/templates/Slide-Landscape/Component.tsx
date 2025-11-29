import React, {useCallback, useState} from 'react';
import {
  AbsoluteFill,
  Html5Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {fontFamily} from '../../load-fonts';

export type SlideLandscapeProps = {
  title: string;
  description: string;
  duration: number;
  imagePath?: string;
  videoPath?: string;
  imageMode?: 'top' | 'center' | 'cover';
  soundEffect?: string;
  appear?: boolean;
};

export const SlideLandscape: React.FC<SlideLandscapeProps> = ({
  title,
  description,
  duration,
  imagePath = '',
  videoPath,
  imageMode = 'top',
  soundEffect,
  appear = false,
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const totalFrames = duration * fps;

  const hasImage = imagePath !== '';
  const hasTitle = title !== '';

  // ========== Animations ==========
  const imageOpacity = appear
    ? 1
    : interpolate(frame, [0, 25], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  const imageScale = appear
    ? 1
    : spring({
        fps,
        frame: Math.max(0, frame - 10),
        config: {damping: 200},
        from: 0.96,
        to: 1,
      });

  const titleOpacity = appear
    ? 1
    : interpolate(frame, [10, 40], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  const titleScale = appear
    ? 1
    : spring({
        fps,
        frame: Math.max(0, frame - 10),
        config: {damping: 200},
        from: 0.92,
        to: 1,
      });

  const descriptionOpacity = appear
    ? 1
    : interpolate(frame, [40, 70], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  const descriptionTranslateY = appear
    ? 0
    : interpolate(frame, [40, 70], [30, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  // Text size auto scale
  const targetWidth = width * 0.8;
  const estimatedCharWidth = 0.55;
  const titleFontSize = Math.min(
    Math.floor(targetWidth / (title.length * estimatedCharWidth)),
    90,
  );
  const descriptionFontSize = Math.floor(titleFontSize * 0.45);

  // ========== Video background ==========
  const [videoErrored, setVideoErrored] = useState(false);

  const handleVideoError = useCallback((error: Error) => {
    console.warn('[SlideLandscape] Background video failed:', error);
    setVideoErrored(true);
  }, []);

  const shouldShowVideo = Boolean(videoPath) && !videoErrored;

  return (
    <AbsoluteFill style={{fontFamily}}>
      {/* Background */}
      {shouldShowVideo ? (
        <AbsoluteFill>
          <OffthreadVideo
            src={staticFile(`assets/${videoPath}`)}
            muted
            onError={handleVideoError}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{backgroundColor: 'black'}} />
      )}

      {/* Content Layer */}
      <AbsoluteFill
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent:
            !hasImage && hasTitle
              ? 'center' // title-only
              : hasImage && !hasTitle
              ? 'center' // image-only
              : 'flex-start', // image + title
          paddingTop:
            hasImage && hasTitle && imageMode === 'top'
              ? '5vh'
              : 0,
          textAlign: 'center',
          zIndex: 2,
        }}
      >
        {/* IMAGE */}
        {hasImage && (
          <Img
            src={staticFile(`assets/${imagePath}`)}
            style={{
              width:
                imageMode === 'cover'
                  ? '100%'
                  : hasTitle
                  ? '85vw'
                  : '70vw',
              height:
                imageMode === 'cover'
                  ? '100%'
                  : hasTitle
                  ? '45vh'
                  : '70vh',
              objectFit: imageMode === 'cover' ? 'cover' : 'contain',
              opacity: imageOpacity,
              transform: `scale(${imageScale})`,
              borderRadius: imageMode === 'cover' ? 0 : 20,
              marginBottom: hasTitle ? '3vh' : 0,
            }}
          />
        )}

        {/* TITLE */}
        {hasTitle && (
          <h1
            style={{
              opacity: titleOpacity,
              transform: `scale(${titleScale})`,
              fontSize: `${titleFontSize}px`,
              fontWeight: 900,
              color: 'white',
              margin: hasImage ? '0 0 20px 0' : 0,
              maxWidth: '90vw',
              lineHeight: '1.1',
              letterSpacing: '-0.01em',
            }}
          >
            {title}
          </h1>
        )}

        {/* DESCRIPTION (only when both image + title exist) */}
        {hasImage && hasTitle && description && (
          <p
            style={{
              opacity: descriptionOpacity,
              transform: `translateY(${descriptionTranslateY}px)`,
              fontSize: `${descriptionFontSize}px`,
              color: 'white',
              margin: 0,
              fontWeight: 600,
              maxWidth: '90vw',
            }}
          >
            {description}
          </p>
        )}
      </AbsoluteFill>

      {/* Sound Effect */}
      {soundEffect && (
        <Sequence from={10}>
          <Html5Audio src={staticFile(soundEffect)} volume={1.0} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

export default SlideLandscape;
