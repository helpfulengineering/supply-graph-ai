"use client";

import { createContext, useContext } from "react";
import {
  DEFAULT_THEME,
  THEMES,
  type ThemeController,
} from "../hooks/useDarkMode";

export const ThemeContext = createContext<ThemeController>({
  isDark: false,
  toggle: () => {},
  theme: DEFAULT_THEME,
  setTheme: () => {},
  themes: THEMES,
});

export function useTheme(): ThemeController {
  return useContext(ThemeContext);
}
