export interface Settings {
  sound: boolean;
  boot: boolean;
  motion: boolean;
}

const KEY = "jarvis-settings";
const DEFAULTS: Settings = { sound: false, boot: true, motion: true };

/** Settings are kept in the browser (localStorage) when possible. */
export function loadSettings(): Settings {
  try {
    const saved = localStorage.getItem(KEY);
    return saved ? { ...DEFAULTS, ...JSON.parse(saved) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
}

export function saveSettings(settings: Settings) {
  try {
    localStorage.setItem(KEY, JSON.stringify(settings));
  } catch {
    // private mode or storage blocked: settings just won't be remembered
  }
}
