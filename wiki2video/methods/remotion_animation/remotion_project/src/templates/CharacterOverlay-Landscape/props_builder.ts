type Assets = Record<string, string | undefined>;

const DEFAULT_IMAGE = 'openai.png';
const VIDEO_EXTENSIONS = /\.(mp4|mov|webm|mkv)$/i;

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

const pickEnvDefault = (config: any, key: string, fallback: number): number => {
  const env = config?.env_defaults || config?.defaults || config?.env;
  if (env && env[key] !== undefined) {
    return coerceNumber(env[key], fallback);
  }
  return fallback;
};

export const previewProps = {
  imagePath: DEFAULT_IMAGE,
  imageIsVideo: false,
  resizeRatio: 0.15,
  position: {x: 0.02, y: 0.78},
  appear: true,
  appearFrom: 'left' as const,
  duration: 5,
  videoPath: undefined,
};

export function buildProps(config: any, assets: Assets) {
  const templateName = String(config?.template || config?.template_name || '').toLowerCase();
  const isPortrait = templateName.includes('portrait') || templateName.includes('tiktok');
  const prefix = isPortrait ? 'TIKTOK' : 'LANDSCAPE';

  const durationMs = pickField<number | undefined>(config, ['duration_ms', 'durationMs'], undefined);
  const duration =
    config?.duration_sec ??
    config?.duration ??
    (durationMs !== undefined ? durationMs / 1000 : undefined) ??
    (config?.data?.duration_ms !== undefined ? config.data.duration_ms / 1000 : undefined);
  const safeDuration = coerceNumber(duration, previewProps.duration);

  const resizeRatio = coerceNumber(
    pickField<number | undefined>(config, ['resize_ratio'], undefined),
    pickEnvDefault(config, `${prefix}_FORMAT_PICTURE_WIDTH_RATIO`, previewProps.resizeRatio),
  );
  const positionX = coerceNumber(
    pickField<number | undefined>(config, ['position_x'], undefined),
    pickEnvDefault(config, `${prefix}_FORMAT_PICTURE_X_RATIO`, previewProps.position.x),
  );
  const positionY = coerceNumber(
    pickField<number | undefined>(config, ['position_y'], undefined),
    pickEnvDefault(config, `${prefix}_FORMAT_PICTURE_Y_RATIO`, previewProps.position.y),
  );
  const bottomMargin = coerceNumber(
    pickField<number | undefined>(config, ['bottom_margin_ratio'], undefined),
    pickEnvDefault(config, `${prefix}_FORMAT_PICTURE_BOTTOM_MARGIN_RATIO`, 0),
  );
  const adjustedPositionY = bottomMargin > 0 ? Math.min(positionY, Math.max(0, 1 - bottomMargin)) : positionY;

  const imagePath = assets.character || assets.image || DEFAULT_IMAGE;
  const imageIsVideo = VIDEO_EXTENSIONS.test(imagePath);
  const appear = pickField<boolean>(config, ['appear'], true);
  const appearFrom = pickField<'left' | 'right'>(
    config,
    ['appear_from', 'appearFrom'],
    previewProps.appearFrom,
  );

  return {
    imagePath,
    imageIsVideo,
    resizeRatio,
    position: {x: positionX, y: adjustedPositionY},
    appear,
    appearFrom,
    duration: safeDuration,
    videoPath: assets.video,
  };
}
