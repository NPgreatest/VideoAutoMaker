import React from 'react';
import {useCurrentFrame, interpolate, AbsoluteFill, spring, useVideoConfig, Img, staticFile, Html5Audio, Sequence} from 'remotion';
import { fontFamily } from './load-fonts';

export const FilterDesktopSlide: React.FC<{
  title: string;
  description: string;
  duration: number;
  imagePath?: string;
  titleStartTime?: number;
  soundEffect?: string;
}> = ({title, description, duration, imagePath = "openai.png", titleStartTime, soundEffect}) => {
  const SOUND_EFFECT_VOLUME = 1.8;
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  const totalFrames = duration * fps;
  
  // Calculate title timing - if no titleStartTime but has title, use 50%
  const titleStartFrame = titleStartTime 
    ? Math.floor((titleStartTime / 1000) * fps) 
    : (title ? Math.floor(totalFrames * 0.5) : Math.floor(totalFrames * 0.3));
  const titleEndFrame = Math.min(titleStartFrame + Math.floor(totalFrames * 0.1), totalFrames);
  
  // Calculate description timing (appears after title)
  const descriptionStartFrame = titleEndFrame;
  const descriptionEndFrame = Math.min(descriptionStartFrame + Math.floor(totalFrames * 0.1), totalFrames);
  
  // Ensure proper ordering
  const safeTitleStartFrame = Math.max(0, titleStartFrame);
  const safeTitleEndFrame = Math.max(safeTitleStartFrame + 1, titleEndFrame);
  const safeDescriptionStartFrame = Math.max(safeTitleEndFrame, descriptionStartFrame);
  const safeDescriptionEndFrame = Math.max(safeDescriptionStartFrame + 1, descriptionEndFrame);
  
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
        background: 'linear-gradient(135deg, #000000 0%, #1a1a1a 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: fontFamily,
        padding: '60px',
      }}
    >
      {/* Background decoration */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'radial-gradient(circle at 20% 80%, rgba(255,255,255,0.05) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(255,255,255,0.05) 0%, transparent 50%)',
        }}
      />
      
      {/* Centered Image */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: `translate(-50%, -50%) scale(${imageScale})`,
          opacity: imageOpacity,
          zIndex: 1,
        }}
      >
        <div
          style={{
            borderRadius: '25px',
            overflow: 'hidden',
            boxShadow: '0 40px 80px rgba(0,0,0,0.7)',
            background: 'white',
            padding: '20px',
            maxWidth: '90vw',
            width: '90vw',
          }}
        >
          <Img
            src={staticFile(`assets/${imagePath}`)}
            alt={title}
            style={{
              width: '100%',
              height: 'auto',
              maxHeight: '80vh',
              borderRadius: '20px',
              objectFit: 'contain',
              display: 'block',
            }}
          />
        </div>
      </div>

      {/* Centered Text Content - CSS FILTER APPROACH */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
          zIndex: 2,
          maxWidth: '90vw',
        }}
      >
        {/* Title - CSS Filter Drop Shadow (only render if title exists) */}
        {title && (
          <h1
            style={{
              opacity: titleOpacity,
              transform: `scale(${titleScale})`,
              fontSize: '72px',
              fontWeight: '900',
              color: 'white',
              margin: '0 0 15px 0',
              lineHeight: '1.0',
              letterSpacing: '-0.02em',
              // CSS FILTER APPROACH - Clean, modern, smooth rendering (weaker stroke)
              filter: 'drop-shadow(0 0 0 #000000) drop-shadow(-2px -2px 0 #000000) drop-shadow(2px -2px 0 #000000) drop-shadow(-2px 2px 0 #000000) drop-shadow(2px 2px 0 #000000)',
              WebkitTextStroke: 'none',
              textShadow: 'none',
            }}
          >
            {title}
          </h1>
        )}
        
        {/* Description - CSS Filter Drop Shadow (only render if description exists) */}
        {description && (
          <p
            style={{
              opacity: descriptionOpacity,
              transform: `translateY(${descriptionTranslateY}px)`,
              fontSize: '32px',
              lineHeight: '1.2',
              margin: '0',
              fontWeight: '600',
              color: 'white',
              // CSS FILTER APPROACH - Clean, modern, smooth rendering (weaker stroke)
              filter: 'drop-shadow(0 0 0 #000000) drop-shadow(-1px -1px 0 #000000) drop-shadow(1px -1px 0 #000000) drop-shadow(-1px 1px 0 #000000) drop-shadow(1px 1px 0 #000000)',
              WebkitTextStroke: 'none',
              textShadow: 'none',
            }}
          >
            {description}
          </p>
        )}
      </div>
      
      {/* Sound Effect (only render if soundEffect exists) - align start to title animation */}
      {soundEffect && (
        <Sequence from={safeTitleStartFrame}>
          <Html5Audio 
            src={staticFile(soundEffect)}
            volume={SOUND_EFFECT_VOLUME}
          />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};
