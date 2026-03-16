// ===================== GLOBAL STATE =====================
let allData    = { receipts: [], items: [], next_id: 1, integrity_issues: [] };
let suggestions = { shops: [], brands: [], models: [], locations: [], documentation: [], projects: [], users: [], categories: [] };
let appSettings = { currency: 'EUR', currency_display_format: 'symbol', warranty_expiration_warning_months: 3 };
let currentSort  = { column: 'id', direction: 'asc' };
let visibleColumns = new Set([
  'id', 'receipt_group_id', 'brand', 'model', 'location', 'category', 'users',
  'project', 'shop', 'purchase_date', 'documentation', 'guarantee_end_date',
  'extended_warranty', 'price', 'file', 'actions'
]);
let userTagsArray = [];
let sessionGroupId  = null;
let sessionItemIds  = [];

// ===================== CONSTANTS =====================
const CURRENCY_SYMBOLS = {
  EUR:'€', USD:'$', GBP:'£', CHF:'Fr', SEK:'kr', NOK:'kr', DKK:'kr',
  PLN:'zł', CZK:'Kč', HUF:'Ft', RON:'lei', BGN:'лв', HRK:'kn',
  JPY:'¥', CNY:'¥', AUD:'A$', CAD:'C$', NZD:'NZ$', BRL:'R$',
  INR:'₹', KRW:'₩', TRY:'₺', ZAR:'R', MXN:'$'
};
const CURRENCIES = [
  'EUR','USD','GBP','CHF','SEK','NOK','DKK','PLN','CZK','HUF',
  'RON','BGN','HRK','JPY','CNY','AUD','CAD','NZD','BRL','INR','KRW','TRY','ZAR','MXN'
];

const API = {
  data:           '/api/data',
  suggestions:    '/api/suggestions',
  settings:       '/api/settings',
  exportJson:     '/api/export/json',
  exportCsv:      '/api/export/csv',
  importJson:     '/api/import/json',
  integrityCheck: '/api/integrity/check',
  upload:         '/api/upload',
  uploadDoc:      '/api/upload/document',
  createItem:     '/api/item',
  updateItem: id  => `/api/item/${id}`,
  deleteItem: id  => `/api/item/${id}`,
  fileUrl:    p   => `/api/file?path=${encodeURIComponent(p)}`
};

// ===================== HELPERS =====================
function $(id)    { return document.getElementById(id); }
function qs(sel)  { return document.querySelector(sel); }
function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }

function bind(id, ev, fn) {
  const el = $(id);
  if (!el) return;
  el.addEventListener(ev, fn);
}

async function fetchJson(url, opts) {
  const resp = await fetch(url, opts);
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`${opts?.method || 'GET'} ${url} failed: ${resp.status} ${text}`);
  }
  return resp.json();
}

function downloadUrl(url) {
  const a = document.createElement('a');
  a.href = url; a.download = '';
  document.body.appendChild(a); a.click(); a.remove();
}
function exportJson() { downloadUrl(API.exportJson); }
function exportCsv()  { downloadUrl(API.exportCsv); }

function escHtml(s)  { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function escAttr(s)  { return String(s).replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

function formatPrice(price) {
  if (price == null || price === '') return '—';
  const num = parseFloat(price);
  if (isNaN(num)) return '—';
  const formatted = num.toFixed(2);
  if (appSettings.currency_display_format === 'symbol') {
    return (CURRENCY_SYMBOLS[appSettings.currency] || appSettings.currency) + formatted;
  }
  return appSettings.currency + ' ' + formatted;
}

// ===================== USER TAGS =====================
function addUserTag(name) {
  name = (name || '').trim();
  if (!name || userTagsArray.includes(name)) return;
  userTagsArray.push(name);
  renderUserTags();
}
function removeUserTag(name) {
  userTagsArray = userTagsArray.filter(u => u !== name);
  renderUserTags();
}
function renderUserTags() {
  const container = $('userTags');
  if (!container) return;
  container.innerHTML = userTagsArray.map(u =>
    `<span class="user-tag">${escHtml(u)}<button type="button" class="tag-remove" data-name="${escAttr(u)}">&times;</button></span>`
  ).join('');
  container.querySelectorAll('.tag-remove').forEach(btn =>
    btn.addEventListener('click', () => removeUserTag(btn.dataset.name))
  );
}
function clearUserTags() {
  userTagsArray = [];
  renderUserTags();
  const i = $('userTagInput'); if (i) i.value = '';
}
function setUserTags(users) {
  userTagsArray = Array.isArray(users) ? [...users] : [];
  renderUserTags();
}

// ===================== DATA LOADING =====================
async function loadData() {
  try {
    allData = await fetchJson(API.data);
    const banner  = $('integrityBanner');
    const issues  = allData.integrity_issues || [];
    if (banner) banner.style.display = issues.length > 0 ? 'block' : 'none';
    if ($('integrityMessage')) $('integrityMessage').textContent = issues.length > 0 ? `${issues.length} integrity issue(s) detected.` : '';
    filterAndRender();
  } catch (err) { console.error('Error loading data:', err); alert('Error loading data (see Console).'); }
}

async function loadSuggestions() {
  try {
    suggestions = await fetchJson(API.suggestions);
    populateDataLists();
    populateFilterDropdowns();
  } catch (err) { console.error('Error loading suggestions:', err); }
}

async function loadSettings() {
  try { appSettings = await fetchJson(API.settings); } catch { /* use defaults */ }
  renderSettingsUI();
}

function renderSettingsUI() {
  // Populate currency select
  const currSel = $('currencySelect');
  if (currSel) {
    currSel.innerHTML = CURRENCIES.map(c =>
      `<option value="${c}"${c === appSettings.currency ? ' selected' : ''}>${c}</option>`
    ).join('');
  }
  const fmtSel = $('currencyFormatSelect');
  if (fmtSel) fmtSel.value = appSettings.currency_display_format || 'symbol';
  const warnInp = $('warrantyWarningInput');
  if (warnInp) warnInp.value = appSettings.warranty_expiration_warning_months ?? 3;
}

// ===================== DATALISTS =====================
function populateDataLists() {
  const set = (id, arr) => {
    const el = $(id); if (!el) return;
    el.innerHTML = (Array.isArray(arr) ? arr : []).map(s => `<option value="${escAttr(String(s))}">`).join('');
  };
  set('shopList',     suggestions.shops);
  set('brandList',    suggestions.brands);
  set('modelList',    suggestions.models);
  set('locationList', suggestions.locations);
  set('docList',      suggestions.documentation);
  set('projectList',  suggestions.projects);
  set('userList',     suggestions.users);
  set('categoryList', suggestions.categories);
}

function populateFilterDropdowns() {
  const projectFilter = $('projectFilter');
  if (projectFilter) {
    const cur = projectFilter.value;
    projectFilter.innerHTML = '<option value="">All Projects</option>' +
      (suggestions.projects || []).map(p => `<option value="${escAttr(String(p))}">${escHtml(p)}</option>`).join('');
    projectFilter.value = cur;
  }
  const userFilter = $('userFilter');
  if (userFilter) {
    const cur = userFilter.value;
    userFilter.innerHTML = '<option value="">All Users</option>' +
      (suggestions.users || []).map(u => `<option value="${escAttr(String(u))}">${escHtml(u)}</option>`).join('');
    userFilter.value = cur;
  }
}

function populateExistingReceiptSelect() {
  const sel = $('existingReceiptSelect');
  if (!sel) return;
  const receipts = allData.receipts || [];
  sel.innerHTML = '<option value="">-- Choose existing receipt --</option>' +
    receipts.map(r => {
      const label = [r.receipt_group_id, r.shop, r.purchase_date].filter(Boolean).join(' · ');
      return `<option value="${escAttr(r.receipt_group_id)}">${escHtml(label)}</option>`;
    }).join('');
}

// ===================== TABLE =====================
function receiptMap() {
  const map = new Map();
  (allData.receipts || []).forEach(r => map.set(r.receipt_group_id, r));
  return map;
}

function normalizeUsers(u) {
  if (Array.isArray(u)) return u;
  return String(u || '').split(';').map(s => s.trim()).filter(Boolean);
}

function calcExtWarrantyEndDate(row) {
  const ext = row.extended_warranty;
  if (!ext || !parseInt(ext.months)) return null;
  const base = row.guarantee_end_date;
  let startDate;
  if (base && base !== 'N/A') {
    startDate = new Date(String(base).replace(/-/g, '/'));
  } else {
    const pd = row.purchase_date;
    if (!pd || pd === 'N/A') return null;
    startDate = new Date(String(pd).replace(/-/g, '/'));
  }
  if (isNaN(startDate)) return null;
  startDate.setMonth(startDate.getMonth() + parseInt(ext.months));
  return startDate.toISOString().split('T')[0];
}

function getStatus(row) {
  const warningDays = (appSettings.warranty_expiration_warning_months || 3) * 30;
  const extEnd = calcExtWarrantyEndDate(row);
  const latestEnd = extEnd || row.guarantee_end_date;
  if (!latestEnd || latestEnd === 'N/A') return 'active';
  const d = new Date(String(latestEnd).replace(/-/g, '/'));
  if (isNaN(d)) return 'active';
  const diffDays = Math.floor((d - new Date()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0)           return 'expired';
  if (diffDays <= warningDays) return 'expiring';
  return 'active';
}

function buildRows() {
  const rmap = receiptMap();
  return (allData.items || []).map(it => {
    const r = rmap.get(it.receipt_group_id) || {};
    const row = {
      id:                  it.id,
      receipt_group_id:    it.receipt_group_id,
      brand:               it.brand    || '',
      model:               it.model    || '',
      location:            it.location || '',
      category:            it.category || '',
      users:               it.users    || [],
      project:             it.project  || '',
      shop:                r.shop          || '',
      purchase_date:       r.purchase_date || '',
      documentation:       r.documentation || '',
      guarantee_end_date:  it.guarantee_end_date || '',
      guarantee_duration:  it.guarantee_duration  || 0,
      guarantee_unit:      it.guarantee_unit      || 'months',
      extended_warranty:   it.extended_warranty   || null,
      price:               it.price != null ? it.price : null,
      file:                r.receipt_filename || it.receipt_relative_path || '',
      receipt_relative_path: r.receipt_relative_path || it.receipt_relative_path || ''
    };
    row.extended_warranty_end_date = calcExtWarrantyEndDate(row);
    return row;
  });
}

function formatExtWarranty(ew) {
  if (!ew) return '';
  const parts = [];
  if (ew.provider) parts.push(escHtml(ew.provider));
  if (ew.months)   parts.push(`${ew.months}mo`);
  if (ew.cost)     parts.push(formatPrice(ew.cost));
  return parts.join(' · ') || 'Yes';
}

function renderTable(rows) {
  const tbody = $('tableBody');
  if (!tbody) return;
  if (!rows || rows.length === 0) {
    tbody.innerHTML = `<tr class="empty-state"><td colspan="16"><div class="empty-message"><span class="empty-icon">📦</span><p>No items yet. Click "Add Receipt" to get started!</p></div></td></tr>`;
    if ($('itemCount')) $('itemCount').textContent = typeof t === 'function' ? t('itemCount', { count: 0 }) : '0 items';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const fileCell = r.receipt_relative_path
      ? `<a href="${API.fileUrl(r.receipt_relative_path)}" target="_blank" class="file-link" title="${escAttr(r.receipt_relative_path)}">${escHtml(r.file || r.receipt_relative_path)}</a>`
      : (r.file ? escHtml(r.file) : '');
    const status   = getStatus(r);
    const rowClass = status === 'expired' ? 'warranty-expired' : status === 'expiring' ? 'warranty-expiring' : '';
    return `
    <tr class="${rowClass}">
      <td data-column="id">${r.id ?? ''}</td>
      <td data-column="receipt_group_id">${escHtml(r.receipt_group_id ?? '')}</td>
      <td data-column="brand">${escHtml(r.brand ?? '')}</td>
      <td data-column="model">${escHtml(r.model ?? '')}</td>
      <td data-column="location">${escHtml(r.location ?? '')}</td>
      <td data-column="category">${escHtml(r.category ?? '')}</td>
      <td data-column="users">${escHtml(normalizeUsers(r.users).join('; '))}</td>
      <td data-column="project">${escHtml(r.project ?? '')}</td>
      <td data-column="shop">${escHtml(r.shop ?? '')}</td>
      <td data-column="purchase_date">${escHtml(r.purchase_date ?? '')}</td>
      <td data-column="documentation">${escHtml(r.documentation ?? '')}</td>
      <td data-column="guarantee_end_date">${escHtml(r.guarantee_end_date ?? '')}</td>
      <td data-column="extended_warranty">${formatExtWarranty(r.extended_warranty)}</td>
      <td data-column="price">${formatPrice(r.price)}</td>
      <td data-column="file">${fileCell}</td>
      <td data-column="actions">
        <button type="button" class="btn-small btn-edit"   data-id="${r.id}">Edit</button>
        <button type="button" class="btn-small btn-delete" data-id="${r.id}">Delete</button>
      </td>
    </tr>`;
  }).join('');
  if ($('itemCount')) $('itemCount').textContent = typeof t === 'function' ? t('itemCount', { count: rows.length }) : `${rows.length} items`;
  updateColumnVisibility();
  qsa('#tableBody .btn-edit').forEach(btn =>
    btn.addEventListener('click', () => editItem(parseInt(btn.dataset.id)))
  );
  qsa('#tableBody .btn-delete').forEach(btn =>
    btn.addEventListener('click', () => deleteItem(parseInt(btn.dataset.id)))
  );
}

function updateColumnVisibility() {
  qsa('th[data-column]').forEach(th => { th.style.display = visibleColumns.has(th.dataset.column) ? '' : 'none'; });
  qsa('#itemsTable td[data-column]').forEach(td => { td.style.display = visibleColumns.has(td.dataset.column) ? '' : 'none'; });
}

function updateSortIndicators() {
  qsa('th.sortable').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.column === currentSort.column)
      th.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
  });
}

function applyFilters(rows) {
  const q       = ($('searchInput')?.value  || '').trim().toLowerCase();
  const project = $('projectFilter')?.value || '';
  const status  = $('statusFilter')?.value  || '';
  const user    = $('userFilter')?.value    || '';
  return (rows || []).filter(r => {
    if (project && String(r.project || '') !== project)           return false;
    if (status  && getStatus(r) !== status)                       return false;
    if (user    && !normalizeUsers(r.users).includes(user))       return false;
    if (q) {
      const hay = [
        r.id, r.receipt_group_id, r.brand, r.model, r.location, r.category,
        r.project, r.shop, r.purchase_date, r.documentation, r.guarantee_end_date,
        normalizeUsers(r.users).join('; '), r.file, formatPrice(r.price)
      ].map(x => String(x || '').toLowerCase()).join(' | ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function sortRows(rows) {
  const col = currentSort.column;
  const dir = currentSort.direction === 'desc' ? -1 : 1;
  if (col === 'id')    return [...rows].sort((a, b) => ((a.id || 0) - (b.id || 0)) * dir);
  if (col === 'price') return [...rows].sort((a, b) => ((parseFloat(a.price) || 0) - (parseFloat(b.price) || 0)) * dir);
  return [...rows].sort((a, b) => String(a?.[col] ?? '').localeCompare(String(b?.[col] ?? '')) * dir);
}

function filterAndRender() {
  renderTable(sortRows(applyFilters(buildRows())));
}

// ===================== IMPORT / EXPORT =====================
async function handleImport(e) {
  const f = e?.target?.files?.[0]; if (!f) return;
  try {
    const payload = JSON.parse(await f.text());
    await fetchJson(API.importJson, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    await loadData(); await loadSuggestions();
    alert('Imported successfully.');
  } catch (err) { console.error('Import failed:', err); alert('Import failed (see Console).'); }
  finally { e.target.value = ''; }
}

async function recheckIntegrity() {
  try { await fetchJson(API.integrityCheck, { method: 'POST' }); await loadData(); }
  catch (err) { console.error('Integrity check failed:', err); await loadData(); }
}

// ===================== FILE HANDLING =====================
async function handleFile(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const resp = await fetch(API.upload, { method: 'POST', body: formData });
    if (!resp.ok) { alert(`Upload failed: ${await resp.text()}`); return; }
    const result = await resp.json();
    if (!result.success) { alert(`Upload failed: ${result.error || 'Unknown error'}`); return; }
    openModalForNew(result);
  } catch (err) { console.error('Upload error:', err); alert(`Upload failed: ${err.message}`); }
  finally { const fi = $('modalFileInput'); if (fi) fi.value = ''; }
}

// ===================== MODAL — OPEN / CLOSE =====================
function openModalForChoose() {
  const modal = $('ocrModal'); if (!modal) return;
  sessionGroupId = null;
  sessionItemIds = [];
  clearFormItemFields();
  populateExistingReceiptSelect();
  $('modalItemId').value = '';
  $('modalReceiptGroupId').value = '';
  const sel = $('existingReceiptSelect'); if (sel) sel.value = '';
  setModalMode('choose');
  modal.style.display = 'flex';
}

function openModalForNew(uploadResult) {
  const modal = $('ocrModal'); if (!modal) return;
  sessionGroupId = uploadResult.receipt_group_id;
  sessionItemIds = [uploadResult.item_id];

  $('modalItemId').value         = uploadResult.item_id || '';
  $('modalReceiptGroupId').value = uploadResult.receipt_group_id || '';
  $('modalMode').value           = 'new';

  const ocr = uploadResult.ocr_data || {};
  $('modalShop').value = ocr.shop || '';
  const pd = ocr.purchase_date || '';
  if (pd && pd !== 'N/A') {
    try { $('modalPurchaseDate').value = new Date(pd.replace(/-/g, ' ')).toISOString().split('T')[0]; }
    catch { $('modalPurchaseDate').value = ''; }
  } else { $('modalPurchaseDate').value = ''; }

  clearFormItemFields();

  const itemsPreview = $('modalItemsPreview');
  const itemsList    = $('modalItemsList');
  if (ocr.items?.length > 0) {
    itemsList.innerHTML = ocr.items.map(i => `<li>${escHtml(i.name)} — ${escHtml(i.price)}</li>`).join('');
    itemsPreview.style.display = 'block';
  } else { itemsPreview.style.display = 'none'; }

  setModalMode('new');
  modal.style.display = 'flex';
}

function setModalMode(mode) {
  const btnAdd    = $('btnAddAnother');
  const btnFinish = $('btnFinish');
  const uploadSec = qs('.upload-select-section');
  const form      = $('ocrForm');
  if (mode === 'choose') {
    // Show upload/existing-receipt chooser; hide form and action buttons until a receipt is chosen
    if (uploadSec) uploadSec.style.display = '';
    if (form)      form.style.display = 'none';
    if (btnAdd)    btnAdd.style.display = 'none';
    if (btnFinish) btnFinish.style.display = 'none';
  } else if (mode === 'new') {
    if (uploadSec) uploadSec.style.display = 'none';
    if (form)      form.style.display = '';
    if (btnAdd)    { btnAdd.style.display = ''; }
    if (btnFinish) { btnFinish.style.display = ''; btnFinish.textContent = 'Finish'; btnFinish.classList.remove('btn-primary'); btnFinish.classList.add('btn-success'); }
  } else {
    if (uploadSec) uploadSec.style.display = 'none';
    if (form)      form.style.display = '';
    if (btnAdd)    { btnAdd.style.display = 'none'; }
    if (btnFinish) { btnFinish.style.display = ''; btnFinish.textContent = 'Save'; btnFinish.classList.remove('btn-success'); btnFinish.classList.add('btn-primary'); }
  }
}

function clearFormItemFields() {
  ['modalBrand','modalModel','modalLocation','modalCategory','modalProject',
   'modalDocumentation','modalWarranty','extWarrantyProvider','extWarrantyMonths',
   'extWarrantyCost','modalPrice'
  ].forEach(id => { const el = $(id); if (el) el.value = ''; });
  const ewCb = $('extendedWarrantyCheckbox');
  if (ewCb) ewCb.checked = false;
  const ewFields = $('extendedWarrantyFields');
  if (ewFields) ewFields.classList.add('hidden');
  // Reset ext warranty doc fields
  const docPath = $('extWarrantyDocPath'); if (docPath) docPath.value = '';
  const docName = $('extWarrantyDocName'); if (docName) docName.textContent = '';
  const docLink = $('extWarrantyDocLink'); if (docLink) { docLink.href = '#'; docLink.classList.add('hidden'); }
  clearUserTags();
}

function closeOcrModal() {
  const modal = $('ocrModal');
  if (modal) { modal.style.display = 'none'; $('ocrForm')?.reset(); }
  clearUserTags();
  sessionGroupId = null;
  sessionItemIds = [];
  // Restore visibility for next open
  const uploadSec = qs('.upload-select-section');
  if (uploadSec) uploadSec.style.display = '';
  const form = $('ocrForm');
  if (form) form.style.display = '';
}

// ===================== FORM DATA =====================
function collectFormData() {
  const shop          = ($('modalShop')?.value          || '').trim();
  const purchaseDate  = $('modalPurchaseDate')?.value   || '';
  const brand         = ($('modalBrand')?.value         || '').trim() || 'N/A';
  const model         = ($('modalModel')?.value         || '').trim() || 'N/A';
  const location      = ($('modalLocation')?.value      || '').trim() || 'N/A';
  const category      = ($('modalCategory')?.value      || '').trim();
  const project       = ($('modalProject')?.value       || '').trim() || 'N/A';
  const documentation = ($('modalDocumentation')?.value || '').trim() || 'N/A';
  const warrantyMonths = parseInt($('modalWarranty')?.value) || 0;
  const priceRaw      = ($('modalPrice')?.value || '').trim();
  const price         = priceRaw ? parseFloat(priceRaw) : null;

  const ewChecked = $('extendedWarrantyCheckbox')?.checked || false;
  const extWarranty = ewChecked ? {
    provider:      ($('extWarrantyProvider')?.value || '').trim(),
    months:        parseInt($('extWarrantyMonths')?.value) || 0,
    cost:          parseFloat($('extWarrantyCost')?.value) || null,
    document_path: ($('extWarrantyDocPath')?.value || '') || null
  } : null;

  let formattedDate = purchaseDate;
  if (purchaseDate) {
    try {
      const d = new Date(purchaseDate + 'T00:00:00');
      const mn = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      formattedDate = `${d.getFullYear()}-${mn[d.getMonth()]}-${String(d.getDate()).padStart(2,'0')}`;
    } catch { /* keep original */ }
  }

  return {
    shop, purchase_date: formattedDate, brand, model, location, category,
    project, documentation, guarantee_duration: warrantyMonths, guarantee_unit: 'months',
    price, extended_warranty: extWarranty, users: [...userTagsArray]
  };
}

function validateForm() {
  const shop  = ($('modalShop')?.value  || '').trim();
  const pd    = $('modalPurchaseDate')?.value || '';
  const brand = ($('modalBrand')?.value || '').trim();
  const model = ($('modalModel')?.value || '').trim();
  if (!shop)  { alert('Shop/Store is required.');    return false; }
  if (!pd)    { alert('Purchase Date is required.'); return false; }
  if (!brand) { alert('Brand is required.');         return false; }
  if (!model) { alert('Model is required.');         return false; }
  // RM-122: purchase date must not be in the future and not more than 100 years ago
  const pdDate  = new Date(pd);
  const today   = new Date(); today.setHours(0, 0, 0, 0);
  const minDate = new Date(today); minDate.setFullYear(minDate.getFullYear() - 100);
  if (pdDate > today)   { alert('Purchase date cannot be in the future.');               return false; }
  if (pdDate < minDate) { alert('Purchase date cannot be more than 100 years in the past.'); return false; }
  // RM-122: Price format
  const priceRaw = ($('modalPrice')?.value || '').trim();
  if (priceRaw && isNaN(parseFloat(priceRaw))) { alert('Price must be a valid number.'); return false; }
  return true;
}

// ===================== MODAL ACTIONS =====================
async function handleAddAnother() {
  if (!validateForm()) return;
  const btn = $('btnAddAnother');
  if (btn) btn.disabled = true;
  try {
    const itemId   = parseInt($('modalItemId').value);
    const formData = collectFormData();

    const resp = await fetchJson(API.updateItem(itemId), {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData)
    });
    if (!resp.success) { alert(`Save failed: ${resp.error || 'Unknown error'}`); return; }

    // Create new placeholder item in the same group
    const createResp = await fetchJson(API.createItem, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ receipt_group_id: sessionGroupId })
    });
    if (!createResp.success) { alert(`Failed to create next item: ${createResp.error}`); return; }

    const newItemId = createResp.item.id;
    sessionItemIds.push(newItemId);
    $('modalItemId').value = newItemId;

    // Keep shop and date, clear item-specific fields
    const keepShop = $('modalShop').value;
    const keepDate = $('modalPurchaseDate').value;
    clearFormItemFields();
    $('modalShop').value         = keepShop;
    $('modalPurchaseDate').value = keepDate;
    $('modalItemsPreview').style.display = 'none';

    const brandInput = $('modalBrand');
    if (brandInput) brandInput.focus();
    await loadSuggestions();
  } catch (err) { console.error('Add Another error:', err); alert(`Error: ${err.message}`); }
  finally { if (btn) btn.disabled = false; }
}

async function handleFinish(e) {
  e.preventDefault();
  if (!validateForm()) return;
  const itemId   = parseInt($('modalItemId').value);
  const formData = collectFormData();
  try {
    const resp = await fetchJson(API.updateItem(itemId), {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData)
    });
    if (!resp.success) { alert(`Save failed: ${resp.error || 'Unknown error'}`); return; }
    closeOcrModal();
    await loadData(); await loadSuggestions();
  } catch (err) { console.error('Save error:', err); alert(`Save failed: ${err.message}`); }
}

async function handleCancelModal() {
  if (sessionItemIds.length > 0) {
    const confirmed = confirm('Are you sure you want to cancel? Unsaved changes will be lost.');
    if (!confirmed) return;
    // Only delete items that were created as placeholders for a NEW receipt upload
    // (not for existing-receipt mode, where the file belongs to an existing group)
    const mode = $('modalMode')?.value;
    if (mode === 'new' && sessionGroupId) {
      // Check if this group existed before this session (existing-receipt) or was just uploaded
      const existedBefore = (allData.receipts || []).some(r => r.receipt_group_id === sessionGroupId);
      if (!existedBefore) {
        for (const id of sessionItemIds) {
          try { await fetchJson(API.deleteItem(id), { method: 'DELETE' }); }
          catch (err) { console.error('Error deleting session item:', err); }
        }
        await loadData();
      }
    }
  }
  closeOcrModal();
}

// Existing receipt flow (RM-123): selecting an existing receipt creates a new item in that group
async function handleExistingReceiptSelect(e) {
  const groupId = e.target.value;
  if (!groupId) return;
  try {
    const createResp = await fetchJson(API.createItem, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ receipt_group_id: groupId })
    });
    if (!createResp.success) { alert(`Failed to start item: ${createResp.error}`); return; }
    const receipt = (allData.receipts || []).find(r => r.receipt_group_id === groupId) || {};
    sessionGroupId = groupId;
    sessionItemIds = [createResp.item.id];
    $('modalItemId').value         = createResp.item.id;
    $('modalReceiptGroupId').value = groupId;
    $('modalMode').value           = 'new';
    $('modalShop').value = receipt.shop !== 'N/A' ? (receipt.shop || '') : '';
    const pd = receipt.purchase_date || '';
    if (pd && pd !== 'N/A') {
      try { $('modalPurchaseDate').value = new Date(pd.replace(/-/g, ' ')).toISOString().split('T')[0]; }
      catch { $('modalPurchaseDate').value = ''; }
    }
    clearFormItemFields();
    setModalMode('new');
    $('modalItemsPreview').style.display = 'none';
  } catch (err) { console.error('Existing receipt error:', err); alert(`Error: ${err.message}`); }
}

// Form submit handler proxy
async function saveOcrData(e) { return handleFinish(e); }

// ===================== EDIT ITEM =====================
async function editItem(itemId) {
  const item    = allData.items.find(i => i.id === itemId);
  if (!item) { alert('Item not found'); return; }
  const receipt = allData.receipts.find(r => r.receipt_group_id === item.receipt_group_id);
  if (!receipt) { alert('Receipt not found'); return; }

  $('modalItemId').value         = item.id;
  $('modalReceiptGroupId').value = item.receipt_group_id;
  $('modalMode').value           = 'edit';

  $('modalShop').value          = receipt.shop          !== 'N/A' ? receipt.shop          : '';
  $('modalBrand').value         = item.brand            !== 'N/A' ? item.brand            : '';
  $('modalModel').value         = item.model            !== 'N/A' ? item.model            : '';
  $('modalLocation').value      = item.location         !== 'N/A' ? item.location         : '';
  $('modalCategory').value      = item.category         || '';
  $('modalProject').value       = item.project          !== 'N/A' ? item.project          : '';
  $('modalDocumentation').value = receipt.documentation !== 'N/A' ? receipt.documentation : '';
  $('modalWarranty').value      = item.guarantee_duration || '';
  $('modalPrice').value         = item.price != null ? item.price : '';

  const pd = receipt.purchase_date || '';
  if (pd && pd !== 'N/A') {
    try { $('modalPurchaseDate').value = new Date(pd.replace(/-/g, ' ')).toISOString().split('T')[0]; }
    catch { $('modalPurchaseDate').value = ''; }
  } else { $('modalPurchaseDate').value = ''; }

  setUserTags(item.users || []);

  const ew   = item.extended_warranty;
  const ewCb = $('extendedWarrantyCheckbox');
  if (ewCb) {
    ewCb.checked = !!(ew && (ew.provider || ew.months));
    const ewFields = $('extendedWarrantyFields');
    if (ewFields) ewFields.classList.toggle('hidden', !ewCb.checked);
  }
  if ($('extWarrantyProvider')) $('extWarrantyProvider').value = ew?.provider || '';
  if ($('extWarrantyMonths'))   $('extWarrantyMonths').value   = ew?.months   || '';
  if ($('extWarrantyCost'))     $('extWarrantyCost').value     = ew?.cost     || '';
  const ewDocPath = ew?.document_path || '';
  const dpEl = $('extWarrantyDocPath'); if (dpEl) dpEl.value = ewDocPath;
  const dnEl = $('extWarrantyDocName');
  const dlEl = $('extWarrantyDocLink');
  if (ewDocPath) {
    if (dnEl) dnEl.textContent = ewDocPath.split('/').pop();
    if (dlEl) { dlEl.href = API.fileUrl(ewDocPath); dlEl.classList.remove('hidden'); }
  } else {
    if (dnEl) dnEl.textContent = '';
    if (dlEl) { dlEl.href = '#'; dlEl.classList.add('hidden'); }
  }

  $('modalItemsPreview').style.display = 'none';
  sessionGroupId = null;
  sessionItemIds = [];
  setModalMode('edit');
  const modal = $('ocrModal');
  if (modal) modal.style.display = 'flex';
}

// ===================== DELETE ITEM =====================
async function deleteItem(itemId) {
  const item         = allData.items.find(i => i.id === itemId);
  if (!item) { alert('Item not found'); return; }
  const itemsInGroup = allData.items.filter(i => i.receipt_group_id === item.receipt_group_id);
  const receipt      = allData.receipts.find(r => r.receipt_group_id === item.receipt_group_id);
  const hasFile      = !!(receipt && receipt.receipt_relative_path);

  let msg;
  if (itemsInGroup.length === 1) {
    msg = hasFile
      ? `⚠️ PERMANENT DELETE\n\nYou are about to delete:\n  • Record: ID ${itemId} (${item.brand||'N/A'} ${item.model||'N/A'})\n  • File: ${receipt.receipt_filename||receipt.receipt_relative_path}\n\nThe receipt FILE WILL BE DELETED from disk.\nThis action cannot be undone.\n\nContinue?`
      : `⚠️ PERMANENT DELETE\n\nYou are about to delete record ID ${itemId}.\nNo file is associated with this record.\n\nContinue?`;
  } else {
    msg = `⚠️ DELETE RECORD\n\nYou are about to delete record ID ${itemId}.\n\nℹ️ The receipt file will NOT be deleted — it is shared with ${itemsInGroup.length - 1} other item(s) in group ${item.receipt_group_id}.\n\nContinue?`;
  }
  if (!confirm(msg)) return;
  try {
    const resp = await fetchJson(API.deleteItem(itemId), { method: 'DELETE' });
    if (!resp.success) { alert(`Delete failed: ${resp.error || 'Unknown error'}`); return; }
    await loadData(); await loadSuggestions();
  } catch (err) { console.error('Delete error:', err); alert(`Delete failed: ${err.message}`); }
}

// ===================== SETTINGS =====================
async function saveSettings() {
  const currency     = $('currencySelect')?.value     || 'EUR';
  const format       = $('currencyFormatSelect')?.value || 'symbol';
  const warningMonths = parseInt($('warrantyWarningInput')?.value) || 3;
  try {
    appSettings = await fetchJson(API.settings, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ currency, currency_display_format: format, warranty_expiration_warning_months: warningMonths })
    });
    filterAndRender();
    alert('Settings saved.');
  } catch (err) { console.error('Settings save error:', err); alert(`Failed to save settings: ${err.message}`); }
}

// ===================== EVENT LISTENERS =====================
function setupEventListeners() {
  // "Add Receipt" button → open modal in choose mode (upload OR existing receipt)
  bind('addReceiptBtn', 'click', openModalForChoose);

  // Modal file input
  const modalFileInput = $('modalFileInput');
  if (modalFileInput) {
    modalFileInput.addEventListener('change', e => { const f = e.target.files?.[0]; if (f) handleFile(f); });
  }

  // Modal drop zone (inside modal)
  const modalDropZone = $('modalDropZone');
  if (modalDropZone) {
    const browseLink = modalDropZone.querySelector('.browse-link');
    if (browseLink) browseLink.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); modalFileInput?.click(); });
    modalDropZone.addEventListener('click', e => { if (!e.target.classList.contains('browse-link')) modalFileInput?.click(); });
    modalDropZone.addEventListener('dragover',  e => { e.preventDefault(); modalDropZone.classList.add('drag-over'); });
    modalDropZone.addEventListener('dragleave', () => modalDropZone.classList.remove('drag-over'));
    modalDropZone.addEventListener('drop', e => {
      e.preventDefault(); modalDropZone.classList.remove('drag-over');
      const f = e.dataTransfer?.files?.[0]; if (f) handleFile(f);
    });
  }

  // Existing receipt dropdown (RM-123)
  bind('existingReceiptSelect', 'change', handleExistingReceiptSelect);

  // Toolbar
  bind('searchInput',   'input',  filterAndRender);
  bind('projectFilter', 'change', filterAndRender);
  bind('statusFilter',  'change', filterAndRender);
  bind('userFilter',    'change', filterAndRender);
  bind('refreshBtn',    'click',  () => { loadData(); loadSuggestions(); });

  // Column toggle
  bind('columnToggleBtn',  'click', () => { const p = $('columnPanel'); if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none'; });
  bind('closeColumnPanel', 'click', () => { const p = $('columnPanel'); if (p) p.style.display = 'none'; });

  // Integrity banner
  bind('recheckBtn',     'click', recheckIntegrity);
  bind('closeBannerBtn', 'click', () => { const b = $('integrityBanner'); if (b) b.style.display = 'none'; });

  // OCR modal buttons
  bind('closeModal',    'click',  handleCancelModal);
  bind('cancelModal',   'click',  handleCancelModal);
  bind('btnAddAnother', 'click',  handleAddAnother);
  bind('ocrForm',       'submit', saveOcrData);

  // Close modal on backdrop click
  const modal = $('ocrModal');
  if (modal) modal.addEventListener('click', e => { if (e.target === modal) handleCancelModal(); });

  // Extended warranty toggle
  bind('extendedWarrantyCheckbox', 'change', e => {
    const fields = $('extendedWarrantyFields');
    if (fields) fields.classList.toggle('hidden', !e.target.checked);
  });

  // RM-77: ext warranty document upload
  bind('extWarrantyDocBtn', 'click', () => $('extWarrantyDocInput')?.click());
  const ewDocInput = $('extWarrantyDocInput');
  if (ewDocInput) {
    ewDocInput.addEventListener('change', async e => {
      const file = e.target.files?.[0];
      if (!file) return;
      const nameEl = $('extWarrantyDocName');
      const linkEl = $('extWarrantyDocLink');
      const pathEl = $('extWarrantyDocPath');
      if (nameEl) nameEl.textContent = 'Uploading…';
      try {
        const fd = new FormData(); fd.append('file', file);
        const resp = await fetch(API.uploadDoc, { method: 'POST', body: fd });
        const result = await resp.json();
        if (result.success) {
          if (pathEl) pathEl.value = result.path;
          if (nameEl) nameEl.textContent = file.name;
          if (linkEl) { linkEl.href = API.fileUrl(result.path); linkEl.classList.remove('hidden'); }
        } else {
          if (nameEl) nameEl.textContent = 'Upload failed.';
          console.error('Doc upload error:', result.error);
        }
      } catch (err) {
        if (nameEl) nameEl.textContent = 'Upload failed.';
        console.error('Doc upload error:', err);
      }
      ewDocInput.value = '';
    });
  }

  // User tag input
  const tagInput = $('userTagInput');
  if (tagInput) {
    tagInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addUserTag(tagInput.value);
        tagInput.value = '';
      }
    });
    tagInput.addEventListener('blur', () => {
      if (tagInput.value.trim()) { addUserTag(tagInput.value); tagInput.value = ''; }
    });
  }

  // Settings
  bind('saveSettingsBtn', 'click', saveSettings);
  bind('menuBackupBtn',   'click', exportJson);
  bind('menuExportBtn',   'click', exportCsv);
  bind('menuRestoreBtn',  'click', () => $('importInput')?.click());
  bind('importInput',     'change', handleImport);

  // Column visibility toggles
  qsa('.col-toggle').forEach(t => t.addEventListener('change', e => {
    const col = e.target.dataset.column; if (!col) return;
    if (e.target.checked) visibleColumns.add(col); else visibleColumns.delete(col);
    updateColumnVisibility();
  }));

  // Sortable headers
  qsa('th.sortable').forEach(th => th.addEventListener('click', () => {
    const col = th.dataset.column; if (!col) return;
    if (currentSort.column === col) currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    else { currentSort.column = col; currentSort.direction = 'asc'; }
    updateSortIndicators(); filterAndRender();
  }));
}

// ===================== INIT =====================
document.addEventListener('DOMContentLoaded', () => {
  // RM-122: set purchase date constraints dynamically
  const pdInput = $('modalPurchaseDate');
  if (pdInput) {
    const today   = new Date();
    const minDate = new Date(today); minDate.setFullYear(minDate.getFullYear() - 100);
    pdInput.max = today.toISOString().split('T')[0];
    pdInput.min = minDate.toISOString().split('T')[0];
  }
  loadSettings();
  loadData();
  loadSuggestions();
  setupEventListeners();
});
