import React from 'react';
import { AbsoluteFill, Video, staticFile, useVideoConfig } from 'remotion';

export const ElasticClip = ({ videoPath, duration, originalLength = 5 }) => {
  const { fps } = useVideoConfig();

  const totalFrames = duration * fps;
  const originalFrames = originalLength * fps;

  // 根据目标时长计算倍率
  // rate = 视频原长度 / 需要长度
  const rate = originalFrames / totalFrames;

  // 限制速度范围（可调）
  let playbackRate = rate;
  if (duration < 5) playbackRate = Math.min(rate, 2.0);    // 快放上限
  else if (duration <= 8) playbackRate = Math.max(rate, 0.6);
  else playbackRate = Math.max(rate, 0.3);                 // >8s 更慢即可

  return (
    <AbsoluteFill>
      <Video
        src={staticFile(`assets/${videoPath}`)}
        playbackRate={playbackRate}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
        }}
      />
    </AbsoluteFill>
  );
};
