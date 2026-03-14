const fs = require('fs');
const { SETTINGS_FILE, SETTINGS_DIR, APP_NAME } = require('../main/constants');

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

module.exports = { getSavedDataPath, saveSettings };
