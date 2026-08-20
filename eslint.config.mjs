import next from "eslint-config-next";

/**
 * Flat config. eslint-config-next 16 exports a flat-config array directly, so
 * no FlatCompat shim is needed.
 *
 * The generated legal content modules are excluded: they are verbatim copies of
 * reviewed documents produced by scripts/extract-legal.mjs.
 */
const config = [
  ...next,
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts", "src/content/legal/*.ts"],
  },
];

export default config;
