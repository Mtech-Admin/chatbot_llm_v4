/**
 * PM2 — DMRC HRMS Chatbot (FastAPI / uvicorn)
 *
 *   mkdir -p logs
 *   cp pm2.env.example .env.local   # configure env
 *   pm2 start ecosystem.config.js
 *   pm2 save && pm2 startup
 *
 * Env file override: PM2_ENV_FILE=/path/to/prod.env pm2 start ecosystem.config.js
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
const envFile = process.env.PM2_ENV_FILE || ".env.local";
const envFromFile = loadEnvFile(path.join(root, envFile));
const listenPort = envFromFile.PORT || process.env.PORT || "8001";

function resolveUvicornScript() {
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
      script: resolveUvicornScript(),
      args: `app.main:app --host 0.0.0.0 --port ${listenPort}`,
      cwd: root,
      interpreter: "python3",
      env: {
        PYTHONUNBUFFERED: "1",
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
