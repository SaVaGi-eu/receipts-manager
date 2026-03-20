const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const state = require('../main/state');
const { getAppDir } = require('../utils/port');

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
  state.startupError = 'Python 3 not found. Please install Python 3 from python.org';
  return null;
}

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
    state.startupError = `Cannot find app.py at: ${appPath}`;
    return false;
  }

  console.log('[Server] ✓ app.py found');
  console.log('[Server] Starting with DATA_DIR:', dataPath);

  try {
    state.flaskProcess = spawn(pythonPath, [appPath], {
      cwd: appDir,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        DATA_DIR: dataPath
      }
    });

    console.log('[Server] ✓ Process spawned with PID:', state.flaskProcess.pid);

    state.flaskProcess.stdout.on('data', d => {
      console.log('[Server STDOUT]', d.toString().trim());
    });

    state.flaskProcess.stderr.on('data', d => {
      const msg = d.toString().trim();
      console.log('[Server STDERR]', msg);
      if (msg.includes('Error') || msg.includes('Traceback')) {
        state.startupError = msg;
      }
    });

    state.flaskProcess.on('error', (err) => {
      console.error('[Server] Process error:', err);
      state.startupError = `Process error: ${err.message}`;
    });

    state.flaskProcess.on('exit', (code, signal) => {
      console.log(`[Server] Process exited with code ${code} and signal ${signal}`);
    });

    return true;
  } catch (err) {
    console.error('[Server] Exception starting server:', err);
    state.startupError = `Exception starting server: ${err.message}`;
    return false;
  }
}

function waitForFlask(url, retries, callback, errorCallback) {
  console.log(`[Server] Waiting for server to respond... (${retries} retries left)`);
  const req = http.get(url, (res) => {
    res.resume();
    if (res.statusCode < 500) {
      console.log('[Server] ✓ Server is ready! Status:', res.statusCode);
      callback();
    } else {
      console.log('[Server] Server responded with error status:', res.statusCode);
      if (retries <= 0) { errorCallback(`Server error: ${res.statusCode}`); return; }
      setTimeout(() => waitForFlask(url, retries - 1, callback, errorCallback), 500);
    }
  });
  req.setTimeout(2000, () => {
    console.log('[Server] Request timeout, retrying...');
    req.destroy();
  });
  req.on('error', (err) => {
    console.log('[Server] Connection error:', err.message.replace(/\n|\r/g, ''));
    if (retries <= 0) { errorCallback(state.startupError || 'Server timeout'); return; }
    setTimeout(() => waitForFlask(url, retries - 1, callback, errorCallback), 500);
  });
}

module.exports = { findPython, startFlask, waitForFlask };
