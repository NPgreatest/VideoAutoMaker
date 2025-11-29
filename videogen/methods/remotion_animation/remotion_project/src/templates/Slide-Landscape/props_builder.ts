// props_builder.ts
type Assets = Record<string, string | undefined>;

const DEFAULT_IMAGE = '';
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
  title: 'Sample Title',
  description: '',
  duration: 5,
  imagePath: '',
  videoPath: undefined,
  imageMode: 'top',
  soundEffect: '',
  appear: false,
};

export function buildProps(config: any, assets: Assets) {
  const durationMs = pickField<number | undefined>(config, ['duration_ms', 'durationMs'], undefined);
  const duration =
    config?.duration_sec ??
    config?.duration ??
    (durationMs !== undefined ? durationMs / 1000 : undefined) ??
    (config?.data?.duration_ms !== undefined ? config.data.duration_ms / 1000 : undefined);

  const safeDuration = coerceNumber(duration, previewProps.duration);

  return {
    title: pickField<string>(config, ['title'], ''),
    description: pickField<string>(config, ['description'], ''),
    duration: safeDuration,
    imagePath: assets.image ?? '',
    videoPath: assets.video,
    imageMode: pickField<string>(config, ['image_mode', 'imageMode'], 'top'),
    soundEffect: pickField<string>(config, ['sound_effect', 'soundEffect'], ''),
    appear: pickField<boolean>(config, ['appear'], previewProps.appear),
  };
}
