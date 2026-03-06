// ===== i18next Initialization =====
// Using i18next for internationalization
// Documentation: https://www.i18next.com

// Wait for i18next to load from CDN
if (typeof i18next === 'undefined') {
  console.error('i18next not loaded! Make sure the CDN script is included in HTML.');
} else {
  // Initialize i18next
  i18next.init({
    lng: localStorage.getItem('selectedLanguage') || 'en',
    fallbackLng: 'en',
    debug: false,
    backend: {
      loadPath: '/static/i18n/{{lng}}.json'
    },
    interpolation: {
      escapeValue: false // Not needed for plain JS
    }
  }, function(err, t) {
    if (err) {
      console.error('i18next initialization failed:', err);
      return;
    }
    // Translate the page once i18next is ready
    translatePage();
  });
}

// Translation function wrapper
function t(key, options = {}) {
  if (typeof i18next === 'undefined') {
    console.warn('i18next not available, returning key:', key);
    return key;
  }
  return i18next.t(key, options);
}

// Translate all elements on the page
function translatePage() {
  if (typeof i18next === 'undefined') return;
  
  // Update document title
  document.title = t('appTitle');
  
  // Translate elements with data-i18n attribute
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (el.tagName === 'INPUT' && el.type !== 'button' && el.type !== 'submit') {
      return; // Skip input fields text content
    }
    el.textContent = t(key);
  });
  
  // Translate placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.placeholder = t(key);
  });
  
  // Update language selector
  const langSelect = document.getElementById('languageSelect');
  if (langSelect) {
    langSelect.value = i18next.language;
  }
}

// Change language function
function changeLanguage(langCode) {
  if (typeof i18next === 'undefined') return;
  
  i18next.changeLanguage(langCode, (err, t) => {
    if (err) {
      console.error('Language change failed:', err);
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
    // Setup language selector
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
      langSelect.addEventListener('change', (e) => {
        changeLanguage(e.target.value);
      });
    }
  });
} else {
  // DOM already loaded
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
