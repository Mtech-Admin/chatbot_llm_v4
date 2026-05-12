/**
 * PM2 — DMRC HRMS Chatbot (FastAPI / uvicorn)
 *
 *   mkdir -p logs
 *   cp pm2.env.example .env.local   # configure env
 *   pm2 start ecosystem.config.js
 *   pm2 save && pm2 startup
 *
 * Which env file is loaded (first match wins):
 *   1) PM2_ENV_FILE=/absolute/or/relative/path.env
 *   2) Else .env.${APP_ENV} where APP_ENV defaults to "local" → only .env.local
 *      Example production: APP_ENV=production pm2 start ecosystem.config.js
 *      → loads .env.production from this folder (must contain LLM_PROVIDER=sarvam, etc.)
 *
 * If the server still uses DeepInfra while your laptop uses Sarvam, the process is
 * almost always reading a different file or stale PM2 env: fix the file PM2 merges below,
 * then `pm2 delete dmrc-hrms-chatbot` and `pm2 start ecosystem.config.js` (restart alone
 * can keep old merged env for some keys unless the app process is recreated).
 *
 * After editing the env file, prefer:
 *   pm2 restart dmrc-hrms-chatbot --update-env
 * so PM2 reapplies variables merged from the ecosystem file (plain restart may keep a stale snapshot).
 *
 * This app runs `venv/bin/uvicorn` with args `app.main:app --host 0.0.0.0 --port …`.
 * Do NOT set `interpreter` — PM2 must exec the venv `uvicorn` script via its shebang
 * (venv Python). Setting `interpreter: "python3"` forces system Python → ModuleNotFoundError: uvicorn.
 * Do NOT pass `-m uvicorn` here: that is a Python flag; if it reaches the uvicorn binary you get
 * `Error: No such option: -m`.
 */

const fs = require("fs");
const path = require("path");

function loadEnvFile(filePath) {
  const abs = path.resolve(filePath);
  if (!fs.existsSync(abs)) {
    console.warn(`[ecosystem.config.js] Env file not found: ${abs}`);
    return {};
  }
  const out = {};
  for (const line of fs.readFileSync(abs, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    out[key] = val;
  }
  return out;
}

const root = __dirname;

// Resolve which env file to load.
// Priority: PM2_ENV_FILE (explicit path) > APP_ENV (local|staging|production) > .env.local
const APP_ENV = (process.env.APP_ENV || "local").trim().toLowerCase();
const envFileMap = {
  local:      ".env.local",
  staging:    ".env.staging",
  production: ".env.production",
};
const envFile =
  process.env.PM2_ENV_FILE ||
  envFileMap[APP_ENV] ||
  `.env.${APP_ENV}`;

const envFromFile = loadEnvFile(path.join(root, envFile));
const listenPort = envFromFile.PORT || process.env.PORT || "8001";

/** venv `uvicorn` console script — executed directly so its shebang uses the venv interpreter. */
function resolveVenvUvicorn() {
  const override = process.env.PM2_UVICORN;
  if (override) return path.resolve(root, override);
  const candidates = ["venv/bin/uvicorn", ".venv/bin/uvicorn"];
  for (const rel of candidates) {
    const p = path.join(root, rel);
    if (fs.existsSync(p)) return rel;
  }
  return "venv/bin/uvicorn";
}

module.exports = {
  apps: [
    {
      name: "dmrc-hrms-chatbot",
      script: resolveVenvUvicorn(),
      args: [
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        String(listenPort),
      ],
      cwd: root,
      env: {
        PYTHONUNBUFFERED: "1",
        APP_ENV: APP_ENV,
        ...envFromFile,
      },
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: "logs/dmrc_chatbot_err.log",
      out_file: "logs/dmrc_chatbot_out.log",
      autorestart: true,
      max_memory_restart: "1500M",
    },
  ],
};
