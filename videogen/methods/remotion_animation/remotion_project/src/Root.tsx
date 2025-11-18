import React from 'react';
import {Composition} from 'remotion';
import {FilterDesktopSlide} from './FilterDesktopSlide';
import {FilterTikTokSlide} from './FilterTikTokSlide';
import {OverlapCharacter} from './OverlapCharacter';
import {OverlapCharacterTiktok} from './OverlapCharacterTiktok';
import './load-fonts'; // Load fonts

export const Root: React.FC = () => {
  return (
    <>
      {/* CSS Filter Desktop Format (16:9) - Modern Approach */}
      <Composition
        id="FilterDesktopSlide"
        component={FilterDesktopSlide}
        durationInFrames={1000}
        width={1920}
        height={1080}
        fps={30}
        defaultProps={{
          title: 'AI Technology',
          description: 'Advanced artificial intelligence technology that transforms how we work and create.',
          duration: 5,
          imagePath: 'openai.png',
          titleStartTime: 1500,
          soundEffect: 'dong_effect.wav'
        }}
      />
      
      {/* CSS Filter TikTok Format (9:16) - Modern Approach */}
      <Composition
        id="FilterTikTokSlide"
        component={FilterTikTokSlide}
        durationInFrames={1000}
        width={1080}
        height={1920}
        fps={30}
        defaultProps={{
          title: 'AI Technology',
          description: 'Advanced artificial intelligence technology that transforms how we work and create.',
          duration: 5,
          imagePath: 'openai.png',
          titleStartTime: 1500,
          soundEffect: 'dong_effect.wav'
        }}
      />
      
      {/* Overlap Character - Character overlay with slide animation */}
      <Composition
        id="OverlapCharacter"
        component={OverlapCharacter}
        durationInFrames={1000}
        width={1920}
        height={1080}
        fps={30}
        defaultProps={{
          imagePath: 'openai.png',
          resizeRatio: 0.15,
          position: { x: 0.02, y: 0.78 },
          appear: true,
          duration: 5,
          videoPath: undefined
        }}
      />

      {/* Overlap Character TikTok - 9:16 character overlay */}
      <Composition
        id="OverlapCharacterTiktok"
        component={OverlapCharacterTiktok}
        durationInFrames={1000}
        width={1080}
        height={1920}
        fps={30}
        defaultProps={{
          imagePath: 'openai.png',
          resizeRatio: 0.25,
          position: {x: 0.05, y: 0.65},
          appear: true,
          duration: 5,
          videoPath: undefined
        }}
      />
    </>
  );
};