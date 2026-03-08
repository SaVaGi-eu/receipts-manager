# Implementation Notes for RM-75, 77, 78, 79, 80

## RM-75: Fix ID Sorting
**Status**: Requires implementation
**Files to modify**:
- `static/app.js` - Update `sortRows()` function to use natural sort for ID column

**Implementation**:
```javascript
function naturalSort(a, b, key) {
  const aVal = String(a?.[key] ?? '');
  const bVal = String(b?.[key] ?? '');
  
  // Extract numbers for numeric comparison
  const aNum = parseInt(aVal.match(/\d+/)?.[0]) || 0;
  const bNum = parseInt(bVal.match(/\d+/)?.[0]) || 0;
  
  if (aNum !== bNum) {
    return aNum - bNum;
  }
  return aVal.localeCompare(bVal);
}

function sortRows(rows) {
  const col = currentSort.column;
  const dir = currentSort.direction === 'desc' ? -1 : 1;
  
  return [...rows].sort((a, b) => {
    if (col === 'id') {
      return naturalSort(a, b, col) * dir;
    }
    return String(a?.[col] ?? '').localeCompare(String(b?.[col] ?? '')) * dir;
  });
}
```

## RM-77: Add Extended Warranty Checkbox
**Status**: Requires implementation
**Files to modify**:
- `app.py` - Add extended warranty fields to item model
- `templates/index.html` - Add UI elements
- `static/app.js` - Handle extended warranty data
- `static/css/style.css` - Style conditional fields

**Data Model Changes**:
Add to item object:
- `extended_warranty`: boolean
- `extended_warranty_provider`: string
- `extended_warranty_months`: number
- `extended_warranty_cost`: number

**HTML Addition** (after warranty field):
```html
<div class="form-group">
  <label>
    <input type="checkbox" id="modalExtendedWarranty">
    <span data-i18n="labelExtendedWarranty">Extended Warranty Purchased?</span>
  </label>
</div>

<div id="extendedWarrantyFields" class="extended-warranty-fields" style="display:none;">
  <div class="form-row">
    <div class="form-group">
      <label for="modalExtWarrantyProvider" data-i18n="labelExtWarrantyProvider">Provider</label>
      <input type="text" id="modalExtWarrantyProvider">
    </div>
    <div class="form-group">
      <label for="modalExtWarrantyMonths" data-i18n="labelExtWarrantyMonths">Duration (months)</label>
      <input type="number" id="modalExtWarrantyMonths" min="1">
    </div>
  </div>
  <div class="form-group">
    <label for="modalExtWarrantyCost" data-i18n="labelExtWarrantyCost">Cost</label>
    <input type="number" id="modalExtWarrantyCost" min="0" step="0.01">
  </div>
</div>
```

## RM-78: Make Brand and Model Required
**Status**: Requires implementation
**Files to modify**:
- `templates/index.html` - Add required attribute and asterisks
- `static/app.js` - Update validation

**HTML Changes**:
```html
<label for="modalBrand">
  <span data-i18n="labelBrand">Brand</span> 
  <span class="required-asterisk">*</span>
</label>
<input type="text" id="modalBrand" list="brandList" required>

<label for="modalModel">
  <span data-i18n="labelModel">Model</span> 
  <span class="required-asterisk">*</span>
</label>
<input type="text" id="modalModel" list="modelList" required>
```

**Validation in saveOcrData**:
```javascript
const brand = $('modalBrand').value.trim();
const model = $('modalModel').value.trim();

if (!brand || !model) {
  alert('Brand and Model are required fields');
  return;
}
```

## RM-79: Add Category Field
**Status**: Requires implementation
**Files to modify**:
- `app.py` - Add category to item model and suggestions
- `templates/index.html` - Add category field and datalist
- `static/app.js` - Handle category data
- Translation files - Add category translations

**Data Model**: Add `category` field to items

**HTML Addition** (between Location and Project):
```html
<div class="form-group">
  <label for="modalCategory" data-i18n="labelCategory">Category</label>
  <input type="text" id="modalCategory" list="categoryList">
</div>
```

Add datalist:
```html
<datalist id="categoryList"></datalist>
```

**Table Column**: Add category column to table

## RM-80: Replace Language Selector with Menu Button
**Status**: Requires implementation
**Files to modify**:
- `templates/index.html` - Replace selector with menu button
- `static/app.js` - Add menu toggle logic
- `static/css/style.css` - Style menu dropdown

**HTML Structure**:
```html
<div class="header-right">
  <span id="itemCount" class="item-count">0 items</span>
  <button id="menuButton" class="menu-button">⋮</button>
  <div id="menuDropdown" class="menu-dropdown hidden">
    <div class="menu-item menu-version">Version 1.0.0</div>
    <div class="menu-separator"></div>
    <div class="menu-section">
      <div class="menu-item-label">Language</div>
      <select id="languageSelect" class="menu-select">...</select>
    </div>
    <div class="menu-separator"></div>
    <button class="menu-item" id="menuBackup">Backup</button>
    <button class="menu-item" id="menuRestore">Restore</button>
    <div class="menu-separator"></div>
    <button class="menu-item" id="menuExportJson">Export JSON</button>
    <button class="menu-item" id="menuExportCsv">Export CSV</button>
    <button class="menu-item" id="menuImport">Import</button>
  </div>
</div>
```

## Testing Checklist

### RM-75
- [ ] ID column sorts 1, 2, 3... 10, 11 (not 1, 10, 11, 2)
- [ ] Ascending and descending work correctly
- [ ] Other columns still sort alphabetically

### RM-77
- [ ] Checkbox appears below warranty field
- [ ] Conditional fields show/hide on checkbox toggle
- [ ] Data saves correctly
- [ ] Data displays in table or detail view
- [ ] Fields clear when unchecked

### RM-78
- [ ] Red asterisks visible on Brand and Model labels
- [ ] Form validation prevents submission without Brand
- [ ] Form validation prevents submission without Model
- [ ] Error message displays clearly
- [ ] HTML5 validation works

### RM-79
- [ ] Category field appears in form
- [ ] Autocomplete works
- [ ] Category saves with item
- [ ] Category appears in table
- [ ] Category included in CSV/JSON export
- [ ] Category filter works (if implemented)
- [ ] Column toggle includes category

### RM-80
- [ ] Menu button visible in header
- [ ] Menu opens on click
- [ ] Menu closes on outside click
- [ ] Menu closes on ESC key
- [ ] Version displays correctly
- [ ] Language selector works in menu
- [ ] All export/import buttons work
- [ ] Mobile responsive
- [ ] Toolbar buttons removed/relocated

## Translation Keys to Add

### RM-77
- `labelExtendedWarranty`: "Extended Warranty Purchased?"
- `labelExtWarrantyProvider`: "Provider"
- `labelExtWarrantyMonths`: "Duration (months)"
- `labelExtWarrantyCost`: "Cost"

### RM-79
- `labelCategory`: "Category"
- `colCategory`: "Category"
- `allCategories`: "All Categories"

### RM-80
- `menu`: "Menu"
- `version`: "Version"
- `backup`: "Backup"
- `restore`: "Restore"
- `dataLocation`: "Data Location"

## Notes
- All changes maintain backward compatibility
- Existing data without new fields will display correctly
- Security validations remain intact
- No breaking changes to API
