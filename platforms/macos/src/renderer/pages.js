const { FLASK_URL } = require('../main/constants');
const state = require('../main/state');

function showErrorPage(errorMessage) {
  console.error('[UI] Showing error page:', errorMessage);
  const html = `<html><body style="font-family:sans-serif;padding:50px;">
    <h1 style="color:#d32f2f">Startup Error</h1>
    <pre style="background:#eee;padding:20px;white-space:pre-wrap;word-wrap:break-word;">${errorMessage}</pre>
    <p>Please check the Console.app logs for more details (search for "Receipt Manager" or "Electron").</p>
    <button onclick="location.reload()" style="padding:10px 20px;font-size:16px;cursor:pointer;">Retry</button>
  </body></html>`;
  if (state.mainWindow && !state.mainWindow.isDestroyed()) {
    state.mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  }
}

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
      button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3); }
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
        window.location.href = 'app://select-location';
      });
    </script>
  </body>
  </html>`;

  if (state.mainWindow && !state.mainWindow.isDestroyed()) {
    state.waitingForLocation = true;
    state.mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  }
}

function loadAppWithRetry(retriesLeft) {
  console.log(`[UI] Loading application... (${retriesLeft} retries left)`);
  if (!state.mainWindow || state.mainWindow.isDestroyed()) return;
  state.mainWindow.loadURL(FLASK_URL);
  state.mainWindow.webContents.once('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('[UI] Failed to load:', errorCode, errorDescription);
    if (retriesLeft > 0) {
      setTimeout(() => loadAppWithRetry(retriesLeft - 1), 1000);
    } else {
      showErrorPage('Failed to load application page.');
    }
  });
  state.mainWindow.webContents.once('did-finish-load', () => {
    console.log('[UI] ✓ Application loaded successfully');
  });
}

module.exports = { showErrorPage, showLocationRequiredPage, loadAppWithRetry };
