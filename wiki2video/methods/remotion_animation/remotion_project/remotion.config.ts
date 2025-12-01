import {Config} from '@remotion/cli/config';

// Templates are auto-discovered from src/templates (see src/templates/index.ts).
Config.setEntryPoint('./src/index.ts');

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setPixelFormat('yuv420p');
Config.setCodec('h264');
Config.setCrf(18);
Config.setConcurrency(1);
Config.setChromiumOpenGlRenderer('angle');
