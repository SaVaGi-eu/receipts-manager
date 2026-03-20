const { app } = require('electron');
const path = require('path');

const PORT = 8765; // Matches app.py — avoids macOS AirPlay on port 5000
const FLASK_URL = `http://127.0.0.1:${PORT}`;
const SESSION_PARTITION = 'persist:receiptmanager';
const APP_NAME = 'Receipt Manager';
const SETTINGS_DIR = path.join(app.getPath('home'), 'Library', 'Application Support', APP_NAME);
const SETTINGS_FILE = path.join(SETTINGS_DIR, 'settings.json');

module.exports = { PORT, FLASK_URL, SESSION_PARTITION, APP_NAME, SETTINGS_DIR, SETTINGS_FILE };
