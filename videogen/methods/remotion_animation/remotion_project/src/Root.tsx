import {Composition} from 'remotion';
import {FilterDesktopSlide} from './FilterDesktopSlide';
import {FilterTikTokSlide} from './FilterTikTokSlide';
import './load-fonts'; // Load fonts

export const Root: React.FC = () => {
  return (
    <>
      {/* CSS Filter Desktop Format (16:9) - Modern Approach */}
      <Composition
        id="FilterDesktopSlide"
        component={FilterDesktopSlide}
        durationInFrames={150}
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
        durationInFrames={150}
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
    </>
  );
};