type Assets = Record<string, string | undefined>;

const DEFAULT_SOUND = '';

const coerceNumber = (value: any, fallback: number): number => {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const pickField = <T>(config: any, keys: string[], fallback: T): T => {
  for (const key of keys) {
    if (config && config[key] !== undefined) {
      return config[key];
    }
    if (config?.data && config.data[key] !== undefined) {
      return config.data[key];
    }
  }
  return fallback;
};

export const previewProps = {
  title: 'Title',
  description: 'Description goes here',
  duration: 5,
  imagePath: undefined,
  videoPath: undefined,
  titleStartTime: 1500,
  soundEffect: DEFAULT_SOUND,
  appear: false,

  // 🔥 新增预览
  imageMode: 'top',
};

export function buildProps(config: any, assets: Assets) {
  const durationMs = pickField(config, ['duration_ms', 'durationMs'], undefined);

  const duration =
    config?.duration_sec ??
    config?.duration ??
    (durationMs !== undefined ? durationMs / 1000 : undefined) ??
    (config?.data?.duration_ms !== undefined ? config.data.duration_ms / 1000 : undefined);

  const safeDuration = coerceNumber(duration, previewProps.duration);

  const imagePath = assets.image || undefined;

  const title = pickField(config, ['title'], '');
  const description = pickField(config, ['description'], '');
  const soundEffect = pickField(config, ['sound_effect', 'soundEffect'], DEFAULT_SOUND);

  const titleStartTime =
    config?.title_start_time ??
    config?.titleStartTime ??
    (config?.data?.title_start_time ?? config?.data?.titleStartTime);


    return {
    title,
    description,
    duration: safeDuration,
    imagePath,
    videoPath: assets.video,
    titleStartTime: coerceNumber(
      titleStartTime,
      Math.floor(safeDuration * 0.5 * 1000),
    ),
    soundEffect,
    appear: pickField<boolean>(config, ['appear'], previewProps.appear),

    // 🔥 新增 imageMode 支持
    imageMode: pickField(config, ['image_mode', 'imageMode'], previewProps.imageMode),
  };
}
