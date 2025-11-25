import React from 'react';
import {Composition} from 'remotion';
import './load-fonts';
import {templates} from './templates';

const basePreviewProps = {
  title: 'Title',
  description: 'Description',
  duration: 5,
  imagePath: 'openai.png',
  videoPath: undefined,
  titleStartTime: 1500,
  soundEffect: '',
  imageIsVideo: false,
  resizeRatio: 0.2,
  position: {x: 0.05, y: 0.7},
  appear: true,
  appearFrom: 'left',
};

export const Root: React.FC = () => (
  <>
    {templates.map((template) => (
      <Composition
        key={template.name}
        id={template.name}
        component={template.Component}
        durationInFrames={template.fps * 600}
        width={template.width}
        height={template.height}
        fps={template.fps}
        defaultProps={(template.previewProps || basePreviewProps) as any}
      />
    ))}
  </>
);
