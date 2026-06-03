import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Decode percent-encoded filenames for display (e.g. from browser download URLs). */
export function displayFileName(name: string): string {
  if (!name) return name;
  try {
    let decoded = decodeURIComponent(name);
    if (decoded.includes("%")) {
      try {
        decoded = decodeURIComponent(decoded);
      } catch {
        /* keep single decode */
      }
    }
    return decoded;
  } catch {
    return name;
  }
}
