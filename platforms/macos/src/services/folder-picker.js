const { app, dialog } = require('electron');
const fs = require('fs');
const path = require('path');
const state = require('../main/state');
const { saveSettings } = require('./settings');

async function promptForDataFolder() {
  const defaultPath = path.join(app.getPath('documents'), 'Receipts Manager');

  console.log('[FolderPicker] Showing folder picker dialog...');
  const result = await dialog.showMessageBox(state.mainWindow, {
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
    const pickResult = await dialog.showOpenDialog(state.mainWindow, {
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
        fs.mkdirSync(path.join(chosenPath, 'database'), { recursive: true });
        fs.mkdirSync(path.join(chosenPath, 'storage'), { recursive: true });
        console.log('[FolderPicker] ✓ Directory structure created successfully');
      } catch (e) {
        console.error('[FolderPicker] ✗ Error creating directory:', e);
        await dialog.showMessageBox(state.mainWindow, {
          type: 'error',
          title: 'Folder Error',
          message: 'Could not create or write to folder',
          detail: e.message,
          buttons: ['Try Again']
        });
        return promptForDataFolder();
      }
    }
    saveSettings(chosenPath);
    return chosenPath;
  }

  return null;
}

module.exports = { promptForDataFolder };
