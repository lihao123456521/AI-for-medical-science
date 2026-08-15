'use strict';

const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const net = require('net');
const path = require('path');

const HEALTH_TIMEOUT_MS = 60000;
const HEALTH_POLL_INTERVAL_MS = 400;

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

function projectRoot() {
  return path.resolve(__dirname, '..');
}

function resolveBackendCommand({ isDev }) {
  const override = process.env.UROPUC_BACKEND_EXE;
  if (override) {
    return { command: override, args: [], cwd: path.dirname(override), isExternal: true };
  }
  if (isDev) {
    const python = process.env.UROPUC_PYTHON || 'python';
    const root = projectRoot();
    return { command: python, args: [path.join(root, 'run_waitress.py')], cwd: root, isExternal: false };
  }
  const exeName = process.platform === 'win32' ? 'UroPUCBackend.exe' : 'UroPUCBackend';
  const backendExe = path.join(process.resourcesPath, 'backend', 'UroPUCBackend', exeName);
  return { command: backendExe, args: [], cwd: path.dirname(backendExe), isExternal: false };
}

function healthProbe(port) {
  return new Promise((resolve) => {
    const req = http.get(
      { host: '127.0.0.1', port, path: '/healthz', timeout: 2500 },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      }
    );
    req.once('error', () => resolve(false));
    req.once('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForHealth(port, onTick) {
  const deadline = Date.now() + HEALTH_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await healthProbe(port)) return true;
    if (onTick) onTick();
    await new Promise((r) => setTimeout(r, HEALTH_POLL_INTERVAL_MS));
  }
  return false;
}

class BackendManager {
  constructor({ logDir }) {
    this.logDir = logDir;
    this.logFile = path.join(logDir, 'backend.log');
    this.child = null;
    this.stopped = false;
    this.recentLog = [];
    this._logStream = null;
  }

  _log(line) {
    const entry = `[${new Date().toISOString()}] ${line}`;
    console.log(`[backend] ${entry}`);
    this.recentLog.push(entry);
    if (this.recentLog.length > 200) this.recentLog.shift();
    try {
      if (!this._logStream) {
        fs.mkdirSync(this.logDir, { recursive: true });
        this._logStream = fs.createWriteStream(this.logFile, { flags: 'a' });
      }
      this._logStream.write(entry + '\n');
    } catch (err) {
      // 日志写入失败不应影响后端运行
    }
  }

  logTail(maxChars = 2000) {
    return this.recentLog.join('\n').slice(-maxChars);
  }

  async start({ isDev }) {
    const port = await findFreePort();
    const { command, args, cwd } = resolveBackendCommand({ isDev });
    this._log(`Starting backend: ${command} ${args.join(' ')} (port ${port})`);

    const child = spawn(command, args, {
      cwd,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: {
        ...process.env,
        HOST: '127.0.0.1',
        PORT: String(port),
        UROPUC_DESKTOP: '1',
      },
    });
    this.child = child;
    this.port = port;
    this.command = command;

    child.stdout.on('data', (d) => this._log(`stdout: ${String(d).trim()}`));
    child.stderr.on('data', (d) => this._log(`stderr: ${String(d).trim()}`));
    child.once('error', (err) => this._log(`spawn error: ${err.message}`));
    child.once('exit', (code, signal) => this._log(`exited code=${code} signal=${signal}`));

    const healthy = await waitForHealth(port);
    if (!healthy) {
      const running = child.exitCode === null && !child.killed;
      const detail = this.logTail();
      this._log(`health check failed on port ${port} (still running: ${running})`);
      if (running) this.stop();
      const reason = running || child.exitCode === null
        ? '后端启动超时（60 秒内 /healthz 未就绪）。'
        : `后端进程提前退出（exit=${child.exitCode}）。`;
      throw new Error(
        `UroPUC 后端启动失败：${reason}\n命令：${command}\n\n最近日志：\n${detail}`
      );
    }
    this._log(`Backend healthy on http://127.0.0.1:${port}`);
    return port;
  }

  stop() {
    if (this.stopped || !this.child || this.child.exitCode !== null) {
      this.stopped = true;
      return;
    }
    this.stopped = true;
    const pid = this.child.pid;
    this._log(`Stopping backend (pid ${pid})`);
    try {
      if (process.platform === 'win32' && pid) {
        // taskkill /T 保证连带 waitress 子进程一起退出，避免残留
        spawn('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
      } else {
        this.child.kill('SIGTERM');
      }
    } catch (err) {
      this._log(`stop error: ${err.message}`);
    }
    if (this._logStream) {
      this._logStream.end();
      this._logStream = null;
    }
  }
}

module.exports = { BackendManager, findFreePort, resolveBackendCommand };
