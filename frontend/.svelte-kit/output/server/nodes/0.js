

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/layout.svelte.js')).default;
export const imports = ["_app/immutable/nodes/0.B83Z2rMo.js","_app/immutable/chunks/C_kHtwHJ.js","_app/immutable/chunks/7h06Y_LQ.js"];
export const stylesheets = [];
export const fonts = [];
