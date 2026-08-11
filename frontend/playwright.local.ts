import base from "./playwright.config";
const EXE = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
export default { ...base, projects: (base.projects ?? []).map((p) => ({ ...p, use: { ...p.use, launchOptions: { executablePath: EXE } } })) };
