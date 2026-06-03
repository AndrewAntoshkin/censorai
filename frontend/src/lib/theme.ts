export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "fc-theme";

export function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function setStoredTheme(theme: Theme) {
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  applyTheme(theme);
}
