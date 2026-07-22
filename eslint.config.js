const sharedGlobals = {
  ArrayBuffer: "readonly",
  Blob: "readonly",
  Number: "readonly",
  Option: "readonly",
  TextDecoder: "readonly",
  URL: "readonly",
  Uint8Array: "readonly",
  document: "readonly",
  window: "readonly",
  navigator: "readonly",
  fetch: "readonly",
  crypto: "readonly",
  console: "readonly",
  setTimeout: "readonly",
  process: "readonly",
};

export default [
  {
    files: ["**/*.js"],
    ignores: ["dist/**", "web/public/data/**"],
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: "module",
      globals: sharedGlobals,
    },
    rules: {
      "no-undef": "error",
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "no-constant-condition": "error",
    },
  },
];
