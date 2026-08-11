"use client";

import { useTheme } from "../../context/ThemeContext";

/**
 * World selector. A native <select> on purpose: it is one control, keyboard-
 * and screen-reader-native, and needs no focus management. The hamburger
 * sitemap gets the fuller radio-list treatment; this is the always-visible
 * affordance until then.
 */
export function ThemePicker() {
  const { theme, setTheme, themes } = useTheme();

  return (
    <label className="flex items-center gap-1.5">
      <span className="sr-only">Theme</span>
      <select
        value={theme}
        onChange={(e) => setTheme(e.target.value as typeof theme)}
        aria-label="Theme"
        title="Change the colour world"
        className="rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground transition-colors hover:bg-muted"
      >
        {themes.map(({ slug, label }) => (
          <option key={slug} value={slug}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}
