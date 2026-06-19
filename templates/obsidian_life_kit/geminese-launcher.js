#!/usr/bin/env node
/**
 * Обёртка для Geminese на Windows: подхватывает %USERPROFILE%\.gemini\.env
 * и GEMINI_CLI_TRUST_WORKSPACE, затем запускает gemini-cli bundle/gemini.js.
 *
 * Установка (один раз):
 *   copy в  C:\Users\ВЫ\.gemini\geminese-launcher.js
 *   Geminese → Gemini CLI path → этот файл
 *
 * В .gemini\.env одна строка: GEMINI_API_KEY=...
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const home = process.env.USERPROFILE || process.env.HOME || "";
const envFile = path.join(home, ".gemini", ".env");

function loadDotEnv(filePath) {
  if (!fs.existsSync(filePath)) return;
  const text = fs.readFileSync(filePath, "utf8");
  for (const line of text.split(/\r?\n/)) {
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
    if (!process.env[key]) process.env[key] = val;
  }
}

loadDotEnv(envFile);
process.env.GEMINI_CLI_TRUST_WORKSPACE = "true";

const npmRoot = path.join(
  process.env.APPDATA || path.join(home, "AppData", "Roaming"),
  "npm",
  "node_modules",
  "@google",
  "gemini-cli"
);

const candidates = [
  path.join(npmRoot, "bundle", "gemini.js"),
  path.join(npmRoot, "dist", "index.js"),
];

const cli = candidates.find((p) => fs.existsSync(p));
if (!cli) {
  process.stderr.write(
    "geminese-launcher: gemini-cli not found. Run: npm install -g @google/gemini-cli\n"
  );
  process.exit(1);
}

const child = spawn(process.execPath, [cli, ...process.argv.slice(2)], {
  stdio: ["pipe", "pipe", "pipe"],
  env: process.env,
  cwd: process.cwd(),
  windowsHide: true,
});

child.stdout.pipe(process.stdout);
child.stderr.pipe(process.stderr);
child.stdin.pipe(process.stdin);

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code == null ? 1 : code);
});
