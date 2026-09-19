import js from "@eslint/js";

export default [
  {
    ignores: ["node_modules/**", "static/js/react/calendar-board.js", "archived_unused_folders/**"],
  },
  js.configs.recommended,
  {
    files: ["frontend/src/calendar-board.tsx"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        AbortController: "readonly",
        document: "readonly",
        fetch: "readonly",
        URLSearchParams: "readonly",
        window: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "off",
    },
  },
];
