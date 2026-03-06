# i18next Migration Guide

## Overview

We have successfully migrated the Receipt Manager from a custom translation system to [i18next](https://www.i18next.com), a professional-grade internationalization framework.

## What Changed?

### Before (Custom System)
- `static/translations.js` - Custom translation object with manual language switching
- Translations embedded in a single JavaScript file
- Simple string replacement with `{count}` placeholders
- Manual pluralization logic

### After (i18next)
- `static/i18n.js` - i18next initialization and helper functions
- `static/i18n/*.json` - Separate JSON files for each language (en, el, nl, lv)
- i18next library loaded from CDN (jsDelivr)
- Built-in pluralization support with `_one`, `_other` suffixes
- HTTP backend for loading translations dynamically

## Benefits

1. **Industry Standard** - i18next is the most popular JavaScript i18n library
2. **Better Pluralization** - Automatic handling of singular/plural forms per language
3. **Easier Maintenance** - Translations in separate JSON files
4. **Scalability** - Easy to add new languages without modifying code
5. **Community Support** - Well-documented with active community
6. **Translation Management** - Can integrate with services like Lokalise, POEditor, Crowdin later

## File Structure

```
static/
├── i18n/
│   ├── en.json     # English translations
│   ├── el.json     # Greek translations (Ελληνικά)
│   ├── nl.json     # Dutch translations (Nederlands)
│   └── lv.json     # Latvian translations (Latviešu)
├── i18n.js          # i18next initialization
└── app.js           # Main application logic
```

## How It Works

### 1. Loading i18next

The HTML template loads i18next from CDN:

```html
<script src="https://cdn.jsdelivr.net/npm/i18next@23.7.16/i18next.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/i18next-http-backend@2.4.3/i18nextHttpBackend.min.js"></script>
```

### 2. Initialization

i18next is initialized inline in the HTML with the HTTP backend plugin:

```javascript
i18next
  .use(i18nextHttpBackend)
  .init({
    lng: localStorage.getItem('selectedLanguage') || 'en',
    fallbackLng: 'en',
    backend: {
      loadPath: '/static/i18n/{{lng}}.json'
    }
  });
```

### 3. Translation Function

The `t()` function is exposed globally:

```javascript
// Simple translation
t('appTitle')  // Returns: "🧾 Receipt & Warranty Manager"

// With interpolation
t('itemCount', { count: 5 })  // Returns: "5 items"
t('itemCount', { count: 1 })  // Returns: "1 item" (automatic pluralization)
```

### 4. Language Switching

```javascript
changeLanguage('el')  // Switch to Greek
changeLanguage('nl')  // Switch to Dutch
changeLanguage('lv')  // Switch to Latvian
```

## Adding a New Language

1. **Create translation file**: `static/i18n/[code].json`
2. **Copy structure** from `en.json`
3. **Translate all strings**
4. **Add to language selector** in `templates/index.html`:
   ```html
   <option value="[code]">🏴 [Language Name]</option>
   ```

### Example: Adding French

```json
// static/i18n/fr.json
{
  "appTitle": "🧾 Gestionnaire de Reçus & Garanties",
  "language": "Langue:",
  "itemCount": "{{count}} éléments",
  "itemCount_one": "{{count}} élément",
  "itemCount_other": "{{count}} éléments",
  ...
}
```

Then add to HTML:
```html
<option value="fr">🇫🇷 Français</option>
```

## Pluralization

i18next automatically handles pluralization based on the `count` parameter:

```json
{
  "itemCount": "{{count}} items",
  "itemCount_one": "{{count}} item",
  "itemCount_other": "{{count}} items"
}
```

When you call `t('itemCount', { count: 1 })`, i18next automatically selects `itemCount_one`.

## Interpolation

Use `{{variable}}` syntax for dynamic values:

```json
{
  "greeting": "Hello, {{name}}!",
  "itemCount": "{{count}} items"
}
```

```javascript
t('greeting', { name: 'John' })  // "Hello, John!"
t('itemCount', { count: 42 })    // "42 items"
```

## Migration Checklist

- [x] Created JSON translation files for all 4 languages
- [x] Added i18next CDN scripts to HTML
- [x] Created `i18n.js` initialization file
- [x] Updated `app.js` to use i18next `t()` function
- [x] Removed old `translations.js` file (deprecated)
- [x] Tested language switching
- [x] Verified pluralization works correctly
- [x] Documented the new system

## Backward Compatibility

The old `translations.js` file is now deprecated but has not been deleted yet. To complete the migration:

```bash
# Remove the old file
git rm static/translations.js
git commit -m "chore: Remove deprecated translations.js"
```

## Testing

1. **Pull the changes**:
   ```bash
   cd ~/receipts-manager
   git pull origin main
   ```

2. **Restart the app**:
   ```bash
   ./install.sh
   # Choose option 3 (Run application)
   ```

3. **Test language switching**:
   - Open the app in browser
   - Change language using the dropdown
   - Verify all UI elements translate correctly
   - Check that item counts show proper pluralization

## Resources

- [i18next Documentation](https://www.i18next.com)
- [i18next Pluralization](https://www.i18next.com/translation-function/plurals)
- [i18next Interpolation](https://www.i18next.com/translation-function/interpolation)
- [HTTP Backend Plugin](https://github.com/i18next/i18next-http-backend)

## Future Enhancements

1. **Translation Management Platform** - Integrate with Lokalise or Crowdin for collaborative translation
2. **Lazy Loading** - Load translations only when needed to reduce initial load time
3. **Namespaces** - Split translations into logical groups (common, forms, errors, etc.)
4. **Language Detection** - Auto-detect user's browser language
5. **More Languages** - Add Spanish, German, Italian, Portuguese, etc.

## Support

If you encounter any issues with translations:

1. Check browser console for i18next errors
2. Verify the JSON files are valid (use a JSON validator)
3. Ensure the translation key exists in all language files
4. Check that i18next CDN scripts loaded successfully

---

**Migration completed**: March 6, 2026
**i18next version**: 23.7.16
**Supported languages**: English (en), Greek (el), Dutch (nl), Latvian (lv)
