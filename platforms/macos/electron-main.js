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
    return path.join(__dirname, '..', '..');
  }
  // When packaged, files are in app.asar.unpacked at the same level as electron-main.js
  // But Python files were copied from ../../ so they're TWO levels up from where electron-main.js is
  const unpackedPath = __dirname.replace('app.asar', 'app.asar.unpacked');
  const parentUnpacked = path.join(unpackedPath, '..', '..');
  
  console.log('[App] Checking paths:');
  console.log('  __dirname:', __dirname);
  console.log('  unpackedPath:', unpackedPath);
  console.log('  parentUnpacked:', parentUnpacked);
  
  // Check where app.py actually is
  const appPyInUnpacked = path.join(unpackedPath, 'app.py');
  const appPyInParent = path.join(parentUnpacked, 'app.py');
  
  if (fs.existsSync(appPyInUnpacked)) {
    console.log('[App] Found app.py in unpacked path');
    return unpackedPath;
  }
  if (fs.existsSync(appPyInParent)) {
    console.log('[App] Found app.py in parent unpacked path');
    return parentUnpacked;
  }
  
  console.log('[App] app.py not found, using unpacked path as fallback');
  return unpackedPath;
}


// ── Settings management ───────────────────────────────────────────────────
function getSavedDataPath() {
  if (!fs.existsSync(SETTINGS_FILE)) return null;
  try {
    const settings = JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf8'));
    const chosen = settings.data_directory;
    if (chosen && fs.existsSync(chosen)) return chosen;
  } catch (e) {
    console.error('[Settings] Error reading settings:', e);
  }
  return null;
}

function saveSettings(dataPath) {
  try {
    if (!fs.existsSync(SETTINGS_DIR)) fs.mkdirSync(SETTINGS_DIR, { recursive: true });
    const settings = {
      data_directory: dataPath,
      app_name: APP_NAME,
      version: 1,
      updated_at: new Date().toISOString()
    };
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 2), 'utf8');
    return true;
  } catch (e) {
    console.error('[Settings] Error saving settings:', e);
    return false;
  }
}

// ── Folder Picker ──────────────────────────────────────────────────────────
async function promptForDataFolder() {
  const defaultPath = path.join(app.getPath('documents'), 'Receipts Manager');
  
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
    chosenPath = defaultPath;
  } else {
    const pickResult = await dialog.showOpenDialog(mainWindow, {
      title: 'Select Data Storage Folder',
      properties: ['openDirectory', 'createDirectory', 'promptToCreate'],
      defaultPath: app.getPath('documents')
    });
    if (!pickResult.canceled && pickResult.filePaths.length > 0) {
      chosenPath = pickResult.filePaths[0];
    }
  }

  if (chosenPath) {
    if (!fs.existsSync(chosenPath)) {
      try {
        fs.mkdirSync(chosenPath, { recursive: true });
        // Create subdirs immediately to verify writability
        fs.mkdirSync(path.join(chosenPath, 'database'), { recursive: true });
        fs.mkdirSync(path.join(chosenPath, 'storage'), { recursive: true });
      } catch (e) {
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
    // User cancelled - show friendly message with retry option
    return null; // Signal cancellation
  }
}

// ── Show "Location Required" page when user cancels ───────────────────────
function showLocationRequiredPage() {
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
    if (pyPath === 'python3' || fs.existsSync(pyPath)) {
      console.log('[Python] Found at:', pyPath);
      return pyPath;
    }
  }
  startupError = 'Python 3 not found. Please install Python 3 from python.org';
  return null;
}

// ── Start server ──────────────────────────────────────────────────────────
function startFlask(dataPath) {
  const pythonPath = findPython();
  if (!pythonPath) return false;
  
  const appDir = getAppDir();
  const appPath = path.join(appDir, 'app.py');
  
  if (!fs.existsSync(appPath)) {
    startupError = `Cannot find app.py at: ${appPath}`;
    return false;
  }

  try {
    flaskProcess = spawn(pythonPath, [appPath], {
      cwd: appDir,
      env: { 
        ...process.env, 
        PYTHONUNBUFFERED: '1',
        DATA_DIR: dataPath // Pass the user-chosen path to Python
      }
    });

    flaskProcess.stdout.on('data', d => console.log('[Server]', d.toString().trim()));
    flaskProcess.stderr.on('data', d => {
      const msg = d.toString().trim();
      console.error('[Server]', msg);
      if (msg.includes('Error') || msg.includes('Traceback')) startupError = msg;
    });

    return true;
  } catch (err) {
    startupError = `Exception starting server: ${err.message}`;
    return false;
  }
}

// ── Standard Boilerplate (Wait/Load/Error) ──────────────────────────────────
function waitForFlask(url, retries, callback, errorCallback) {
  const req = http.get(url, (res) => {
    res.resume();
    if (res.statusCode < 500) {
      console.log('[Electron] Server is ready!');
      callback();
    } else {
      if (retries <= 0) { errorCallback(`Server error: ${res.statusCode}`); return; }
      setTimeout(() => waitForFlask(url, retries - 1, callback, errorCallback), 500);
    }
  });
  req.setTimeout(2000, () => req.destroy());
  req.on('error', () => {
    if (retries <= 0) { errorCallback(startupError || 'Server timeout'); return; }
    setTimeout(() => waitForFlask(url, retries - 1, callback, errorCallback), 500);
  });
}

function loadAppWithRetry(retriesLeft) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.loadURL(FLASK_URL);
  mainWindow.webContents.once('did-fail-load', () => {
    if (retriesLeft > 0) setTimeout(() => loadAppWithRetry(retriesLeft - 1), 1000);
    else showErrorPage('Failed to load application page.');
  });
}

function showErrorPage(errorMessage) {
  const html = `<html><body style="font-family:sans-serif;padding:50px;">
    <h1 style="color:#d32f2f">Startup Error</h1>
    <pre style="background:#eee;padding:20px;">${errorMessage}</pre>
    <p>Please try running from Terminal to see detailed logs.</p>
    <button onclick="location.reload()">Retry</button>
  </body></html>`;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400, height: 900,
    title: 'Receipt & Warranty Manager',
    webPreferences: {
      nodeIntegration: false, contextIsolation: true,
      webSecurity: false, partition: SESSION_PARTITION
    }
  });

  const loadingHtml = `<html><body style="background:#764ba2;color:white;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
    <div style="border:4px solid rgba(255,255,255,.3);border-top:4px solid white;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;"></div>
    <h2>Receipt Manager</h2><p>Starting...</p>
    <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
  </body></html>`;
  mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(loadingHtml));

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Listen for custom protocol to handle "Select Location" button click
  mainWindow.webContents.on('will-navigate', async (event, url) => {
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

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── Main Entry ─────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  // Session / CSP setup
  const ses = session.fromPartition(SESSION_PARTITION);
  ses.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    delete responseHeaders['content-security-policy'];
    delete responseHeaders['Content-Security-Policy'];
    callback({ responseHeaders });
  });

  // Create window first
  createWindow();

  // 1. Data Directory resolution
  let dataPath = getSavedDataPath();
  if (!dataPath) {
    // First time - prompt for location
    dataPath = await promptForDataFolder();
    if (!dataPath) {
      // User cancelled - show "Location Required" page (no crash, no quit)
      showLocationRequiredPage();
      return; // Stop here, wait for user to click button
    }
  }

  // 2. Process management
  killPortProcess(PORT);
  await new Promise(r => setTimeout(r, 1000));
  
  if (!startFlask(dataPath) && startupError) {
    showErrorPage(startupError);
  } else {
    waitForFlask(FLASK_URL, 60, () => loadAppWithRetry(5), (err) => showErrorPage(err));
  }
}).catch(err => {
  dialog.showErrorBox('Startup Error', err.message);
});

app.on('window-all-closed', () => {
  if (flaskProcess) flaskProcess.kill('SIGTERM');
  app.quit();
});
