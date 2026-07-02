import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

// Focused, correctness-oriented lint (mirrors the Python side's narrow ruff
// selection). Not type-checked lint to keep the gate fast and low-noise.
export default tseslint.config(
  {
    ignores: [
      "dist",
      "artifacts",
      "src/api/generated",
      "src/components/ui",
      "node_modules",
    ],
  },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      // Established react-hooks rules only. The plugin's v7 "recommended" also
      // enables experimental React-Compiler advisories (e.g. set-state-in-effect)
      // that the codebase isn't written against; keep the gate on real bugs.
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  // Test + harness files may use dev globals and looser typing.
  {
    files: ["**/*.{test,spec}.{ts,tsx}", "e2e/**", "src/test/**"],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    rules: {
      // e2e files are Playwright, not React: its `use(...)` fixture param is not
      // React's `use` hook.
      "react-hooks/rules-of-hooks": "off",
    },
  },
);
