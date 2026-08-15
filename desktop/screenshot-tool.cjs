'use strict';
// 多视口截图工具：用真实 BrowserWindow 尺寸渲染页面并截图
const { app, BrowserWindow } = require('electron');
const fs = require('fs');
const path = require('path');

const URL_BASE = process.env.SHOT_URL || 'http://127.0.0.1:5001/';
const OUT_DIR = process.env.SHOT_DIR || path.join(__dirname, '..', '.ui_shots');
// 可用 SHOT_SIZE="1920x1080" 只跑单个视口（每视口独立进程更稳）
const SIZES = process.env.SHOT_SIZE
  ? [process.env.SHOT_SIZE.split('x').map(Number)]
  : [
      [1920, 1080],
      [1440, 900],
      [1366, 768],
      [860, 700],
      [480, 850],
    ];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

app.whenReady().then(async () => {
  // TRAE 沙箱不允许写默认 userData（Roaming\Electron），重定向到项目内
  app.setPath('userData', path.join(__dirname, '..', '.electron-userdata'));
  fs.mkdirSync(OUT_DIR, { recursive: true });
  for (const [w, h] of SIZES) {
    const win = new BrowserWindow({
      width: w,
      height: h,
      useContentSize: true,
      show: true,
      webPreferences: {
        // 每个视口独立 partition，保证每次都是全新欢迎态
        partition: `shot-${w}`,
        nodeIntegration: false,
        contextIsolation: true,
        offscreen: false,
      },
    });
    try {
      await win.loadURL(URL_BASE);
      await sleep(1500);
      fs.writeFileSync(path.join(OUT_DIR, `welcome_${w}.png`), (await win.webContents.capturePage()).toPNG());

      await win.webContents.executeJavaScript(`
        (function () {
          var input = document.getElementById('messageInput');
          input.value = '你好，请介绍一下你能帮我做什么';
          document.getElementById('sendBtn').click();
          return true;
        })()
      `);
      await sleep(10000);
      fs.writeFileSync(path.join(OUT_DIR, `chat_${w}.png`), (await win.webContents.capturePage()).toPNG());

      await win.webContents.executeJavaScript(`
        (function () {
          document.getElementById('doctorAvatarBtn').click();
          return true;
        })()
      `);
      await sleep(600);
      fs.writeFileSync(path.join(OUT_DIR, `popover_${w}.png`), (await win.webContents.capturePage()).toPNG());

      // 记录关键布局数据：欢迎态元素位置 / AI 气泡左偏移 / 欢迎态是否残留
      const metrics = await win.webContents.executeJavaScript(`
        (function () {
          var chatWindow = document.getElementById('chatWindow');
          var cwRect = chatWindow.getBoundingClientRect();
          var empty = document.getElementById('emptyState');
          var emptyVisible = empty && getComputedStyle(empty).display !== 'none';
          var hero = document.querySelector('.hero-avatar');
          var heroInfo = hero ? hero.getBoundingClientRect() : null;
          var thread = document.getElementById('chatThread');
          var threadStyle = thread ? getComputedStyle(thread) : null;
          var aiRow = document.querySelector('.message-row.assistant');
          var aiInfo = null;
          var userRow = document.querySelector('.message-row.user');
          var userInfo = null;
          if (aiRow) {
            var avatar = aiRow.querySelector('.message-avatar');
            var bubble = aiRow.querySelector('.message-bubble');
            aiInfo = {
              avatarLeft: avatar ? Math.round(avatar.getBoundingClientRect().left - cwRect.left) : null,
              bubbleLeft: bubble ? Math.round(bubble.getBoundingClientRect().left - cwRect.left) : null,
            };
          }
          if (userRow) {
            var ub = userRow.querySelector('.message-bubble');
            userInfo = ub ? { right: Math.round(cwRect.right - ub.getBoundingClientRect().right) } : null;
          }
          return JSON.stringify({
            viewport: window.innerWidth + 'x' + window.innerHeight,
            welcomeVisible: emptyVisible,
            heroCenterOffset: heroInfo ? Math.round((heroInfo.left + heroInfo.width / 2) - (cwRect.left + cwRect.width / 2)) : null,
            threadMaxWidth: threadStyle ? threadStyle.maxWidth : null,
            ai: aiInfo,
            user: userInfo,
          });
        })()
      `);
      fs.writeFileSync(path.join(OUT_DIR, `metrics_${w}.json`), String(metrics));
      console.log(`[${w}] done: ${metrics}`);
    } catch (err) {
      console.error(`[${w}] failed: ${err.message}`);
    }
    win.destroy();
  }
  app.exit(0);
});
