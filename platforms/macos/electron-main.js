const { app, BrowserWindow, shell, dialog, session } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

let flaskProcess = null;
let mainWindow = null;
let startupError = null;
let waitingForLocation = false; // Track if we're waiting for folder selection

const PORT = 8765; // Matches app.py - avoids macOS AirPlay on port 5000
const FLASK_URL = `http://127.0.0.1:${PORT}`;
const SESSION_PARTITION = 'persist:receiptmanager';
const APP_NAME = "Receipt Manager";

// Settings file location (macOS standard)
const SETTINGS_DIR = path.join(app.getPath('home'), 'Library', 'Application Support', APP_NAME);
const SETTINGS_FILE = path.join(SETTINGS_DIR, 'settings.json');

console.log('[Electron] Starting Receipt Manager...');
console.log('[Electron] Settings file:', SETTINGS_FILE);

// ── Ensure only one instance of the app runs ──────────────────────────────
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  console.log('[Electron] Another instance is already running. Exiting.');
  app.quit();
} else {
  app.on('second-instance', (event, argv, workingDirectory) => {
    // Someone tried to start a second instance — focus the existing window
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

// ── Kill any process holding the given port ────────────────────────────────
function killPortProcess(port) {
  try {
    const pids = execSync(`lsof -ti :${port}`, {
      encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore']
    }).trim();
    if (pids) {
      pids.split('\n').forEach(pid => {
        try { process.kill(parseInt(pid), 'SIGKILL'); } catch (e) {}
      });
      console.log(`[Electron] Killed stale process(es) on port ${port}:`, pids);
    }
  } catch (e) { /* no process on that port, fine */ }
}

// ── Get the correct base directory ────────────────────────────────────────
function getAppDir() {
  if (!app.isPackaged) {
    // In development, go up two levels from platforms/macos/ to reach root
    const dir = path.join(__dirname, '..', '..');
    console.log('[Electron] Running in development mode, app dir:', dir);
    return dir;
  }
  // When packaged, extraResources are in Contents/Resources/
  console.log('[Electron] Running in packaged mode, resources path:', process.resourcesPath);
  return process.resourcesPath;
}

// ── Settings management ───────────────────────────────────────────────────
function getSavedDataPath() {
  console.log('[Settings] Checking for saved data path...');
  if (!fs.existsSync(SETTINGS_FILE)) {
    console.log('[Settings] Settings file does not exist:', SETTINGS_FILE);
    return null;
  }
  try {
    const content = fs.readFileSync(SETTINGS_FILE, 'utf8');
    console.log('[Settings] Settings file content:', content);
    const settings = JSON.parse(content);
    const chosen = settings.data_directory;
    console.log('[Settings] Configured data directory:', chosen);
    if (chosen && fs.existsSync(chosen)) {
      console.log('[Settings] ✓ Data directory exists and is accessible');
      return chosen;
    } else {
      console.log('[Settings] ✗ Data directory does not exist or is not accessible');
    }
  } catch (e) {
    console.error('[Settings] Error reading settings:', e);
  }
  return null;
}

function saveSettings(dataPath) {
  console.log('[Settings] Saving data path:', dataPath);
  try {
    if (!fs.existsSync(SETTINGS_DIR)) {
      console.log('[Settings] Creating settings directory:', SETTINGS_DIR);
      fs.mkdirSync(SETTINGS_DIR, { recursive: true });
    }
    const settings = {
      data_directory: dataPath,
      app_name: APP_NAME,
      version: 1,
      updated_at: new Date().toISOString()
    };
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 2), 'utf8');
    console.log('[Settings] ✓ Settings saved successfully');
    return true;
  } catch (e) {
    console.error('[Settings] ✗ Error saving settings:', e);
    return false;
  }
}

// ── Folder Picker ──────────────────────────────────────────────────────────
async function promptForDataFolder() {
  const defaultPath = path.join(app.getPath('documents'), 'Receipts Manager');

  console.log('[FolderPicker] Showing folder picker dialog...');
  const result = await dialog.showMessageBox(mainWindow, {
    type: 'question',
    buttons: ['Choose Folder...', 'Use Default (Documents)'],
    defaultId: 1,
    title: 'First Time Setup',
    message: 'Where would you like to store your receipts and database?',
    detail: `If you choose Default, we will create a folder at:\n${defaultPath}\n\nYou can also choose any other location (like iCloud or an external drive).`,
    noLink: true
  });

  let chosenPath = null;
  if (result.response === 1) {
    console.log('[FolderPicker] User chose default location:', defaultPath);
    chosenPath = defaultPath;
  } else {
    console.log('[FolderPicker] User wants to choose custom location...');
    const pickResult = await dialog.showOpenDialog(mainWindow, {
      title: 'Select Data Storage Folder',
      properties: ['openDirectory', 'createDirectory', 'promptToCreate'],
      defaultPath: app.getPath('documents')
    });
    if (!pickResult.canceled && pickResult.filePaths.length > 0) {
      chosenPath = pickResult.filePaths[0];
      console.log('[FolderPicker] User selected:', chosenPath);
    } else {
      console.log('[FolderPicker] User cancelled folder selection');
    }
  }

  if (chosenPath) {
    if (!fs.existsSync(chosenPath)) {
      try {
        console.log('[FolderPicker] Creating directory structure...');
        fs.mkdirSync(chosenPath, { recursive: true });
        // Create subdirs immediately to verify writability
        fs.mkdirSync(path.join(chosenPath, 'database'), { recursive: true });
        fs.mkdirSync(path.join(chosenPath, 'storage'), { recursive: true });
        console.log('[FolderPicker] ✓ Directory structure created successfully');
      } catch (e) {
        console.error('[FolderPicker] ✗ Error creating directory:', e);
        await dialog.showMessageBox(mainWindow, {
          type: 'error',
          title: 'Folder Error',
          message: 'Could not create or write to folder',
          detail: e.message,
          buttons: ['Try Again']
        });
        return promptForDataFolder(); // Try again
      }
    }
    saveSettings(chosenPath);
    return chosenPath;
  } else {
    // User cancelled - signal cancellation
    return null;
  }
}

// ── Show "Location Required" page when user cancels ───────────────────────
function showLocationRequiredPage() {
  console.log('[UI] Showing location required page');
  const html = `<!DOCTYPE html>
  <html>
  <head>
    <meta charset="UTF-8">
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        color: white;
      }
      .container {
        text-align: center;
        background: rgba(255, 255, 255, 0.15);
        padding: 60px;
        border-radius: 20px;
        backdrop-filter: blur(10px);
        max-width: 550px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      }
      .icon { font-size: 72px; margin-bottom: 25px; }
      h1 { margin: 0 0 20px 0; font-size: 32px; font-weight: 600; }
      p { font-size: 18px; line-height: 1.7; margin: 20px 0; opacity: 0.95; }
      button {
        background: white;
        color: #667eea;
        border: none;
        padding: 18px 50px;
        font-size: 18px;
        font-weight: 600;
        border-radius: 12px;
        cursor: pointer;
        margin-top: 25px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
      }
      button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
      }
      button:active { transform: translateY(0px); }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="icon">📁</div>
      <h1>Storage Location Required</h1>
      <p>Receipt Manager needs a folder to store your receipts and database.</p>
      <p><strong>Please select a location to continue.</strong></p>
      <button id="selectBtn">Select Location...</button>
    </div>
    <script>
      document.getElementById('selectBtn').addEventListener('click', () => {
        // Signal to Electron we want to select location
        window.location.href = 'app://select-location';
      });
    </script>
  </body>
  </html>`;

  if (mainWindow && !mainWindow.isDestroyed()) {
    waitingForLocation = true;
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  }
}

// ── Find Python ───────────────────────────────────────────────────────────
function findPython() {
  console.log('[Python] Searching for Python executable...');
  const appDir = getAppDir();
  const possiblePaths = [
    path.join(appDir, 'venv', 'bin', 'python3'),
    path.join(appDir, 'venv', 'bin', 'python'),
    '/usr/local/bin/python3',
    '/opt/homebrew/bin/python3',
    '/usr/bin/python3',
    'python3'
  ];

  for (const pyPath of possiblePaths) {
    console.log('[Python] Checking:', pyPath);
    if (pyPath === 'python3' || fs.existsSync(pyPath)) {
      console.log('[Python] ✓ Found at:', pyPath);
      return pyPath;
    }
  }

  console.error('[Python] ✗ Python 3 not found in any expected location');
  startupError = 'Python 3 not found. Please install Python 3 from python.org';
  return null;
}

// ── Start server ──────────────────────────────────────────────────────────
function startFlask(dataPath) {
  console.log('[Server] Starting Python backend...');
  console.log('[Server] Data path:', dataPath);

  const pythonPath = findPython();
  if (!pythonPath) return false;

  const appDir = getAppDir();
  const appPath = path.join(appDir, 'app.py');

  console.log('[Server] App directory:', appDir);
  console.log('[Server] Looking for app.py at:', appPath);

  if (!fs.existsSync(appPath)) {
    console.error('[Server] ✗ app.py not found at:', appPath);
    startupError = `Cannot find app.py at: ${appPath}`;
    return false;
  }

  console.log('[Server] ✓ app.py found');
  console.log('[Server] Starting with DATA_DIR:', dataPath);

  try {
    flaskProcess = spawn(pythonPath, [appPath], {
      cwd: appDir,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        DATA_DIR: dataPath // Pass the user-chosen path to Python
      }
    });

    console.log('[Server] ✓ Process spawned with PID:', flaskProcess.pid);

    flaskProcess.stdout.on('data', d => {
      const msg = d.toString().trim();
      console.log('[Server STDOUT]', msg);
    });

    flaskProcess.stderr.on('data', d => {
      const msg = d.toString().trim();
      console.log('[Server STDERR]', msg);
      if (msg.includes('Error') || msg.includes('Traceback')) {
        startupError = msg;
      }
    });

    flaskProcess.on('error', (err) => {
      console.error('[Server] Process error:', err);
      startupError = `Process error: ${err.message}`;
    });

    flaskProcess.on('exit', (code, signal) => {
      console.log(`[Server] Process exited with code ${code} and signal ${signal}`);
    });

    return true;
  } catch (err) {
    console.error('[Server] Exception starting server:', err);
    startupError = `Exception starting server: ${err.message}`;
    return false;
  }
}

// ── Standard Boilerplate (Wait / Load / Error) ────────────────────────────
function waitForFlask(url, retries, callback, errorCallback) {
  console.log(`[Server] Waiting for server to respond... (${retries} retries left)`);
  const req = http.get(url, (res) => {
    res.resume();
    if (res.statusCode < 500) {
      console.log('[Server] ✓ Server is ready! Status:', res.statusCode);
      callback();
    } else {
      console.log('[Server] Server responded with error status:', res.statusCode);
      if (retries <= 0) {
        errorCallback(`Server error: ${res.statusCode}`);
        return;
      }
      setTimeout(() => waitForFlask(url, retries - 1, callback, errorCallback), 500);
    }
  });
  req.setTimeout(2000, () => {
    console.log('[Server] Request timeout, retrying...');
    req.destroy();
  });
  req.on('error', (err) => {
    console.log('[Server] Connection error:', err.message.replace(/\n|\r/g, ''));
    if (retries <= 0) {
      errorCallback(startupError || 'Server timeout');
      return;
    }
    setTimeout(() => waitForFlask(url, retries - 1, callback, errorCallback), 500);
  });
}

function loadAppWithRetry(retriesLeft) {
  console.log(`[UI] Loading application... (${retriesLeft} retries left)`);
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.loadURL(FLASK_URL);
  mainWindow.webContents.once('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('[UI] Failed to load:', errorCode, errorDescription);
    if (retriesLeft > 0) {
      setTimeout(() => loadAppWithRetry(retriesLeft - 1), 1000);
    } else {
      showErrorPage('Failed to load application page.');
    }
  });
  mainWindow.webContents.once('did-finish-load', () => {
    console.log('[UI] ✓ Application loaded successfully');
  });
}

function showErrorPage(errorMessage) {
  console.error('[UI] Showing error page:', errorMessage);
  const html = `<html><body style="font-family:sans-serif;padding:50px;">
    <h1 style="color:#d32f2f">Startup Error</h1>
    <pre style="background:#eee;padding:20px;white-space:pre-wrap;word-wrap:break-word;">${errorMessage}</pre>
    <p>Please check the Console.app logs for more details (search for "Receipt Manager" or "Electron").</p>
    <button onclick="location.reload()" style="padding:10px 20px;font-size:16px;cursor:pointer;">Retry</button>
  </body></html>`;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  }
}

// ── createWindow ───────────────────────────────────────────────────────────
function createWindow() {
  console.log('[Window] Creating application window...');

  // If a window already exists, focus it and return
  if (mainWindow) {
    console.log('[Window] Window already exists, focusing...');
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'Receipt & Warranty Manager',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      partition: SESSION_PARTITION,
      // preload: path.join(__dirname, 'preload.js'), // enable if you use a preload
    }
  });

  console.log('[Window] ✓ Window created');

  // ALWAYS open DevTools for debugging
  try {
    console.log('[DevTools] Opening developer tools...');
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } catch (e) {
    console.error('[DevTools] Could not open developer tools:', e);
  }

  const loadingHtml = `<html><body style="background:#764ba2;color:white;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
    <div style="border:4px solid rgba(255,255,255,.3);border-top:4px solid white;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;"></div>
    <h2>Receipt Manager</h2><p>Starting...</p>
    <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
  </body></html>`;
  mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(loadingHtml));

  // Prevent external links from opening inside the app
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    console.log('[Window] Opening external URL:', url);
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Listen for custom protocol to handle "Select Location" button click
  mainWindow.webContents.on('will-navigate', async (event, url) => {
    console.log('[Window] Navigation event:', url);
    if (url === 'app://select-location' && waitingForLocation) {
      event.preventDefault();
      waitingForLocation = false;

      // Show folder picker
      const dataPath = await promptForDataFolder();
      if (dataPath) {
        // User selected a location, start the server
        console.log('[App] User selected data path:', dataPath);
        killPortProcess(PORT);
        await new Promise(r => setTimeout(r, 1000));

        if (!startFlask(dataPath) && startupError) {
          showErrorPage(startupError);
        } else {
          waitForFlask(FLASK_URL, 60, () => loadAppWithRetry(5), (err) => showErrorPage(err));
        }
      } else {
        // User cancelled again - show the page again
        showLocationRequiredPage();
      }
    }
  });

  mainWindow.on('closed', () => {
    console.log('[Window] Window closed');
    mainWindow = null;
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

  // Create the window first
  createWindow();

  // Session / CSP setup
  const ses = session.fromPartition(SESSION_PARTITION);
  ses.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    delete responseHeaders['content-security-policy'];
    delete responseHeaders['Content-Security-Policy'];
    callback({ responseHeaders });
  });

  // 1. Data Directory resolution
  let dataPath = getSavedDataPath();
  if (!dataPath) {
    console.log('[App] No saved data path found, prompting user...');
    // First time - prompt for location
    dataPath = await promptForDataFolder();
    if (!dataPath) {
      // User cancelled initial selection - show the location required page
      console.log('[App] User cancelled folder selection, showing location required page');
      waitingForLocation = true;
      showLocationRequiredPage();
      return; // Stop here, wait for user to click button
    }
  }

  console.log('[App] ✓ Data path configured:', dataPath);

  // 2. Start backend
  console.log('[App] Cleaning up port', PORT);
  killPortProcess(PORT);
  await new Promise(r => setTimeout(r, 500));

  if (!startFlask(dataPath) && startupError) {
    console.error('[App] ✗ Failed to start backend');
    showErrorPage(startupError);
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

app.on('window-all-closed', () => {
  console.log('[App] All windows closed');
  if (flaskProcess) {
    console.log('[App] Terminating backend process...');
    flaskProcess.kill('SIGTERM');
  }
  app.quit();
});

app.on('will-quit', () => {
  console.log('[App] Application quitting...');
});

console.log('[Electron] electron-main.js loaded successfully');
