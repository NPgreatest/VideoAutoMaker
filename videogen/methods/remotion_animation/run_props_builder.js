#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const projectNodeModules = path.resolve(__dirname, 'remotion_project/node_modules');
module.paths.push(projectNodeModules);

const ts = require('typescript');


const transpile = (tsPath) => {
  const code = fs.readFileSync(tsPath, 'utf8');
  const result = ts.transpileModule(code, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.React,
        charset: "utf8",
      target: ts.ScriptTarget.ES2019,
      esModuleInterop: true,
    },
    fileName: tsPath,
  });
  return result.outputText;
};

const loadBuilder = (tsPath) => {
  const absolutePath = path.resolve(tsPath);
  const compiled = transpile(absolutePath);
  const module = {exports: {}};
  const dirname = path.dirname(absolutePath);
  const wrapper = new Function('require', 'module', 'exports', '__dirname', '__filename', compiled);
  const localRequire = (id) => require(require.resolve(id, {paths: [dirname]}));
  wrapper(localRequire, module, module.exports, dirname, absolutePath);
  return module.exports;
};

const main = () => {
  const [builderPath, configJson = '{}', assetsJson = '{}'] = process.argv.slice(2);
  if (!builderPath) {
    throw new Error('Missing props_builder path');
  }

  const config = JSON.parse(configJson);
  const assets = JSON.parse(assetsJson);

  const builderModule = loadBuilder(builderPath);
  const buildProps =
    builderModule.buildProps ||
    (builderModule.default && builderModule.default.buildProps) ||
    builderModule.default;

  if (typeof buildProps !== 'function') {
    throw new Error(`buildProps not found in ${builderPath}`);
  }

  const result = buildProps(config, assets);
  process.stdout.write(JSON.stringify(result ?? {}));
};

try {
  main();
} catch (err) {
  console.error(err?.stack || err?.message || String(err));
  process.exit(1);
}
