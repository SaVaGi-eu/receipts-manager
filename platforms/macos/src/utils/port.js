const { execSync } = require('child_process');
const { app } = require('electron');
const path = require('path');

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

function getAppDir() {
  if (!app.isPackaged) {
    // In development, go up four levels from src/utils/ to reach the project root
    const dir = path.join(__dirname, '..', '..', '..', '..');
    console.log('[Electron] Running in development mode, app dir:', dir);
    return dir;
  }
  // When packaged, extraResources are in Contents/Resources/
  console.log('[Electron] Running in packaged mode, resources path:', process.resourcesPath);
  return process.resourcesPath;
}

module.exports = { killPortProcess, getAppDir };
