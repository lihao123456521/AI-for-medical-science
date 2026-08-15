'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// 只暴露最小桌面能力，不透出 ipcRenderer 或 Node API
contextBridge.exposeInMainWorld('uropucDesktop', {
  isDesktop: true,
  platform: process.platform,
  openLogsFolder: () => ipcRenderer.invoke('uropuc:open-logs'),
});
