'use strict';

const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const path = require('path');

const { BackendManager } = require('./backend-manager.cjs');

const isDev = process.argv.includes('--dev') || !app.isPackaged;

let mainWindow = null;
let backend = null;

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(bootstrap).catch((err) => {
    console.error(err);
    dialog.showErrorBox('UroPUC 启动失败', String(err && err.message ? err.message : err));
    app.exit(1);
  });

  app.on('window-all-closed', () => {
    app.quit();
  });

  app.on('before-quit', () => {
    if (backend) backend.stop();
  });
}

async function bootstrap() {
  const logDir = path.join(app.getPath('userData'), 'logs');
  backend = new BackendManager({ logDir });

  let port;
  try {
    port = await backend.start({ isDev });
  } catch (err) {
    dialog.showErrorBox('UroPUC 后端启动失败', String(err && err.message ? err.message : err));
    app.exit(1);
    return;
  }

  ipcMain.handle('uropuc:open-logs', () => shell.openPath(logDir));

  createWindow(`http://127.0.0.1:${port}`);
}

function createWindow(url) {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 640,
    show: false,
    autoHideMenuBar: true,
    title: 'UroPUC',
    backgroundColor: '#f4f6fb',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      spellcheck: false,
    },
  });

  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 只允许加载本地后端地址；禁止跳转外部站点
  mainWindow.webContents.on('will-navigate', (event, targetUrl) => {
    if (!isLocalBackendUrl(targetUrl)) event.preventDefault();
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url) && !isLocalBackendUrl(url)) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  mainWindow.loadURL(url);
}

function isLocalBackendUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.hostname === '127.0.0.1' && parsed.protocol === 'http:';
  } catch {
    return false;
  }
}
