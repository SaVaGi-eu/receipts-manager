// ===================== Settings & Menu Modal (RM-80) =====================

// Current storage configuration (loaded from backend)
let currentConfig = {
  storageType: 'local',
  dataFile: '/data/receipts.json'
};

/**
 * Initialize settings modal functionality
 */
function initSettingsModal() {
  const menuBtn = document.getElementById('menuBtn');
  const menuModal = document.getElementById('menuModal');
  const closeMenuModal = document.getElementById('closeMenuModal');
  const closeMenuModalBtn = document.getElementById('closeMenuModalBtn');
  const changeLocationBtn = document.getElementById('changeLocationBtn');

  // Open settings modal
  if (menuBtn) {
    menuBtn.addEventListener('click', () => {
      if (menuModal) {
        menuModal.style.display = 'flex';
        loadCurrentConfig();
      }
    });
  }

  // Close settings modal
  [closeMenuModal, closeMenuModalBtn].forEach(btn => {
    if (btn) {
      btn.addEventListener('click', () => {
        if (menuModal) menuModal.style.display = 'none';
      });
    }
  });

  // Click outside to close
  if (menuModal) {
    menuModal.addEventListener('click', (e) => {
      if (e.target === menuModal) {
        menuModal.style.display = 'none';
      }
    });
  }

  // Change location button
  if (changeLocationBtn) {
    changeLocationBtn.addEventListener('click', () => {
      openLocationModal();
    });
  }

  // Menu action buttons
  const menuBackupBtn = document.getElementById('menuBackupBtn');
  const menuRestoreBtn = document.getElementById('menuRestoreBtn');
  const menuExportBtn = document.getElementById('menuExportBtn');

  if (menuBackupBtn) {
    menuBackupBtn.addEventListener('click', () => {
      // Reuse existing export function
      if (typeof exportJson === 'function') exportJson();
    });
  }

  if (menuRestoreBtn) {
    menuRestoreBtn.addEventListener('click', () => {
      // Reuse existing import function
      const importInput = document.getElementById('importInput');
      if (importInput) importInput.click();
    });
  }

  if (menuExportBtn) {
    menuExportBtn.addEventListener('click', () => {
      // Reuse existing CSV export
      if (typeof exportCsv === 'function') exportCsv();
    });
  }

  // Language selector
  const languageSelect = document.getElementById('languageSelect');
  if (languageSelect) {
    // Set current language
    const currentLang = localStorage.getItem('language') || 'en';
    languageSelect.value = currentLang;

    languageSelect.addEventListener('change', (e) => {
      const newLang = e.target.value;
      localStorage.setItem('language', newLang);
      // If i18n is available, change language
      if (typeof i18next !== 'undefined' && i18next.changeLanguage) {
        i18next.changeLanguage(newLang);
      }
      // Optionally reload to apply changes
      // window.location.reload();
    });
  }
}

/**
 * Load current configuration and display it
 */
function loadCurrentConfig() {
  // Update display elements
  const storageTypeEl = document.getElementById('currentStorageType');
  const storagePathEl = document.getElementById('currentStoragePath');

  if (storageTypeEl) {
    storageTypeEl.textContent = currentConfig.storageType === 'local' ? 'Local' : 'Cloud';
  }

  if (storagePathEl) {
    storagePathEl.textContent = currentConfig.dataFile || '/data/receipts.json';
  }
}

/**
 * Open location change modal
 */
function openLocationModal() {
  const locationModal = document.getElementById('locationModal');
  const localPathInput = document.getElementById('localPathInput');

  if (locationModal) {
    locationModal.style.display = 'flex';

    // Set current path
    if (localPathInput) {
      localPathInput.value = currentConfig.dataFile || '/data/receipts.json';
    }

    // Initialize location modal handlers if not already done
    initLocationModal();
  }
}

/**
 * Initialize location change modal functionality
 */
function initLocationModal() {
  const locationModal = document.getElementById('locationModal');
  const closeLocationModal = document.getElementById('closeLocationModal');
  const cancelLocationChange = document.getElementById('cancelLocationChange');
  const applyLocationChange = document.getElementById('applyLocationChange');
  const browsePathBtn = document.getElementById('browsePathBtn');
  const storageRadios = document.querySelectorAll('input[name="storage"]');
  const localPathSection = document.getElementById('localPathSection');

  // Close handlers
  [closeLocationModal, cancelLocationChange].forEach(btn => {
    if (btn) {
      btn.addEventListener('click', () => {
        if (locationModal) locationModal.style.display = 'none';
      });
    }
  });

  // Click outside to close
  if (locationModal) {
    locationModal.addEventListener('click', (e) => {
      if (e.target === locationModal) {
        locationModal.style.display = 'none';
      }
    });
  }

  // Toggle local path section based on storage type
  storageRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      if (localPathSection) {
        localPathSection.style.display = e.target.value === 'local' ? 'block' : 'none';
      }
    });
  });

  // RM-80: Browse button - opens native file dialog
  if (browsePathBtn) {
    browsePathBtn.addEventListener('click', async () => {
      try {
        console.log('[Settings] Calling /api/browse/path...');
        const response = await fetch('/api/browse/path');
        const result = await response.json();

        console.log('[Settings] Browse result:', result);

        if (result.success && result.path) {
          const localPathInput = document.getElementById('localPathInput');
          if (localPathInput) {
            localPathInput.value = result.path;
            console.log('[Settings] Path updated to:', result.path);
          }
        } else {
          console.log('[Settings] No file selected or error:', result.error);
          // Don't show alert for cancellation
          if (result.error && result.error !== 'No file selected') {
            alert(`Browse failed: ${result.error}`);
          }
        }
      } catch (err) {
        console.error('[Settings] Browse error:', err);
        alert(`Error opening file browser: ${err.message}`);
      }
    });
  }

  // Apply changes
  if (applyLocationChange) {
    applyLocationChange.addEventListener('click', () => {
      applyLocationSettings();
    });
  }
}

/**
 * Apply location settings changes
 */
function applyLocationSettings() {
  const storageType = document.querySelector('input[name="storage"]:checked')?.value || 'local';
  const localPathInput = document.getElementById('localPathInput');
  const newPath = localPathInput?.value?.trim();

  if (storageType === 'local' && !newPath) {
    alert('Please provide a valid file path.');
    return;
  }

  // Update config
  currentConfig.storageType = storageType;
  currentConfig.dataFile = newPath;

  // Save to localStorage (for demo purposes)
  localStorage.setItem('storageConfig', JSON.stringify(currentConfig));

  // Show confirmation
  alert('Storage location updated! The application needs to restart for changes to take effect.\n\nNote: This is a UI demo. Backend integration coming soon.');

  // Update display
  loadCurrentConfig();

  // Close modals
  const locationModal = document.getElementById('locationModal');
  const menuModal = document.getElementById('menuModal');
  if (locationModal) locationModal.style.display = 'none';
  if (menuModal) menuModal.style.display = 'none';
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSettingsModal);
} else {
  initSettingsModal();
}

// Load saved config from localStorage on startup
try {
  const savedConfig = localStorage.getItem('storageConfig');
  if (savedConfig) {
    currentConfig = JSON.parse(savedConfig);
  }
} catch (e) {
  console.warn('[Settings] Failed to load saved config:', e);
}
