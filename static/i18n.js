// ===== i18next Initialization =====
// Using i18next for internationalization
// Documentation: https://www.i18next.com

// Translation function wrapper
function t(key, options = {}) {
  if (typeof i18next === 'undefined' || !i18next.isInitialized) {
    console.warn('[i18n] i18next not ready, returning key:', key);
    return key;
  }
  return i18next.t(key, options);
}

// Wait for i18next libraries to load from CDN
function initializeI18next() {
  if (typeof i18next === 'undefined') {
    console.error('[i18n] i18next not loaded! Make sure the CDN script is included in HTML.');
    return;
  }
  
  if (typeof i18nextHttpBackend === 'undefined') {
    console.error('[i18n] i18next-http-backend not loaded! Make sure the CDN script is included in HTML.');
    return;
  }

  console.log('[i18n] Initializing i18next...');
  
  // Initialize i18next with HTTP backend
  i18next
    .use(i18nextHttpBackend)
    .init({
      lng: localStorage.getItem('selectedLanguage') || 'en',
      fallbackLng: 'en',
      debug: false,
      backend: {
        loadPath: '/static/i18n/{{lng}}.json'
      },
      interpolation: {
        escapeValue: false
      }
    }, function(err, t) {
      if (err) {
        console.error('[i18n] Initialization error:', err);
        return;
      }
      console.log('[i18n] i18next initialized with language:', i18next.language);
      
      // Set up all global exports
      setupGlobalExports();
      
      // Now translate the page
      translatePage();
      
      // Emit ready event for app.js to start
      window.dispatchEvent(new Event('i18nextReady'));
    });
}

// Start initialization when this script loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeI18next);
} else {
  // DOM already loaded, init immediately
  initializeI18next();
}

// Translate all elements on the page
function translatePage() {
  if (typeof i18next === 'undefined' || !i18next.isInitialized) {
    console.warn('[i18n] Cannot translate page, i18next not ready');
    return;
  }
  
  console.log('[i18n] Translating page to:', i18next.language);
  
  // Update document title - use i18next.t directly to bypass any wrapper
  document.title = i18next.t('appTitle');
  
  // Translate elements with data-i18n attribute
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (el.tagName === 'INPUT' && el.type !== 'button' && el.type !== 'submit') {
      return; // Skip input fields text content
    }
    // Use i18next.t directly instead of calling t()
    const translated = i18next.t(key);
    if (translated !== key) {
      el.textContent = translated;
    }
  });
  
  // Translate placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    // Use i18next.t directly
    const translated = i18next.t(key);
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

// Setup language selector
function setupLanguageSelector() {
  const langSelect = document.getElementById('languageSelect');
  if (langSelect) {
    langSelect.addEventListener('change', (e) => {
      changeLanguage(e.target.value);
    });
  }
}

// Initialize language selector when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupLanguageSelector);
} else {
  setupLanguageSelector();
}

// Set up global exports
function setupGlobalExports() {
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
}
