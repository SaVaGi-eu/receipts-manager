const fs = require('fs');
const path = require('path');
const { BrowserWindow, shell, app } = require('electron');
const { SESSION_PARTITION, FLASK_URL, PORT } = require('./constants');
const state = require('./state');
const { killPortProcess } = require('../utils/port');
const { startFlask, waitForFlask } = require('../services/server');
const { promptForDataFolder } = require('../services/folder-picker');
const { showErrorPage, showLocationRequiredPage, loadAppWithRetry } = require('../renderer/pages');

// RM-114: persist window size and position across restarts
const _WIN_STATE_FILE = path.join(app.getPath('userData'), 'window-state.json');
const _DEFAULT_WIN_STATE = { width: 1400, height: 900 };

function loadWindowState() {
  try {
    const raw = fs.readFileSync(_WIN_STATE_FILE, 'utf8');
    const s = JSON.parse(raw);
    if (typeof s.width === 'number' && typeof s.height === 'number') {
      return s;
    }
  } catch (_) { /* no saved state yet */ }
  return { ..._DEFAULT_WIN_STATE };
}

function saveWindowState(win) {
  try {
    if (win.isMaximized() || win.isMinimized() || win.isFullScreen()) return;
    const b = win.getBounds();
    fs.writeFileSync(_WIN_STATE_FILE, JSON.stringify(b), 'utf8');
  } catch (err) {
    console.warn('[Window] Could not save window state:', err.message);
  }
}

const _savedState = loadWindowState();

const WINDOW_OPTIONS = {
  width: _savedState.width,
  height: _savedState.height,
  x: _savedState.x,
  y: _savedState.y,
  title: 'Receipt & Warranty Manager',
  webPreferences: {
    nodeIntegration: false,
    contextIsolation: true,
    partition: SESSION_PARTITION,
    // preload: path.join(__dirname, 'preload.js'), // enable if you use a preload
  }
};

function setupWindowListeners(win) {
  // Prevent external links from opening inside the app
  win.webContents.setWindowOpenHandler(({ url }) => {
    console.log('[Window] Opening external URL:', url);
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Listen for custom protocol to handle "Select Location" button click
  win.webContents.on('will-navigate', async (event, url) => {
    console.log('[Window] Navigation event:', url);
    if (url === 'app://select-location' && state.waitingForLocation) {
      event.preventDefault();
      state.waitingForLocation = false;

      const dataPath = await promptForDataFolder();
      if (dataPath) {
        console.log('[App] User selected data path:', dataPath);
        killPortProcess(PORT);
        await new Promise(r => setTimeout(r, 1000));

        if (!startFlask(dataPath) && state.startupError) {
          showErrorPage(state.startupError);
        } else {
          waitForFlask(FLASK_URL, 60, () => loadAppWithRetry(5), (err) => showErrorPage(err));
        }
      } else {
        showLocationRequiredPage();
      }
    }
  });

  // RM-114: save bounds on move and resize
  win.on('resize', () => saveWindowState(win));
  win.on('move', () => saveWindowState(win));

  win.on('closed', () => {
    console.log('[Window] Window closed');
    state.mainWindow = null;
  });
}

function createMainWindow() {
  console.log('[Window] Creating application window...');

  // If a window already exists, focus it instead of creating a second one
  if (state.mainWindow) {
    console.log('[Window] Window already exists, focusing...');
    if (state.mainWindow.isMinimized()) state.mainWindow.restore();
    state.mainWindow.focus();
    return;
  }

  state.mainWindow = new BrowserWindow(WINDOW_OPTIONS);
  console.log('[Window] ✓ Window created');

  const loadingHtml = `<html><body style="background:#764ba2;color:white;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
    <div style="border:4px solid rgba(255,255,255,.3);border-top:4px solid white;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;"></div>
    <h2>Receipt Manager</h2><p>Starting...</p>
    <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
  </body></html>`;
  state.mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(loadingHtml));

  setupWindowListeners(state.mainWindow);
}

module.exports = { createMainWindow, WINDOW_OPTIONS, setupWindowListeners };
