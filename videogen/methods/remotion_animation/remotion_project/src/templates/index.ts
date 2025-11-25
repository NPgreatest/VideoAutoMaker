import React from 'react';

declare const require: any;

export type TemplateMetadata = {
  name: string;
  entry: string;
  width: number;
  height: number;
  fps: number;
  props_builder: string;
};

export type TemplateDefinition = TemplateMetadata & {
  Component: React.FC<any>;
  previewProps?: Record<string, unknown>;
};

const metaContext = (require as any).context('./', true, /template\.json$/);
const componentContext = (require as any).context('./', true, /Component\.(t|j)sx?$/);
const builderContext = (require as any).context('./', true, /props_builder\.ts$/);

export const templates: TemplateDefinition[] = metaContext.keys().map((key: string) => {
  const meta = metaContext(key) as TemplateMetadata;
  const dir = key.replace('./', '').replace(/\/template\.json$/, '');

  const componentKey = `./${dir}/Component.tsx`;
  const componentModule = componentContext(componentKey);
  const normalizedName = meta.name.replace(/[^a-zA-Z0-9]/g, '');
  const Component =
    componentModule.default ||
    componentModule[normalizedName] ||
    componentModule.Component ||
    componentModule[meta.name];

  if (!Component) {
    throw new Error(`Component not found for template ${meta.name} (${componentKey})`);
  }

  const builderKey = `./${dir}/props_builder.ts`;
  const builderModule = builderContext.keys().includes(builderKey) ? builderContext(builderKey) : undefined;
  const previewProps = builderModule?.previewProps || builderModule?.defaultPreviewProps;

  return {
    ...meta,
    Component,
    previewProps,
  };
});
