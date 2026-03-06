// ===== i18next Initialization =====
// Using i18next for internationalization
// Documentation: https://www.i18next.com

// Wait for i18next to load from CDN and be initialized
if (typeof i18next === 'undefined') {
  console.error('i18next not loaded! Make sure the CDN script is included in HTML.');
} else if (typeof i18nextHttpBackend === 'undefined') {
  console.error('i18next-http-backend not loaded! Make sure the CDN script is included in HTML.');
} else {
  // i18next is already initialized in the HTML with the backend
  // We just need to wait for it to be ready
  i18next.on('initialized', function() {
    console.log('[i18n] i18next initialized with language:', i18next.language);
    translatePage();
    // Emit ready event for app.js to start
    window.dispatchEvent(new Event('i18nextReady'));
  });
  
  // If already initialized, trigger immediately
  if (i18next.isInitialized) {
    console.log('[i18n] i18next already initialized');
    translatePage();
    window.dispatchEvent(new Event('i18nextReady'));
  }
}

// Translation function wrapper
function t(key, options = {}) {
  if (typeof i18next === 'undefined' || !i18next.isInitialized) {
    console.warn('[i18n] i18next not ready, returning key:', key);
    return key;
  }
  return i18next.t(key, options);
}

// Translate all elements on the page
function translatePage() {
  if (typeof i18next === 'undefined' || !i18next.isInitialized) {
    console.warn('[i18n] Cannot translate page, i18next not ready');
    return;
  }
  
  console.log('[i18n] Translating page to:', i18next.language);
  
  // Update document title
  document.title = t('appTitle');
  
  // Translate elements with data-i18n attribute
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (el.tagName === 'INPUT' && el.type !== 'button' && el.type !== 'submit') {
      return; // Skip input fields text content
    }
    const translated = t(key);
    if (translated !== key) {
      el.textContent = translated;
    }
  });
  
  // Translate placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    const translated = t(key);
    if (translated !== key) {
      el.placeholder = translated;
    }
  });
  
  // Update language selector
  const langSelect = document.getElementById('languageSelect');
  if (langSelect) {
    langSelect.value = i18next.language;
  }
  
  console.log('[i18n] Page translation complete');
}

// Change language function
function changeLanguage(langCode) {
  if (typeof i18next === 'undefined' || !i18next.isInitialized) {
    console.error('[i18n] Cannot change language, i18next not ready');
    return;
  }
  
  console.log('[i18n] Changing language to:', langCode);
  
  i18next.changeLanguage(langCode, (err, t) => {
    if (err) {
      console.error('[i18n] Language change failed:', err);
      return;
    }
    localStorage.setItem('selectedLanguage', langCode);
    translatePage();
    
    // Trigger custom event for other scripts that need to update
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: langCode } }));
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setupLanguageSelector();
  });
} else {
  setupLanguageSelector();
}

function setupLanguageSelector() {
  const langSelect = document.getElementById('languageSelect');
  if (langSelect) {
    langSelect.addEventListener('change', (e) => {
      changeLanguage(e.target.value);
    });
  }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.t = t;
  window.changeLanguage = changeLanguage;
  window.translatePage = translatePage;
  
  // For backwards compatibility
  Object.defineProperty(window, 'currentLanguage', {
    get: function() {
      return typeof i18next !== 'undefined' ? i18next.language : 'en';
    }
  });
}
