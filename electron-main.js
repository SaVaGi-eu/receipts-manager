const { app, BrowserWindow, shell, dialog, session } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

let flaskProcess = null;
let mainWindow = null;
let startupError = null;

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
      pids.split('\
').forEach(pid => {
        try { process.kill(parseInt(pid), 'SIGKILL'); } catch (e) {}
      });
      console.log(`[Electron] Killed stale process(es) on port ${port}:`, pids);
    }
  } catch (e) { /* no process on that port, fine */ }
}

// ── Get the correct base directory ────────────────────────────────────────
function getAppDir() {
  if (!app.isPackaged) return __dirname;
  const unpackedPath = __dirname.replace('app.asar', 'app.asar.unpacked');
  if (fs.existsSync(unpackedPath)) {
    console.log('[App] Using unpacked path:', unpackedPath);
    return unpackedPath;
  }
  return __dirname;
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
  
  const result = await dialog.showMessageBox({
    type: 'question',
    buttons: ['Choose Folder...', 'Use Default (Documents)'],
    defaultId: 1,
    title: 'First Time Setup',
    message: 'Where would you like to store your receipts and database?',
    detail: `If you choose Default, we will create a folder at:
${defaultPath}

You can also choose any other location (like iCloud or an external drive).`,
    noLink: true
  });

  let chosenPath = null;
  if (result.response === 1) {
    chosenPath = defaultPath;
  } else {
    const pickResult = await dialog.showOpenDialog({
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
        dialog.showErrorBox('Folder Error', `Could not create or write to folder:
${e.message}`);
        return promptForDataFolder(); // Try again
      }
    }
    saveSettings(chosenPath);
    return chosenPath;
  } else {
    // User cancelled picking - we can't proceed
    app.quit();
    return null;
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

  waitForFlask(FLASK_URL, 60, () => loadAppWithRetry(5), (err) => showErrorPage(err));
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

  // 1. Data Directory resolution
  let dataPath = getSavedDataPath();
  if (!dataPath) {
    // Show splash window first so dialog doesn't look floating
    createWindow();
    dataPath = await promptForDataFolder();
    if (!dataPath) return; // app.quit() called inside
  } else {
    createWindow();
  }

  // 2. Process management
  killPortProcess(PORT);
  await new Promise(r => setTimeout(r, 1000));
  
  if (!startFlask(dataPath) && startupError) {
    dialog.showErrorBox('Startup Error', startupError);
  }
}).catch(err => {
  dialog.showErrorBox('Startup Error', err.message);
});

app.on('window-all-closed', () => {
  if (flaskProcess) flaskProcess.kill('SIGTERM');
  app.quit();
});
