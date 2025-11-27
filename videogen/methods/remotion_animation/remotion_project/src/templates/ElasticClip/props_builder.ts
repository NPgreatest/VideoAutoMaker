type Assets = Record<string, string | undefined>;

const coerceNumber = (value: any, fallback: number): number => {
  if (value === null || value === undefined || value === '') return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const pickField = (config: any, keys: string[], fallback: any) => {
  for (const key of keys) {
    if (config && config[key] !== undefined) return config[key];
    if (config?.data && config.data[key] !== undefined) return config.data[key];
  }
  return fallback;
};

export const previewProps = {
  videoPath: undefined,
  duration: 5,
  originalLength: 5,
};

export function buildProps(config: any, assets: Assets) {
  const durationMs = pickField(config, ['duration_ms', 'durationMs'], undefined);

  const duration =
    config?.duration_sec ??
    config?.duration ??
    (durationMs !== undefined ? durationMs / 1000 : undefined) ??
    (config?.data?.duration_ms !== undefined ? config.data.duration_ms / 1000 : undefined);

  const safeDuration = coerceNumber(duration, previewProps.duration);

  const originalLength = coerceNumber(pickField(config, ['original_length', 'originalLength'], undefined), previewProps.originalLength);

  return {
    videoPath: assets.video,
    duration: safeDuration,
    originalLength,
  };
}
