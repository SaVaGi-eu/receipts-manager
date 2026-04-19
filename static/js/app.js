// ===================== GLOBAL STATE =====================
let allData    = { receipts: [], items: [], next_id: 1, integrity_issues: [] };
let suggestions = { shops: [], brands: [], models: [], locations: [], documentation: [], projects: [], users: [], categories: [] };
let appSettings = { currency: 'EUR', currency_display_format: 'symbol', warranty_expiration_warning_months: 3, date_format: 'DD-MMM-YYYY' };
let currentSort  = { column: 'id', direction: 'asc' };
let visibleColumns = new Set([
  'id', 'receipt_group_id', 'brand', 'model', 'location', 'category', 'users',
  'project', 'shop', 'purchase_date', 'documentation', 'guarantee_end_date',
  'extended_warranty', 'price', 'file', 'actions'
]);
let userTagsArray = [];
let sessionGroupId  = null;
let sessionItemIds  = [];
let chooseColOrder  = ['group_id', 'shop', 'date'];
let invoiceRows     = [];
let nextRowId       = 0;
let activeFilters   = {};
let filterPanelField = 'shop';

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

const FILTER_FIELDS = [
  { key: 'shop',          labelKey: 'colShop',          type: 'checkbox', search: true  },
  { key: 'brand',         labelKey: 'colBrand',         type: 'checkbox', search: true  },
  { key: 'category',      labelKey: 'colCategory',      type: 'checkbox', search: false },
  { key: 'documentation', labelKey: 'colDocumentation', type: 'checkbox', search: false },
  { key: 'location',      labelKey: 'colLocation',      type: 'checkbox', search: true  },
  { key: 'purchase_date', labelKey: 'colPurchaseDate',  type: 'daterange'               },
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
function cell(text)  {
  const s = String(text ?? '');
  return `<span class="cell-truncate" title="${escAttr(s)}">${escHtml(s)}</span>`;
}

// RM-188: Format a stored YYYY-MMM-DD date string into the user's preferred display format
function formatDate(dateStr) {
  if (!dateStr || dateStr === 'N/A') return dateStr || '';
  const MONTHS = { Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11 };
  const m = /^(\d{4})-([A-Za-z]{3})-(\d{2})$/.exec(dateStr);
  if (!m) return dateStr;
  const year = m[1], mon = m[2], day = m[3];
  const mm = String(MONTHS[mon] + 1).padStart(2, '0');
  switch (appSettings.date_format || 'DD-MMM-YYYY') {
    case 'DD/MM/YYYY':  return `${day}/${mm}/${year}`;
    case 'MM/DD/YYYY':  return `${mm}/${day}/${year}`;
    case 'YYYY-MM-DD':  return `${year}-${mm}-${day}`;
    default:            return `${day}-${mon}-${year}`;  // DD-MMM-YYYY
  }
}

function parseDateToISO(dateStr) {
  if (!dateStr || dateStr === 'N/A') return '';
  const MONTHS = { Jan:'01',Feb:'02',Mar:'03',Apr:'04',May:'05',Jun:'06',Jul:'07',Aug:'08',Sep:'09',Oct:'10',Nov:'11',Dec:'12' };
  const m = /^(\d{4})-([A-Za-z]{3})-(\d{2})$/.exec(dateStr);
  if (!m) return dateStr;
  return `${m[1]}-${MONTHS[m[2]] || '00'}-${m[3]}`;
}

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
  const dateFmtSel = $('dateFormatSelect');
  if (dateFmtSel) dateFmtSel.value = appSettings.date_format || 'DD-MMM-YYYY';
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
  const sortBy = $('existingReceiptSort')?.value || 'group_id';
  const receipts = [...(allData.receipts || [])].sort((a, b) => {
    if (sortBy === 'shop') return String(a.shop || '').localeCompare(String(b.shop || ''));
    if (sortBy === 'date') return String(b.purchase_date || '').localeCompare(String(a.purchase_date || ''));
    return String(a.receipt_group_id || '').localeCompare(String(b.receipt_group_id || ''));
  });
  sel.innerHTML = `<option value="">${t('selectReceiptOption') || '-- Choose existing receipt --'}</option>` +
    receipts.map(r => {
      const colValues = { group_id: r.receipt_group_id, shop: r.shop, date: formatDate(r.purchase_date) };
      const label = chooseColOrder.map(k => colValues[k]).filter(Boolean).join(' · ');
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
      quantity:            it.quantity || 1,
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

function updateItemCount(count) {
  const el = $('itemCount');
  if (!el) return;
  el.textContent = typeof t === 'function' && typeof i18next !== 'undefined' && i18next.isInitialized
    ? t('itemCount', { count })
    : `${count} items`;
}

function renderTable(rows) {
  const tbody = $('tableBody');
  if (!tbody) return;
  if (!rows || rows.length === 0) {
    tbody.innerHTML = `<tr class="empty-state"><td colspan="16"><div class="empty-message"><span class="empty-icon">📦</span><p>No items yet. Click "Add Receipt" to get started!</p></div></td></tr>`;
    updateItemCount(0);
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const filePath = r.receipt_relative_path || '';
    const fileCell = filePath
      ? `<span class="cell-truncate"><a href="${API.fileUrl(filePath)}" target="_blank" class="file-link" title="${escAttr(filePath)}">${escHtml(r.file || filePath)}</a></span>`
      : (r.file ? cell(r.file) : '');
    const openBtn = filePath
      ? `<button type="button" class="btn-small btn-open" data-id="${r.id}" data-path="${escAttr(filePath)}" data-i18n="open">Open</button>`
      : '';
    const status   = getStatus(r);
    const rowClass = status === 'expired' ? 'warranty-expired' : status === 'expiring' ? 'warranty-expiring' : '';
    return `
    <tr class="${rowClass}">
      <td data-column="id">${r.id ?? ''}</td>
      <td data-column="receipt_group_id">${cell(r.receipt_group_id)}</td>
      <td data-column="brand">${cell(r.brand)}</td>
      <td data-column="model">${cell(r.model)}</td>
      <td data-column="location">${cell(r.location)}</td>
      <td data-column="category">${cell(r.category)}</td>
      <td data-column="users">${cell(normalizeUsers(r.users).join('; '))}</td>
      <td data-column="project">${cell(r.project)}</td>
      <td data-column="shop">${cell(r.shop)}</td>
      <td data-column="purchase_date">${cell(formatDate(r.purchase_date))}</td>
      <td data-column="documentation">${cell(r.documentation)}</td>
      <td data-column="guarantee_end_date">${cell(formatDate(r.guarantee_end_date))}</td>
      <td data-column="extended_warranty">${cell(formatExtWarranty(r.extended_warranty))}</td>
      <td data-column="price">${r.quantity > 1
        ? `<span class="cell-truncate" title="Unit: ${escAttr(formatPrice(r.price))} × ${r.quantity}">${escHtml(formatPrice(r.price != null ? r.price * r.quantity : null))}</span>`
        : formatPrice(r.price)}</td>
      <td data-column="file">${fileCell}</td>
      <td data-column="actions">
        ${openBtn}
        <button type="button" class="btn-small btn-edit"   data-id="${r.id}">Edit</button>
        <button type="button" class="btn-small btn-delete" data-id="${r.id}">Delete</button>
      </td>
    </tr>`;
  }).join('');
  updateItemCount(rows.length);
  updateColumnVisibility();
  qsa('#tableBody .btn-open').forEach(btn =>
    btn.addEventListener('click', () => window.open(API.fileUrl(btn.dataset.path), '_blank'))
  );
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
    // RM-193: panel filters
    for (const f of FILTER_FIELDS) {
      if (f.type === 'daterange') {
        const range = activeFilters.purchase_date;
        if (range?.from || range?.to) {
          const iso = parseDateToISO(r.purchase_date);
          if (range.from && iso < range.from) return false;
          if (range.to   && iso > range.to)   return false;
        }
      } else {
        const vals = activeFilters[f.key];
        if (vals instanceof Set && vals.size > 0) {
          if (!vals.has(String(r[f.key] || '').trim())) return false;
        }
      }
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
  syncChooseColSelects();
  populateExistingReceiptSelect();
  $('modalItemId').value = '';
  $('modalReceiptGroupId').value = '';
  const sel = $('existingReceiptSelect'); if (sel) sel.value = '';
  // Hide the col order panel when opening fresh
  const panel = $('chooseColOrderPanel'); if (panel) panel.style.display = 'none';
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
  setModalMode('new');
  modal.style.display = 'flex';
}

function setModalMode(mode) {
  const btnFinish = $('btnFinish');
  const addRowBtn = $('addRowBtn');
  const uploadSec = qs('.upload-select-section');
  const form      = $('ocrForm');
  if (mode === 'choose') {
    if (uploadSec) uploadSec.style.display = '';
    if (form)      form.style.display = 'none';
    if (btnFinish) btnFinish.style.display = 'none';
    if (addRowBtn) addRowBtn.style.display = 'none';
  } else if (mode === 'new') {
    if (uploadSec) uploadSec.style.display = 'none';
    if (form)      form.style.display = '';
    if (addRowBtn) addRowBtn.style.display = '';
    if (btnFinish) { btnFinish.style.display = ''; btnFinish.textContent = t('saveAll') || 'Save All'; btnFinish.classList.remove('btn-primary'); btnFinish.classList.add('btn-success'); }
    const titleEl = $('modalTitle'); if (titleEl) titleEl.textContent = '📦 Add New Item';
  } else {
    if (uploadSec) uploadSec.style.display = 'none';
    if (form)      form.style.display = '';
    if (addRowBtn) addRowBtn.style.display = '';
    if (btnFinish) { btnFinish.style.display = ''; btnFinish.textContent = t('saveAll') || 'Save'; btnFinish.classList.remove('btn-success'); btnFinish.classList.add('btn-primary'); }
    const titleEl = $('modalTitle'); if (titleEl) titleEl.textContent = '✏️ Edit Item';
  }
}

function clearFormItemFields() {
  // Reset invoice table to one blank row
  invoiceRows = []; nextRowId = 0;
  addInvoiceRow({});
  // Reset extended warranty
  ['extWarrantyProvider','extWarrantyMonths','extWarrantyCost'].forEach(id => { const el = $(id); if (el) el.value = ''; });
  const ewCb = $('extendedWarrantyCheckbox');
  if (ewCb) ewCb.checked = false;
  const ewFields = $('extendedWarrantyFields');
  if (ewFields) ewFields.classList.add('hidden');
  const docPath = $('extWarrantyDocPath'); if (docPath) docPath.value = '';
  const docName = $('extWarrantyDocName'); if (docName) docName.textContent = '';
  const docLink = $('extWarrantyDocLink'); if (docLink) { docLink.href = '#'; docLink.classList.add('hidden'); }
}

function closeOcrModal() {
  const modal = $('ocrModal');
  if (modal) { modal.style.display = 'none'; $('ocrForm')?.reset(); }
  invoiceRows = []; nextRowId = 0;
  sessionGroupId = null;
  sessionItemIds = [];
  const uploadSec = qs('.upload-select-section');
  if (uploadSec) uploadSec.style.display = '';
  const form = $('ocrForm');
  if (form) form.style.display = '';
}

// ===================== INVOICE TABLE (RM-187) =====================
function syncInvoiceRowsFromDOM() {
  qsa('#invoiceTableBody tr[data-row-id]').forEach(tr => {
    const row = invoiceRows.find(r => r.id === parseInt(tr.dataset.rowId));
    if (!row) return;
    row.brand    = tr.querySelector('[data-field="brand"]')?.value    || '';
    row.model    = tr.querySelector('[data-field="model"]')?.value    || '';
    row.location = tr.querySelector('[data-field="location"]')?.value || '';
    row.category = tr.querySelector('[data-field="category"]')?.value || '';
    row.project  = tr.querySelector('[data-field="project"]')?.value  || '';
    row.price    = tr.querySelector('[data-field="price"]')?.value    || '';
    row.qty      = Math.max(1, parseInt(tr.querySelector('[data-field="qty"]')?.value) || 1);
  });
}

function renderInvoiceTable() {
  const tbody = $('invoiceTableBody');
  if (!tbody) return;
  const canDel = invoiceRows.length > 1;
  tbody.innerHTML = invoiceRows.map(row => {
    const chips = row.users.map(u =>
      `<span class="row-user-chip">${escHtml(u)}<button type="button" class="row-chip-remove" data-user="${escAttr(u)}">&times;</button></span>`
    ).join('');
    const p = parseFloat(row.price);
    const lineTotal = (!isNaN(p) && p >= 0) ? formatPrice(p * row.qty) : '—';
    return `<tr data-row-id="${row.id}">
      <td><input class="row-input"            data-field="brand"    value="${escAttr(row.brand)}"    list="brandList"    maxlength="100" placeholder="Brand *"></td>
      <td><input class="row-input"            data-field="model"    value="${escAttr(row.model)}"    list="modelList"    maxlength="100" placeholder="Model *"></td>
      <td><input class="row-input"            data-field="location" value="${escAttr(row.location)}" list="locationList" maxlength="100"></td>
      <td><input class="row-input"            data-field="category" value="${escAttr(row.category)}" list="categoryList" maxlength="50"></td>
      <td><input class="row-input"            data-field="project"  value="${escAttr(row.project)}"  list="projectList"  maxlength="100"></td>
      <td><div class="row-users">${chips}<input type="text" class="row-user-input" list="userList" placeholder="+"></div></td>
      <td><input class="row-input row-price-input" type="text"   data-field="price" value="${escAttr(row.price)}" inputmode="decimal" placeholder="0.00" maxlength="10"></td>
      <td><input class="row-input row-qty-input"   type="number" data-field="qty"   value="${row.qty}" min="1" max="9999" step="1"></td>
      <td class="row-line-total">${lineTotal}</td>
      <td><button type="button" class="row-del-btn" data-row-id="${row.id}"${canDel ? '' : ' disabled'}>🗑️</button></td>
    </tr>`;
  }).join('');
  updateReceiptTotal();
}

function updateRowLineTotal(tr) {
  const p   = parseFloat(tr.querySelector('[data-field="price"]')?.value);
  const qty = Math.max(1, parseInt(tr.querySelector('[data-field="qty"]')?.value) || 1);
  const cell = tr.querySelector('.row-line-total');
  if (cell) cell.textContent = (!isNaN(p) && p >= 0) ? formatPrice(p * qty) : '—';
}

function updateReceiptTotal() {
  let total = 0, hasAny = false;
  qsa('#invoiceTableBody tr').forEach(tr => {
    const p   = parseFloat(tr.querySelector('[data-field="price"]')?.value);
    const qty = Math.max(1, parseInt(tr.querySelector('[data-field="qty"]')?.value) || 1);
    if (!isNaN(p) && p >= 0) { total += p * qty; hasAny = true; }
  });
  const el = $('receiptTotal');
  if (el) el.textContent = hasAny ? formatPrice(total) : '—';
}

function addInvoiceRow(data = {}) {
  syncInvoiceRowsFromDOM();
  const id = nextRowId++;
  invoiceRows.push({
    id,
    brand:    data.brand    || '',
    model:    data.model    || '',
    location: data.location || '',
    category: data.category || '',
    project:  data.project  || '',
    users:    Array.isArray(data.users) ? [...data.users] : [],
    price:    data.price    != null ? String(data.price) : '',
    qty:      data.qty      || 1
  });
  renderInvoiceTable();
}

function removeInvoiceRow(id) {
  if (invoiceRows.length <= 1) return;
  syncInvoiceRowsFromDOM();
  invoiceRows = invoiceRows.filter(r => r.id !== id);
  renderInvoiceTable();
}

function renderUsersCell(rowId) {
  const tr = document.querySelector(`#invoiceTableBody tr[data-row-id="${rowId}"]`);
  if (!tr) return;
  const row = invoiceRows.find(r => r.id === rowId);
  if (!row) return;
  const container = tr.querySelector('.row-users');
  if (!container) return;
  container.querySelectorAll('.row-user-chip').forEach(el => el.remove());
  const input = container.querySelector('.row-user-input');
  const frag = document.createDocumentFragment();
  row.users.forEach(u => {
    const span = document.createElement('span');
    span.className = 'row-user-chip';
    span.innerHTML = `${escHtml(u)}<button type="button" class="row-chip-remove" data-user="${escAttr(u)}">&times;</button>`;
    frag.appendChild(span);
  });
  container.insertBefore(frag, input || null);
}

function addInvoiceUserChip(rowId, name) {
  name = name.trim();
  const row = invoiceRows.find(r => r.id === rowId);
  if (!row || !name || row.users.includes(name)) return;
  row.users.push(name);
  renderUsersCell(rowId);
}

function removeInvoiceUserChip(rowId, name) {
  const row = invoiceRows.find(r => r.id === rowId);
  if (!row) return;
  row.users = row.users.filter(u => u !== name);
  renderUsersCell(rowId);
}

function setupInvoiceTableListeners() {
  const tbody = $('invoiceTableBody');
  if (!tbody) return;

  tbody.addEventListener('click', e => {
    const del = e.target.closest('.row-del-btn');
    if (del && !del.disabled) { removeInvoiceRow(parseInt(del.dataset.rowId)); return; }
    const chip = e.target.closest('.row-chip-remove');
    if (chip) {
      const rowId = parseInt(chip.closest('tr')?.dataset.rowId);
      if (!isNaN(rowId)) removeInvoiceUserChip(rowId, chip.dataset.user);
    }
  });

  tbody.addEventListener('input', e => {
    const tr = e.target.closest('tr'); if (!tr) return;
    const f = e.target.dataset.field;
    if (f === 'price' || f === 'qty') { updateRowLineTotal(tr); updateReceiptTotal(); }
  });

  tbody.addEventListener('keydown', e => {
    if (!e.target.classList.contains('row-user-input')) return;
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const rowId = parseInt(e.target.closest('tr')?.dataset.rowId);
      const name = e.target.value.trim();
      if (!isNaN(rowId) && name) { addInvoiceUserChip(rowId, name); e.target.value = ''; }
    }
  });

  tbody.addEventListener('focusout', e => {
    if (!e.target.classList.contains('row-user-input')) return;
    const rowId = parseInt(e.target.closest('tr')?.dataset.rowId);
    const name = e.target.value.trim();
    if (!isNaN(rowId) && name) { addInvoiceUserChip(rowId, name); e.target.value = ''; }
  });
}

function collectInvoiceRowData(rowIdx) {
  const row = invoiceRows[rowIdx];
  if (!row) return { brand: 'N/A', model: 'N/A', location: 'N/A', category: '', project: 'N/A', users: [], price: null, qty: 1 };
  const tr = document.querySelector(`#invoiceTableBody tr[data-row-id="${row.id}"]`);
  const brand    = (tr?.querySelector('[data-field="brand"]')?.value    || row.brand    || '').trim() || 'N/A';
  const model    = (tr?.querySelector('[data-field="model"]')?.value    || row.model    || '').trim() || 'N/A';
  const location = (tr?.querySelector('[data-field="location"]')?.value || row.location || '').trim() || 'N/A';
  const category = (tr?.querySelector('[data-field="category"]')?.value || row.category || '').trim() || '';
  const project  = (tr?.querySelector('[data-field="project"]')?.value  || row.project  || '').trim() || 'N/A';
  const priceRaw = tr?.querySelector('[data-field="price"]')?.value ?? row.price;
  const price    = priceRaw !== '' && priceRaw != null ? parseFloat(priceRaw) : null;
  const qty      = Math.max(1, parseInt(tr?.querySelector('[data-field="qty"]')?.value) || row.qty || 1);
  return { brand, model, location, category, project, users: [...(row.users || [])], price: isNaN(price) ? null : price, qty };
}

// ===================== FORM DATA =====================
function collectFormData() {
  const shop          = ($('modalShop')?.value          || '').trim();
  const purchaseDate  = $('modalPurchaseDate')?.value   || '';
  const documentation = ($('modalDocumentation')?.value || '').trim() || 'N/A';
  const warrantyMonths = parseInt($('modalWarranty')?.value) || 0;

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

  // Read item fields from first row of invoice table (RM-191 will handle all rows)
  const row0 = collectInvoiceRowData(0);

  return {
    shop, purchase_date: formattedDate,
    brand: row0.brand, model: row0.model, location: row0.location,
    category: row0.category, project: row0.project, users: row0.users,
    price: row0.price, quantity: row0.qty,
    documentation, guarantee_duration: warrantyMonths, guarantee_unit: 'months',
    extended_warranty: extWarranty
  };
}

function validateForm() {
  const shop = ($('modalShop')?.value || '').trim();
  const pd   = $('modalPurchaseDate')?.value || '';
  if (!shop) { alert('Shop/Store is required.');    return false; }
  if (!pd)   { alert('Purchase Date is required.'); return false; }
  const pdDate  = new Date(pd);
  const today   = new Date(); today.setHours(0, 0, 0, 0);
  const minDate = new Date(today); minDate.setFullYear(minDate.getFullYear() - 100);
  if (pdDate > today)   { alert('Purchase date cannot be in the future.');                   return false; }
  if (pdDate < minDate) { alert('Purchase date cannot be more than 100 years in the past.'); return false; }
  // Validate first row
  const firstTr = qs('#invoiceTableBody tr');
  const brand = (firstTr?.querySelector('[data-field="brand"]')?.value || '').trim();
  const model = (firstTr?.querySelector('[data-field="model"]')?.value || '').trim();
  if (!brand) { alert('Brand is required for at least the first item.'); return false; }
  if (!model) { alert('Model is required for at least the first item.'); return false; }
  const priceRaw = (firstTr?.querySelector('[data-field="price"]')?.value || '').trim();
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

    // RM-182: save current item then open choose modal (with RM-181 pre-fill)
    const resp = await fetchJson(API.updateItem(itemId), {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData)
    });
    if (!resp.success) { alert(`Save failed: ${resp.error || 'Unknown error'}`); return; }
    await Promise.all([loadData(), loadSuggestions()]);
    openModalForChoose();
  } catch (err) { console.error('Add Another error:', err); alert(`Error: ${err.message}`); }
  finally { if (btn) btn.disabled = false; }
}

async function handleFinish(e) {
  e.preventDefault();
  if (!validateForm()) return;

  syncInvoiceRowsFromDOM();
  const itemId = parseInt($('modalItemId').value);

  // Collect receipt header fields (shared across all rows)
  const shop          = ($('modalShop')?.value          || '').trim();
  const purchaseDate  = $('modalPurchaseDate')?.value   || '';
  const documentation = ($('modalDocumentation')?.value || '').trim() || 'N/A';
  const warrantyMonths = parseInt($('modalWarranty')?.value) || 0;
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
      const d  = new Date(purchaseDate + 'T00:00:00');
      const mn = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      formattedDate = `${d.getFullYear()}-${mn[d.getMonth()]}-${String(d.getDate()).padStart(2,'0')}`;
    } catch { /* keep original */ }
  }

  const header = {
    shop, purchase_date: formattedDate, documentation,
    guarantee_duration: warrantyMonths, guarantee_unit: 'months',
    extended_warranty: extWarranty
  };

  const buildPayload = rowIdx => {
    const row = collectInvoiceRowData(rowIdx);
    return { ...header, brand: row.brand, model: row.model, location: row.location,
      category: row.category, project: row.project, users: row.users,
      price: row.price, quantity: row.qty };
  };

  const btn = $('btnFinish');
  if (btn) btn.disabled = true;
  try {
    // Row 0: update the pre-created placeholder item
    const resp0 = await fetchJson(API.updateItem(itemId), {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPayload(0))
    });
    if (!resp0.success) { alert(`Save failed (row 1): ${resp0.error || 'Unknown error'}`); return; }

    // Rows 1..N: create then fully update each additional row
    for (let i = 1; i < invoiceRows.length; i++) {
      const createResp = await fetchJson(API.createItem, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ receipt_group_id: sessionGroupId })
      });
      if (!createResp.success) { alert(`Save failed (row ${i + 1}): ${createResp.error || 'Unknown error'}`); return; }
      const newId = createResp.item.id;
      sessionItemIds.push(newId);

      const updateResp = await fetchJson(API.updateItem(newId), {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload(i))
      });
      if (!updateResp.success) { alert(`Save failed (row ${i + 1}): ${updateResp.error || 'Unknown error'}`); return; }
    }

    closeOcrModal();
    await loadData(); await loadSuggestions();
  } catch (err) {
    console.error('Save error:', err); alert(`Save failed: ${err.message}`);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function handleCancelModal() {
  if (sessionItemIds.length > 0) {
    const confirmed = confirm('Are you sure you want to cancel? Unsaved changes will be lost.');
    if (!confirmed) return;
    const mode = $('modalMode')?.value;
    if (mode === 'new' && sessionGroupId) {
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
    // RM-181: re-fill documentation after clear (it's a header field)
    if (receipt.documentation && receipt.documentation !== 'N/A') {
      const docEl = $('modalDocumentation'); if (docEl) docEl.value = receipt.documentation;
    }
    setModalMode('new');
  } catch (err) { console.error('Existing receipt error:', err); alert(`Error: ${err.message}`); }
}

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
  $('modalDocumentation').value = receipt.documentation !== 'N/A' ? receipt.documentation : '';
  $('modalWarranty').value      = item.guarantee_duration || '';

  const pd = receipt.purchase_date || '';
  if (pd && pd !== 'N/A') {
    try { $('modalPurchaseDate').value = new Date(pd.replace(/-/g, ' ')).toISOString().split('T')[0]; }
    catch { $('modalPurchaseDate').value = ''; }
  } else { $('modalPurchaseDate').value = ''; }

  // Populate invoice table with single row
  invoiceRows = []; nextRowId = 0;
  addInvoiceRow({
    brand:    item.brand    !== 'N/A' ? item.brand    : '',
    model:    item.model    !== 'N/A' ? item.model    : '',
    location: item.location !== 'N/A' ? item.location : '',
    category: item.category || '',
    project:  item.project  !== 'N/A' ? item.project  : '',
    users:    Array.isArray(item.users) ? item.users : normalizeUsers(item.users),
    price:    item.price != null ? String(item.price) : '',
    qty:      item.quantity || 1
  });

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

// ===================== FILTER PANEL (RM-193) =====================
function filterFieldLabel(key) {
  const f = FILTER_FIELDS.find(x => x.key === key);
  return (f && t(f.labelKey)) || key;
}

function getDistinctValues(fieldKey) {
  const vals = new Set();
  buildRows().forEach(r => {
    const v = String(r[fieldKey] || '').trim();
    if (v && v !== 'N/A') vals.add(v);
  });
  return [...vals].sort((a, b) => a.localeCompare(b));
}

function renderFilterValuesPane(fieldKey) {
  const pane = $('filterValuesContent'); if (!pane) return;
  const field = FILTER_FIELDS.find(f => f.key === fieldKey); if (!field) return;

  if (field.type === 'daterange') {
    const range = activeFilters.purchase_date || {};
    pane.innerHTML = `
      <div class="filter-daterange">
        <label>${escHtml(t('filterDateFrom') || 'From')}</label>
        <input type="date" id="filterDateFrom" value="${escAttr(range.from || '')}">
        <label>${escHtml(t('filterDateTo') || 'To')}</label>
        <input type="date" id="filterDateTo" value="${escAttr(range.to || '')}">
      </div>`;
    const syncDate = () => {
      const from = $('filterDateFrom')?.value || '';
      const to   = $('filterDateTo')?.value   || '';
      if (from || to) activeFilters.purchase_date = { from, to };
      else delete activeFilters.purchase_date;
      updateFilterUI(); filterAndRender();
    };
    bind('filterDateFrom', 'change', syncDate);
    bind('filterDateTo',   'change', syncDate);
    return;
  }

  const values   = getDistinctValues(fieldKey);
  const selected = activeFilters[fieldKey] || new Set();
  const searchHtml = field.search
    ? `<input type="text" id="filterValueSearch" class="filter-value-search" placeholder="${escAttr(t('filterSearch') || 'Search...')}">`
    : '';
  const listHtml = values.length
    ? values.map(v => `<label class="filter-checkbox-label">
        <input type="checkbox" class="filter-value-cb" data-field="${escAttr(fieldKey)}" data-value="${escAttr(v)}"${selected.has(v) ? ' checked' : ''}>
        ${escHtml(v)}</label>`).join('')
    : `<span class="filter-empty">${escHtml(t('noFilterValues') || 'No values')}</span>`;

  pane.innerHTML = searchHtml + `<div id="filterCheckboxList" class="filter-checkbox-list">${listHtml}</div>`;

  if (field.search) {
    bind('filterValueSearch', 'input', e => {
      const q = e.target.value.toLowerCase();
      qsa('#filterCheckboxList .filter-checkbox-label').forEach(lbl =>
        lbl.style.display = lbl.textContent.trim().toLowerCase().includes(q) ? '' : 'none'
      );
    });
  }

  qsa('#filterCheckboxList .filter-value-cb').forEach(cb => {
    cb.addEventListener('change', () => {
      const fk  = cb.dataset.field;
      const val = cb.dataset.value;
      if (!activeFilters[fk]) activeFilters[fk] = new Set();
      if (cb.checked) activeFilters[fk].add(val);
      else {
        activeFilters[fk].delete(val);
        if (!activeFilters[fk].size) delete activeFilters[fk];
      }
      updateFilterUI(); filterAndRender();
    });
  });
}

function countActiveFilters() {
  return FILTER_FIELDS.reduce((n, f) => {
    if (f.type === 'daterange') return n + ((activeFilters.purchase_date?.from || activeFilters.purchase_date?.to) ? 1 : 0);
    return n + (activeFilters[f.key]?.size > 0 ? 1 : 0);
  }, 0);
}

function updateFilterUI() {
  const count = countActiveFilters();
  const badge = $('filterBadge');
  if (badge) { badge.textContent = count; badge.style.display = count > 0 ? '' : 'none'; }

  qsa('.filter-field-btn').forEach(btn => {
    const fk = btn.dataset.field;
    const on = fk === 'purchase_date'
      ? !!(activeFilters.purchase_date?.from || activeFilters.purchase_date?.to)
      : !!(activeFilters[fk]?.size);
    btn.classList.toggle('has-filter', on);
  });

  renderFilterChips();
}

function renderFilterChips() {
  const container = $('activeFilterChips'); if (!container) return;
  const chips = [];
  FILTER_FIELDS.forEach(f => {
    if (f.type === 'daterange') {
      const r = activeFilters.purchase_date;
      if (r?.from || r?.to) {
        const lbl = [r.from, r.to].filter(Boolean).join(' → ');
        chips.push(`<span class="filter-chip"><strong>${escHtml(filterFieldLabel(f.key))}:</strong> ${escHtml(lbl)}<button type="button" class="chip-remove" data-field="purchase_date">&times;</button></span>`);
      }
    } else {
      const vals = activeFilters[f.key];
      if (vals?.size) {
        [...vals].forEach(v =>
          chips.push(`<span class="filter-chip"><strong>${escHtml(filterFieldLabel(f.key))}:</strong> ${escHtml(v)}<button type="button" class="chip-remove" data-field="${escAttr(f.key)}" data-value="${escAttr(v)}">&times;</button></span>`)
        );
      }
    }
  });
  container.innerHTML = chips.join('');
  container.style.display = chips.length ? '' : 'none';

  qsa('#activeFilterChips .chip-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      const fk  = btn.dataset.field;
      const val = btn.dataset.value;
      if (fk === 'purchase_date') {
        delete activeFilters.purchase_date;
      } else {
        activeFilters[fk]?.delete(val);
        if (!activeFilters[fk]?.size) delete activeFilters[fk];
      }
      updateFilterUI(); filterAndRender();
      if (filterPanelField === fk) renderFilterValuesPane(fk);
    });
  });
}

function clearAllFilters() {
  activeFilters = {};
  updateFilterUI(); filterAndRender();
  renderFilterValuesPane(filterPanelField);
}

function openFilterPanel() {
  const panel = $('filterPanel'); if (!panel) return;
  panel.style.display = '';
  qsa('.filter-field-btn').forEach(b => b.classList.toggle('active', b.dataset.field === filterPanelField));
  renderFilterValuesPane(filterPanelField);
}

// ===================== SETTINGS =====================
async function saveSettings() {
  const currency      = $('currencySelect')?.value      || 'EUR';
  const format        = $('currencyFormatSelect')?.value || 'symbol';
  const warningMonths = parseInt($('warrantyWarningInput')?.value) || 3;
  const dateFormat    = $('dateFormatSelect')?.value    || 'DD-MMM-YYYY';
  try {
    appSettings = await fetchJson(API.settings, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ currency, currency_display_format: format, warranty_expiration_warning_months: warningMonths, date_format: dateFormat })
    });
    filterAndRender();
    alert('Settings saved.');
  } catch (err) { console.error('Settings save error:', err); alert(`Failed to save settings: ${err.message}`); }
}

// ===================== EVENT LISTENERS =====================
function setupEventListeners() {
  bind('addReceiptBtn', 'click', openModalForChoose);

  const modalFileInput = $('modalFileInput');
  if (modalFileInput) {
    modalFileInput.addEventListener('change', e => { const f = e.target.files?.[0]; if (f) handleFile(f); });
  }

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

  bind('existingReceiptSort',   'change', populateExistingReceiptSelect);
  bind('existingReceiptSelect', 'change', handleExistingReceiptSelect);
  bind('addRowBtn', 'click', () => addInvoiceRow({}));
  setupInvoiceTableListeners();

  // RM-185: compact rows toggle
  bind('compactRowsToggle', 'change', e => {
    applyCompactRows(e.target.checked);
    localStorage.setItem('rm_compact_rows', e.target.checked);
  });

  // RM-190: column order gear + selects
  bind('chooseColOrderBtn', 'click', () => {
    const panel = $('chooseColOrderPanel');
    if (panel) {
      const visible = panel.style.display !== 'none';
      panel.style.display = visible ? 'none' : 'flex';
      if (!visible) syncChooseColSelects();
    }
  });
  bind('chooseCol1', 'change', () => handleChooseColChange(0));
  bind('chooseCol2', 'change', () => handleChooseColChange(1));
  bind('chooseCol3', 'change', () => handleChooseColChange(2));

  // RM-186: live line total
  const updateLineTotal = () => {
    const qty   = Math.max(1, parseInt($('modalQuantity')?.value) || 1);
    const price = parseFloat($('modalPrice')?.value);
    const el    = $('lineTotalDisplay');
    if (el) el.textContent = (!isNaN(price) && price >= 0) ? formatPrice(qty * price) : '—';
  };
  bind('modalPrice',    'input', updateLineTotal);
  bind('modalQuantity', 'input', updateLineTotal);

  bind('searchInput',   'input',  filterAndRender);
  bind('projectFilter', 'change', filterAndRender);
  bind('statusFilter',  'change', filterAndRender);
  bind('userFilter',    'change', filterAndRender);
  bind('refreshBtn',    'click',  () => { loadData(); loadSuggestions(); });

  bind('columnToggleBtn',  'click', () => { const p = $('columnPanel'); if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none'; });
  bind('closeColumnPanel', 'click', () => { const p = $('columnPanel'); if (p) p.style.display = 'none'; });

  bind('recheckBtn',     'click', recheckIntegrity);
  bind('closeBannerBtn', 'click', () => { const b = $('integrityBanner'); if (b) b.style.display = 'none'; });

  bind('closeModal',    'click',  handleCancelModal);
  bind('cancelModal',   'click',  handleCancelModal);

  bind('ocrForm',       'submit', saveOcrData);

  const modal = $('ocrModal');
  if (modal) modal.addEventListener('click', e => { if (e.target === modal) handleCancelModal(); });

  bind('extendedWarrantyCheckbox', 'change', e => {
    const fields = $('extendedWarrantyFields');
    if (fields) fields.classList.toggle('hidden', !e.target.checked);
  });

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

  bind('saveSettingsBtn', 'click', saveSettings);
  bind('menuBackupBtn',   'click', exportJson);
  bind('menuExportBtn',   'click', exportCsv);
  bind('menuRestoreBtn',  'click', () => $('importInput')?.click());
  bind('importInput',     'change', handleImport);

  qsa('.col-toggle').forEach(t => t.addEventListener('change', e => {
    const col = e.target.dataset.column; if (!col) return;
    if (e.target.checked) visibleColumns.add(col); else visibleColumns.delete(col);
    localStorage.setItem('rm_visible_columns', JSON.stringify([...visibleColumns]));
    updateColumnVisibility();
  }));

  qsa('th.sortable').forEach(th => th.addEventListener('click', () => {
    const col = th.dataset.column; if (!col) return;
    if (currentSort.column === col) currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    else { currentSort.column = col; currentSort.direction = 'asc'; }
    localStorage.setItem('rm_sort_column', currentSort.column);
    localStorage.setItem('rm_sort_direction', currentSort.direction);
    updateSortIndicators(); filterAndRender();
  }));

  // RM-193: filter panel
  bind('filterBtn', 'click', () => {
    const panel = $('filterPanel');
    if (!panel) return;
    if (panel.style.display === 'none') { openFilterPanel(); }
    else { panel.style.display = 'none'; }
  });

  document.addEventListener('click', e => {
    const panel = $('filterPanel');
    if (!panel || panel.style.display === 'none') return;
    if (!panel.contains(e.target) && !$('filterBtn')?.contains(e.target)) {
      panel.style.display = 'none';
    }
  });

  document.addEventListener('click', e => {
    const btn = e.target.closest('.filter-field-btn');
    if (!btn) return;
    filterPanelField = btn.dataset.field;
    qsa('.filter-field-btn').forEach(b => b.classList.toggle('active', b === btn));
    renderFilterValuesPane(filterPanelField);
  });

  bind('clearAllFiltersBtn', 'click', clearAllFilters);

  // Re-render item count when language changes so the translation updates
  window.addEventListener('languageChanged', () => filterAndRender());
}

// ===================== PERSISTENCE (RM-179, RM-184, RM-185, RM-190) =====================
function loadPersistedPreferences() {
  const savedCol = localStorage.getItem('rm_sort_column');
  const savedDir = localStorage.getItem('rm_sort_direction');
  if (savedCol) { currentSort.column = savedCol; currentSort.direction = savedDir || 'asc'; }

  const savedCols = localStorage.getItem('rm_visible_columns');
  if (savedCols) {
    try {
      visibleColumns = new Set(JSON.parse(savedCols));
      qsa('.col-toggle').forEach(cb => { cb.checked = visibleColumns.has(cb.dataset.column); });
    } catch { /* keep defaults */ }
  }

  // RM-185: compact rows
  applyCompactRows(localStorage.getItem('rm_compact_rows') === 'true');

  // RM-190: choose column order
  const savedOrder = localStorage.getItem('rm_choose_col_order');
  if (savedOrder) {
    try {
      const arr = JSON.parse(savedOrder);
      if (Array.isArray(arr) && arr.length === 3) chooseColOrder = arr;
    } catch { /* keep defaults */ }
  }
}

// ===================== COMPACT ROWS (RM-185) =====================
function applyCompactRows(enabled) {
  const table = $('itemsTable');
  if (table) table.classList.toggle('compact', enabled);
  const toggle = $('compactRowsToggle');
  if (toggle) toggle.checked = enabled;
}

// ===================== CHOOSE COLUMN ORDER (RM-190) =====================
function syncChooseColSelects() {
  ['chooseCol1', 'chooseCol2', 'chooseCol3'].forEach((id, i) => {
    const el = $(id); if (el) el.value = chooseColOrder[i];
  });
}

function handleChooseColChange(changedIdx) {
  const ids = ['chooseCol1', 'chooseCol2', 'chooseCol3'];
  const newVal = $(ids[changedIdx])?.value;
  if (!newVal) return;
  // Swap the other slot that already had this value
  const swapIdx = chooseColOrder.findIndex((v, i) => i !== changedIdx && v === newVal);
  if (swapIdx >= 0) chooseColOrder[swapIdx] = chooseColOrder[changedIdx];
  chooseColOrder[changedIdx] = newVal;
  syncChooseColSelects();
  localStorage.setItem('rm_choose_col_order', JSON.stringify(chooseColOrder));
  populateExistingReceiptSelect();
}

// ===================== AUTH (RM-177) =====================
async function checkAuthAndShowLogout() {
  try {
    const status = await fetchJson('/api/auth-status');
    if (status.auth_enabled) { const btn = $('logoutBtn'); if (btn) btn.style.display = ''; }
  } catch { /* non-critical */ }
}

// ===================== INIT =====================
function appInit() {
  const pdInput = $('modalPurchaseDate');
  if (pdInput) {
    const today   = new Date();
    const minDate = new Date(today); minDate.setFullYear(minDate.getFullYear() - 100);
    pdInput.max = today.toISOString().split('T')[0];
    pdInput.min = minDate.toISOString().split('T')[0];
  }
  loadPersistedPreferences();
  loadSettings();
  loadData();
  loadSuggestions();
  setupEventListeners();
  checkAuthAndShowLogout();
}

// Wait for i18next to be ready before starting the app
// This ensures t() works correctly from the very first render
window.addEventListener('i18nextReady', appInit);

// Fallback: if i18nextReady never fires (e.g. CDN failure), start anyway after DOM load
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if (typeof i18next === 'undefined' || !i18next.isInitialized) {
      console.warn('[app] i18nextReady never fired, starting app without i18n');
      appInit();
    }
  }, 3000);
});
