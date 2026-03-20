const { app, session, dialog } = require('electron');
const { PORT, FLASK_URL, SESSION_PARTITION } = require('./constants');
const state = require('./state');
const { createMainWindow } = require('./window');
const { killPortProcess } = require('../utils/port');
const { getSavedDataPath } = require('../services/settings');
const { startFlask, waitForFlask } = require('../services/server');
const { promptForDataFolder } = require('../services/folder-picker');
const { showErrorPage, showLocationRequiredPage, loadAppWithRetry } = require('../renderer/pages');

console.log('[Electron] Starting Receipt Manager...');

// ── Ensure only one instance of the app runs ──────────────────────────────
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  console.log('[Electron] Another instance is already running. Exiting.');
  app.quit();
} else {
  app.on('second-instance', () => {
    if (state.mainWindow) {
      if (state.mainWindow.isMinimized()) state.mainWindow.restore();
      state.mainWindow.focus();
    }
  });
}

// ── Main Entry ─────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  console.log('═'.repeat(60));
  console.log('[App] Receipt Manager starting...');
  console.log('[App] Electron version:', process.versions.electron);
  console.log('[App] Node version:', process.versions.node);
  console.log('[App] Packaged:', app.isPackaged);
  console.log('═'.repeat(60));

  createMainWindow();

  // Session / CSP setup
  const ses = session.fromPartition(SESSION_PARTITION);
  ses.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    delete responseHeaders['content-security-policy'];
    delete responseHeaders['Content-Security-Policy'];
    callback({ responseHeaders });
  });

  // 1. Data directory resolution
  let dataPath = getSavedDataPath();
  if (!dataPath) {
    console.log('[App] No saved data path found, prompting user...');
    dataPath = await promptForDataFolder();
    if (!dataPath) {
      console.log('[App] User cancelled folder selection, showing location required page');
      state.waitingForLocation = true;
      showLocationRequiredPage();
      return;
    }
  }

  console.log('[App] ✓ Data path configured:', dataPath);

  // 2. Start backend
  console.log('[App] Cleaning up port', PORT);
  killPortProcess(PORT);
  await new Promise(r => setTimeout(r, 500));

  if (!startFlask(dataPath) && state.startupError) {
    console.error('[App] ✗ Failed to start backend');
    showErrorPage(state.startupError);
  } else {
    console.log('[App] Backend started, waiting for it to be ready...');
    waitForFlask(FLASK_URL, 60, () => {
      console.log('[App] Backend ready, loading application UI...');
      loadAppWithRetry(5);
    }, (err) => {
      console.error('[App] Backend failed to start:', err);
      showErrorPage(err);
    });
  }
}).catch(err => {
  console.error('[App] Fatal error during startup:', err);
  dialog.showErrorBox('Startup Error', err.message);
});

// On macOS, clicking the dock icon should re-open the window if it was closed
app.on('activate', () => {
  createMainWindow();
});

app.on('window-all-closed', () => {
  console.log('[App] All windows closed');
  if (state.flaskProcess) {
    console.log('[App] Terminating backend process...');
    state.flaskProcess.kill('SIGTERM');
  }
  app.quit();
});

app.on('will-quit', () => {
  console.log('[App] Application quitting...');
});

console.log('[Electron] index.js loaded successfully');
