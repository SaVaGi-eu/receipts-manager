// Use translation system from i18next (loaded via CDN and i18n.js)
// No local t() function - use window.t directly which is set by i18n.js

function updateUI() {
  console.log('[app] Updating UI');
  // Let i18n.js handle the main translation
  if (typeof window.translatePage === 'function') {
    window.translatePage();
  }

  // Update item count with proper pluralization
  const count = allData.items?.length || 0;
  const itemCountEl = document.getElementById('itemCount');
  if (itemCountEl && typeof window.t === 'function') {
    itemCountEl.textContent = window.t('itemCount', { count });
  }

  // Update buttons in table
  if (typeof window.t === 'function') {
    document.querySelectorAll('.btn-edit').forEach(btn => btn.textContent = window.t('edit'));
    document.querySelectorAll('.btn-delete').forEach(btn => btn.textContent = window.t('delete'));
    document.querySelectorAll('.btn-open').forEach(btn => btn.textContent = window.t('open'));
  }
}

// ===== Original Application Logic =====
let allData = { receipts: [], items: [], next_id: 1, integrity_issues: [] };
let suggestions = { shops: [], brands: [], models: [], locations: [], documentation: [], projects: [], users: [], categories: [] }; // RM-79: Added categories
let currentSort = { column: 'id', direction: 'asc' };
let visibleColumns = new Set([
  'id', 'receipt_group_id', 'brand', 'model', 'location', 'category', 'users', // RM-79: Added category
  'project', 'shop', 'purchase_date', 'documentation', 'guarantee_end_date', 'extended_warranty', 'actions' // RM-77: Added extended_warranty, removed 'file'
]);

// ===== User tags management =====
let userTags = [];

const API = {
  data: '/api/data',
  suggestions: '/api/suggestions',
  exportJson: '/api/export/json',
  exportCsv: '/api/export/csv',
  importJson: '/api/import/json',
  integrityCheck: '/api/integrity/check',
  upload: '/api/upload',
  updateItem: (id) => `/api/item/${id}`,
  deleteItem: (id) => `/api/item/${id}`,
  fileUrl: (path) => `/api/file?path=${encodeURIComponent(path)}`
};

function $(id) { return document.getElementById(id); }
function qs(sel) { return document.querySelector(sel); }
function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }

function bind(id, event, handler) {
  const el = $(id);
  if (!el) { console.warn(`[bind] Missing #${id}`); return; }
  el.addEventListener(event, handler);
}

async function fetchJson(url, opts) {
  const resp = await fetch(url, opts);
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`${opts?.method || 'GET'} ${url} failed: ${resp.status} ${text}`);
  }
  return await resp.json();
}

function downloadUrl(url) {
  const a = document.createElement('a');
  a.href = url; a.download = '';
  document.body.appendChild(a); a.click(); a.remove();
}
function exportJson() { downloadUrl(API.exportJson); }
function exportCsv()  { downloadUrl(API.exportCsv);  }

async function loadData() {
  try {
    allData = await fetchJson(API.data);
    const banner = $('integrityBanner');
    if (banner) {
      const issues = allData.integrity_issues || [];
      banner.style.display = issues.length > 0 ? 'flex' : 'none';
      if ($('integrityMessage') && typeof window.t === 'function')
        $('integrityMessage').textContent = issues.length > 0 ? window.t('integrityIssues', { count: issues.length }) : '';
    }
    filterAndRender();
  } catch (err) {
    console.error('Error loading data:', err);
    alert('Error loading data (see Console).');
  }
}

async function loadSuggestions() {
  try {
    suggestions = await fetchJson(API.suggestions);
    populateDataLists();
    populateFilterDropdowns();
    populateExistingReceipts();
  } catch (err) { console.error('Error loading suggestions:', err); }
}

function populateDataLists() {
  const set = (id, arr) => {
    const el = $(id); if (!el) return;
    const safe = Array.isArray(arr) ? arr : [];
    el.innerHTML = safe.map(s => `<option value="${String(s).replace(/"/g, '&quot;')}">`).join('');
  };
  set('shopList', suggestions.shops);
  set('brandList', suggestions.brands);
  set('modelList', suggestions.models);
  set('locationList', suggestions.locations);
  set('docList', suggestions.documentation);
  set('projectList', suggestions.projects);
  set('userList', suggestions.users);
  set('categoryList', suggestions.categories || []); // RM-79: Category autocomplete
}

function populateFilterDropdowns() {
  const t = window.t || (key => key);
  const projectFilter = $('projectFilter');
  if (projectFilter) {
    const current = projectFilter.value;
    projectFilter.innerHTML = `<option value="">${t('allProjects')}</option>` +
      (Array.isArray(suggestions.projects) ? suggestions.projects : [])
        .map(p => `<option value="${String(p).replace(/"/g, '&quot;')}">${p}</option>`).join('');
    projectFilter.value = current;
  }
  const userFilter = $('userFilter');
  if (userFilter) {
    const current = userFilter.value;
    userFilter.innerHTML = `<option value="">${t('allUsers')}</option>` +
      (Array.isArray(suggestions.users) ? suggestions.users : [])
        .map(u => `<option value="${String(u).replace(/"/g, '&quot;')}">${u}</option>`).join('');
    userFilter.value = current;
  }
}

function populateExistingReceipts() {
  const select = $('existingReceiptSelect');
  if (!select) return;
  const t = window.t || (key => key);
  
  const rmap = receiptMap();
  const options = Array.from(rmap.values())
    .sort((a, b) => String(b.purchase_date || '').localeCompare(String(a.purchase_date || '')))
    .map(r => {
      const label = `${r.shop || 'Unknown'} - ${r.purchase_date || 'No date'} - ${r.receipt_group_id}`;
      return `<option value="${r.receipt_group_id}">${label}</option>`;
    }).join('');
  
  select.innerHTML = `<option value="">${t('selectReceiptOption')}</option>` + options;
}

function receiptMap() {
  const map = new Map();
  (allData.receipts || []).forEach(r => map.set(r.receipt_group_id, r));
  return map;
}

function normalizeUsers(u) {
  if (Array.isArray(u)) return u;
  return String(u || '').split(';').map(s => s.trim()).filter(Boolean);
}

function getStatus(item) {
  const end = item?.guarantee_end_date;
  if (!end || end === 'N/A') return 'active';
  const d = new Date(String(end).replace(/-/g, '/'));
  if (isNaN(d)) return 'active';
  const diffDays = Math.floor((d - new Date()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return 'expired';
  if (diffDays <= 90) return 'expiring';
  return 'active';
}

function applyFilters(rows) {
  const q       = ($('searchInput')?.value  || '').trim().toLowerCase();
  const project = $('projectFilter')?.value || '';
  const status  = $('statusFilter')?.value  || '';
  const user    = $('userFilter')?.value    || '';
  return (rows || []).filter(r => {
    if (project && String(r.project || '') !== project) return false;
    if (status  && getStatus(r) !== status) return false;
    if (user    && !normalizeUsers(r.users).includes(user)) return false;
    if (q) {
      const hay = [
        r.id, r.receipt_group_id, r.brand, r.model, r.location, r.category, r.project, // RM-79: Added category to search
        r.shop, r.purchase_date, r.documentation, r.guarantee_end_date,
        normalizeUsers(r.users).join('; ')
      ].map(x => String(x || '').toLowerCase()).join(' | ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

// RM-75: Numeric ID sorting
function sortRows(rows) {
  const col = currentSort.column;
  const dir = currentSort.direction === 'desc' ? -1 : 1;
  return [...rows].sort((a, b) => {
    const aVal = a?.[col] ?? '';
    const bVal = b?.[col] ?? '';
    
    // RM-75: Numeric sorting for ID column
    if (col === 'id') {
      const aNum = parseInt(aVal);
      const bNum = parseInt(bVal);
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return (aNum - bNum) * dir;
      }
    }
    
    // String sorting for other columns
    return String(aVal).localeCompare(String(bVal)) * dir;
  });
}

function buildRows() {
  const rmap = receiptMap();
  return (allData.items || []).map(it => {
    const r = rmap.get(it.receipt_group_id) || {};
    return {
      id: it.id, 
      receipt_group_id: it.receipt_group_id,
      brand: it.brand || '', 
      model: it.model || '', 
      location: it.location || '',
      category: it.category || '', // RM-79: Category field
      users: it.users || [], 
      project: it.project || '',
      shop: r.shop || '', 
      purchase_date: r.purchase_date || '',
      documentation: r.documentation || '', 
      guarantee_end_date: it.guarantee_end_date || '',
      extended_warranty: it.extended_warranty ? '✓' : '', // RM-77: Extended warranty indicator
      receipt_relative_path: r.receipt_relative_path || it.receipt_relative_path || ''
    };
  });
}

function renderTable(rows) {
  const tbody = $('tableBody');
  if (!tbody) return;
  const t = window.t || (key => key);
  if (!rows || rows.length === 0) {
    tbody.innerHTML = `<tr class="empty-state"><td colspan="14"><div class="empty-message"><span class="empty-icon">📦</span><p>${t('noItems')}</p></div></td></tr>`;
    if ($('itemCount')) $('itemCount').textContent = t('itemCount', { count: 0 });
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const hasFile = !!r.receipt_relative_path;
    const openButton = hasFile 
      ? `<button type="button" class="btn-small btn-open" data-action="open" data-file-path="${r.receipt_relative_path}">${t('open')}</button>`
      : '';

    return `
    <tr data-item-id="${r.id}">
      <td data-column="id">${r.id ?? ''}</td>
      <td data-column="receipt_group_id">${r.receipt_group_id ?? ''}</td>
      <td data-column="brand">${r.brand ?? ''}</td>
      <td data-column="model">${r.model ?? ''}</td>
      <td data-column="location">${r.location ?? ''}</td>
      <td data-column="category">${r.category ?? ''}</td>
      <td data-column="users">${normalizeUsers(r.users).join('; ')}</td>
      <td data-column="project">${r.project ?? ''}</td>
      <td data-column="shop">${r.shop ?? ''}</td>
      <td data-column="purchase_date">${r.purchase_date ?? ''}</td>
      <td data-column="documentation">${r.documentation ?? ''}</td>
      <td data-column="guarantee_end_date">${r.guarantee_end_date ?? ''}</td>
      <td data-column="extended_warranty">${r.extended_warranty ?? ''}</td>
      <td data-column="actions">
        ${openButton}
        <button type="button" class="btn-small btn-edit" data-action="edit">${t('edit')}</button>
        <button type="button" class="btn-small btn-delete" data-action="delete">${t('delete')}</button>
      </td>
    </tr>`;
  }).join('');
  if ($('itemCount')) $('itemCount').textContent = t('itemCount', { count: rows.length });
  updateColumnVisibility();
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

function filterAndRender() {
  renderTable(sortRows(applyFilters(buildRows())));
}

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

async function handleFile(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const resp = await fetch(API.upload, { method: 'POST', body: formData });
    if (!resp.ok) { alert(`Upload failed: ${await resp.text()}`); return; }
    const result = await resp.json();
    if (!result.success) { alert(`Upload failed: ${result.error || 'Unknown error'}`); return; }
    showOcrModal(result, 'new');
  } catch (err) { console.error('Upload error:', err); alert(`Upload failed: ${err.message}`); }
  finally { const fi = $('modalFileInput'); if (fi) fi.value = ''; }
}

function showOcrModal(uploadResult, mode = 'new') {
  const modal = $('ocrModal'); if (!modal) return;
  const ocr = uploadResult?.ocr_data || {};
  
  $('modalMode').value = mode;
  $('modalItemId').value = mode === 'new' ? (uploadResult?.item_id || '') : '';
  $('modalReceiptGroupId').value = uploadResult?.receipt_group_id || '';

  const modalTitle = $('modalTitle');
  if (modalTitle) {
    if (mode === 'new') modalTitle.textContent = '📄 Add New Receipt';
    else if (mode === 'existing') modalTitle.textContent = '📎 Add Item to Existing Receipt';
    else if (mode === 'edit') modalTitle.textContent = '✏️ Edit Item';
  }

  $('modalShop').value = ocr.shop || '';
  const pd = ocr.purchase_date || '';
  if (pd && pd !== 'N/A') {
    try { $('modalPurchaseDate').value = new Date(pd.replace(/-/g, ' ')).toISOString().split('T')[0]; }
    catch { $('modalPurchaseDate').value = ''; }
  } else { $('modalPurchaseDate').value = ''; }
  $('modalDocumentation').value = ocr.documentation || '';
  $('modalWarranty').value = '';
  $('modalBrand').value = ''; 
  $('modalModel').value = ''; 
  $('modalLocation').value = '';
  $('modalCategory').value = ''; // RM-79: Clear category field
  $('modalProject').value = '';
  
  // RM-77: Clear extended warranty fields
  $('extendedWarrantyCheckbox').checked = false;
  $('extWarrantyProvider').value = '';
  $('extWarrantyMonths').value = '';
  $('extWarrantyCost').value = '';
  $('extendedWarrantyFields').classList.add('hidden');
  
  userTags = [];
  renderUserTags();

  const isExisting = mode === 'existing';
  $('modalShop').readOnly = isExisting;
  $('modalPurchaseDate').readOnly = isExisting;
  $('modalDocumentation').readOnly = isExisting;
  if (isExisting) {
    $('modalShop').classList.add('readonly');
    $('modalPurchaseDate').classList.add('readonly');
    $('modalDocumentation').classList.add('readonly');
  } else {
    $('modalShop').classList.remove('readonly');
    $('modalPurchaseDate').classList.remove('readonly');
    $('modalDocumentation').classList.remove('readonly');
  }

  const uploadSection = qs('.upload-select-section');
  if (uploadSection) uploadSection.style.display = (mode === 'edit') ? 'none' : 'block';

  const itemsPreview = $('modalItemsPreview');
  const itemsList = $('modalItemsList');
  if (ocr.items && ocr.items.length > 0) {
    itemsList.innerHTML = ocr.items.map(i => `<li>${i.name} - ${i.price}</li>`).join('');
    itemsPreview.style.display = 'block';
  } else { itemsPreview.style.display = 'none'; }
  
  modal.style.display = 'flex';
}

function openNewReceiptModal() {
  $('ocrForm').reset();
  $('modalMode').value = 'new';
  $('modalItemId').value = '';
  $('modalReceiptGroupId').value = '';
  $('existingReceiptSelect').value = '';
  
  // RM-77: Reset extended warranty fields
  $('extendedWarrantyCheckbox').checked = false;
  $('extendedWarrantyFields').classList.add('hidden');
  
  userTags = [];
  renderUserTags();
  
  const modalTitle = $('modalTitle');
  if (modalTitle) modalTitle.textContent = '📄 Add New Receipt';
  
  const uploadSection = qs('.upload-select-section');
  if (uploadSection) uploadSection.style.display = 'block';
  
  $('modalShop').readOnly = false;
  $('modalPurchaseDate').readOnly = false;
  $('modalDocumentation').readOnly = false;
  $('modalShop').classList.remove('readonly');
  $('modalPurchaseDate').classList.remove('readonly');
  $('modalDocumentation').classList.remove('readonly');
  
  $('modalItemsPreview').style.display = 'none';
  $('ocrModal').style.display = 'flex';
}

function handleExistingReceiptSelect(e) {
  const receiptGroupId = e.target.value;
  if (!receiptGroupId) return;
  
  const fileInput = $('modalFileInput');
  if (fileInput) fileInput.value = '';
  
  const receipt = allData.receipts.find(r => r.receipt_group_id === receiptGroupId);
  if (!receipt) { alert('Receipt not found'); return; }
  
  const result = {
    receipt_group_id: receipt.receipt_group_id,
    ocr_data: {
      shop: receipt.shop,
      purchase_date: receipt.purchase_date,
      documentation: receipt.documentation
    }
  };
  
  showOcrModal(result, 'existing');
}

function closeOcrModal() {
  const modal = $('ocrModal');
  if (modal) { 
    modal.style.display = 'none'; 
    $('ocrForm').reset(); 
    $('existingReceiptSelect').value = '';
    const fileInput = $('modalFileInput');
    if (fileInput) fileInput.value = '';
    // RM-77: Reset extended warranty
    $('extendedWarrantyCheckbox').checked = false;
    $('extendedWarrantyFields').classList.add('hidden');
    userTags = [];
    renderUserTags();
  }
}

// RM-80: Menu modal functions
function openMenuModal() {
  const modal = $('menuModal');
  if (!modal) return;
  
  // Update current location display
  const storageType = $('currentStorageType');
  const storagePath = $('currentStoragePath');
  if (storageType) storageType.textContent = 'Local';
  if (storagePath) storagePath.textContent = '/data/receipts.json';
  
  modal.style.display = 'flex';
}

function closeMenuModal() {
  const modal = $('menuModal');
  if (modal) modal.style.display = 'none';
}

function openLocationModal() {
  const modal = $('locationModal');
  if (!modal) return;
  
  // Set current selection to local
  const localRadio = $('storageLocal');
  if (localRadio) localRadio.checked = true;
  
  modal.style.display = 'flex';
}

function closeLocationModal() {
  const modal = $('locationModal');
  if (modal) modal.style.display = 'none';
}

function applyLocationChange() {
  const selectedStorage = document.querySelector('input[name="storage"]:checked')?.value;
  
  if (selectedStorage === 'cloud') {
    alert('Cloud storage is coming soon!');
    return;
  }
  
  // For local storage, just close the modal
  closeLocationModal();
  closeMenuModal();
  alert('Storage location confirmed: Local (/data)');
}

function addUserTag(username) {
  const trimmed = username.trim();
  if (!trimmed || userTags.includes(trimmed)) return;
  userTags.push(trimmed);
  renderUserTags();
  $('userTagInput').value = '';
}

function removeUserTag(username) {
  userTags = userTags.filter(u => u !== username);
  renderUserTags();
}

function renderUserTags() {
  const container = $('userTags');
  if (!container) return;
  container.innerHTML = userTags.map(user => 
    `<span class="user-tag" data-user="${user.replace(/"/g, '&quot;')}">
      ${user}
      <span class="tag-remove">×</span>
    </span>`
  ).join('');
  
  // Add event listeners to remove buttons
  container.querySelectorAll('.tag-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const tag = e.target.closest('.user-tag');
      const username = tag?.dataset.user;
      if (username) removeUserTag(username);
    });
  });
}

async function saveOcrData(e) {
  e.preventDefault();
  const mode = $('modalMode').value;
  let itemId = parseInt($('modalItemId').value);
  const receiptGroupId = $('modalReceiptGroupId').value;

  const shop = $('modalShop').value.trim();
  const purchaseDate = $('modalPurchaseDate').value;
  const warranty = parseInt($('modalWarranty').value) || 0;
  const brand = $('modalBrand').value.trim(); // RM-78: Required field
  const model = $('modalModel').value.trim(); // RM-78: Required field
  const location = $('modalLocation').value.trim() || 'N/A';
  const category = $('modalCategory').value.trim() || 'N/A'; // RM-79: Category field
  const project = $('modalProject').value.trim() || 'N/A';
  const documentation = $('modalDocumentation').value.trim() || 'N/A';
  const users = userTags.length > 0 ? userTags : [];

  // RM-78: Validate required fields
  if (!shop || !purchaseDate || !brand || !model) { 
    alert('Shop, Purchase Date, Brand, and Model are required');
    return; 
  }

  // RM-77: Extended warranty data
  let extendedWarranty = null;
  if ($('extendedWarrantyCheckbox').checked) {
    extendedWarranty = {
      provider: $('extWarrantyProvider').value.trim() || '',
      months: parseInt($('extWarrantyMonths').value) || 0,
      cost: $('extWarrantyCost').value.trim() || ''
    };
  }

  let formattedDate = purchaseDate;
  try {
    const d = new Date(purchaseDate + 'T00:00:00');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    formattedDate = `${d.getFullYear()}-${months[d.getMonth()]}-${String(d.getDate()).padStart(2,'0')}`;
  } catch { /* keep original */ }

  if (mode === 'existing' && !itemId) {
    itemId = allData.next_id || 1;
  }

  if (!itemId || !receiptGroupId) { alert('Invalid item or receipt ID'); return; }

  try {
    const payload = {
      shop,
      purchase_date: formattedDate,
      brand,
      model,
      location,
      category, // RM-79: Include category
      project,
      documentation,
      users,
      guarantee_duration: warranty,
      guarantee_unit: 'months'
    };
    
    // RM-77: Add extended warranty if present
    if (extendedWarranty) {
      payload.extended_warranty = extendedWarranty;
    }
    
    const resp = await fetchJson(API.updateItem(itemId), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!resp.success) { alert(`Save failed: ${resp.error || 'Unknown error'}`); return; }
    closeOcrModal();
    await loadData(); 
    await loadSuggestions();
  } catch (err) { console.error('Save error:', err); alert(`Save failed: ${err.message}`); }
}

async function editItem(itemId) {
  const item = allData.items.find(i => i.id === itemId);
  if (!item) { alert('Item not found'); return; }
  const receipt = allData.receipts.find(r => r.receipt_group_id === item.receipt_group_id);
  if (!receipt) { alert('Receipt not found'); return; }

  $('modalItemId').value = item.id;
  $('modalReceiptGroupId').value = item.receipt_group_id;
  $('modalMode').value = 'edit';
  $('modalShop').value = receipt.shop !== 'N/A' ? receipt.shop : '';
  $('modalBrand').value = item.brand !== 'N/A' ? item.brand : '';
  $('modalModel').value = item.model !== 'N/A' ? item.model : '';
  $('modalLocation').value = item.location !== 'N/A' ? item.location : '';
  $('modalCategory').value = item.category !== 'N/A' ? item.category : ''; // RM-79: Load category
  $('modalProject').value = item.project !== 'N/A' ? item.project : '';
  $('modalDocumentation').value = receipt.documentation !== 'N/A' ? receipt.documentation : '';
  
  // RM-77: Load extended warranty data
  if (item.extended_warranty) {
    $('extendedWarrantyCheckbox').checked = true;
    $('extWarrantyProvider').value = item.extended_warranty.provider || '';
    $('extWarrantyMonths').value = item.extended_warranty.months || '';
    $('extWarrantyCost').value = item.extended_warranty.cost || '';
    $('extendedWarrantyFields').classList.remove('hidden');
  } else {
    $('extendedWarrantyCheckbox').checked = false;
    $('extendedWarrantyFields').classList.add('hidden');
  }
  
  userTags = Array.isArray(item.users) ? item.users : [];
  renderUserTags();

  const warranty = item.guarantee_unit === 'months' ? (item.guarantee_duration || 0) : 0;
  $('modalWarranty').value = warranty > 0 ? warranty : '';

  const pd = receipt.purchase_date || '';
  if (pd && pd !== 'N/A') {
    try { $('modalPurchaseDate').value = new Date(pd.replace(/-/g, ' ')).toISOString().split('T')[0]; }
    catch { $('modalPurchaseDate').value = ''; }
  } else { $('modalPurchaseDate').value = ''; }

  $('modalShop').readOnly = false;
  $('modalPurchaseDate').readOnly = false;
  $('modalDocumentation').readOnly = false;
  $('modalShop').classList.remove('readonly');
  $('modalPurchaseDate').classList.remove('readonly');
  $('modalDocumentation').classList.remove('readonly');

  const modalTitle = $('modalTitle');
  if (modalTitle) modalTitle.textContent = '✏️ Edit Item';

  const uploadSection = qs('.upload-select-section');
  if (uploadSection) uploadSection.style.display = 'none';

  $('modalItemsPreview').style.display = 'none';
  $('ocrModal').style.display = 'flex';
}

async function deleteItem(itemId) {
  const item = allData.items.find(i => i.id === itemId);
  if (!item) { alert('Item not found'); return; }

  const itemsInGroup = allData.items.filter(i => i.receipt_group_id === item.receipt_group_id);
  const receipt = allData.receipts.find(r => r.receipt_group_id === item.receipt_group_id);
  const hasFile = !!(receipt && receipt.receipt_relative_path);

  let msg;
  if (itemsInGroup.length === 1) {
    if (hasFile) {
      msg =
        `⚠️  PERMANENT DELETE — please read carefully!\n\n` +
        `You are about to delete:\n` +
        `  • Record  : ID ${itemId} (${item.brand || 'N/A'} ${item.model || 'N/A'})\n` +
        `  • File    : ${receipt.receipt_filename || receipt.receipt_relative_path}\n\n` +
        `The receipt FILE WILL BE DELETED from disk.\n` +
        `This action cannot be undone.\n\n` +
        `Continue?`;
    } else {
      msg =
        `⚠️  PERMANENT DELETE\n\n` +
        `You are about to delete record ID ${itemId}.\n` +
        `No file is associated with this record.\n\n` +
        `Continue?`;
    }
  } else {
    msg =
      `⚠️  DELETE RECORD\n\n` +
      `You are about to delete record ID ${itemId}.\n\n` +
      `ℹ️  The receipt file will NOT be deleted — it is shared\n` +
      `with ${itemsInGroup.length - 1} other item(s) in group ${item.receipt_group_id}.\n\n` +
      `Continue?`;
  }

  if (!confirm(msg)) return;

  try {
    const resp = await fetchJson(API.deleteItem(itemId), { method: 'DELETE' });
    if (!resp.success) { alert(`Delete failed: ${resp.error || 'Unknown error'}`); return; }
    await loadData();
    await loadSuggestions();
  } catch (err) {
    console.error('Delete error:', err);
    alert(`Delete failed: ${err.message}`);
  }
}

function openFile(filePath) {
  if (!filePath) return;
  window.open(API.fileUrl(filePath), '_blank');
}

// Event delegation for table actions
function handleTableClick(e) {
  const button = e.target.closest('button[data-action]');
  if (!button) return;
  
  const action = button.dataset.action;
  const row = button.closest('tr');
  const itemId = parseInt(row?.dataset.itemId);
  
  if (!itemId) return;
  
  switch (action) {
    case 'edit':
      editItem(itemId);
      break;
    case 'delete':
      deleteItem(itemId);
      break;
    case 'open':
      const filePath = button.dataset.filePath;
      openFile(filePath);
      break;
  }
}

function setupEventListeners() {
  ['dragenter','dragover','dragleave','drop'].forEach(ev =>
    window.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); }, false)
  );

  const modalDropZone = $('modalDropZone');
  const modalFileInput = $('modalFileInput');
  if (modalDropZone && modalFileInput) {
    const browseLink = modalDropZone.querySelector('.browse-link');
    if (browseLink) browseLink.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); modalFileInput.click(); });
    modalDropZone.addEventListener('click', e => { if (!e.target.classList.contains('browse-link')) modalFileInput.click(); });
    modalDropZone.addEventListener('dragover', () => modalDropZone.classList.add('drag-over'));
    modalDropZone.addEventListener('dragleave', () => modalDropZone.classList.remove('drag-over'));
    modalDropZone.addEventListener('drop', e => { 
      modalDropZone.classList.remove('drag-over'); 
      const f = e.dataTransfer?.files?.[0]; 
      if (f) {
        $('existingReceiptSelect').value = '';
        handleFile(f); 
      }
    });
    modalFileInput.addEventListener('change', e => { 
      const f = e.target.files?.[0]; 
      if (f) {
        $('existingReceiptSelect').value = '';
        handleFile(f); 
      }
    });
  }

  bind('existingReceiptSelect', 'change', handleExistingReceiptSelect);

  const userTagInput = $('userTagInput');
  if (userTagInput) {
    userTagInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        const value = userTagInput.value.trim();
        if (value) addUserTag(value);
      }
    });
  }

  // RM-77: Extended warranty checkbox toggle
  const extWarrantyCheckbox = $('extendedWarrantyCheckbox');
  if (extWarrantyCheckbox) {
    extWarrantyCheckbox.addEventListener('change', e => {
      const fields = $('extendedWarrantyFields');
      if (fields) {
        if (e.target.checked) {
          fields.classList.remove('hidden');
        } else {
          fields.classList.add('hidden');
        }
      }
    });
  }

  // Event delegation for table row actions
  const itemsTable = $('itemsTable');
  if (itemsTable) {
    itemsTable.addEventListener('click', handleTableClick);
  }

  // RM-80: Menu modal event handlers
  bind('menuBtn', 'click', openMenuModal);
  bind('closeMenuModal', 'click', closeMenuModal);
  bind('closeMenuModalBtn', 'click', closeMenuModal);
  
  // Menu modal backdrop close
  const menuModal = $('menuModal');
  if (menuModal) {
    menuModal.addEventListener('click', e => {
      if (e.target === menuModal) closeMenuModal();
    });
  }
  
  // Location change handlers
  bind('changeLocationBtn', 'click', () => {
    openLocationModal();
  });
  bind('closeLocationModal', 'click', closeLocationModal);
  bind('cancelLocationChange', 'click', closeLocationModal);
  bind('applyLocationChange', 'click', applyLocationChange);
  
  // Location modal backdrop close
  const locationModal = $('locationModal');
  if (locationModal) {
    locationModal.addEventListener('click', e => {
      if (e.target === locationModal) closeLocationModal();
    });
  }
  
  // Menu action buttons
  bind('menuBackupBtn', 'click', () => { exportJson(); });
  bind('menuRestoreBtn', 'click', () => { $('importInput')?.click(); });
  bind('menuExportBtn', 'click', () => { exportCsv(); });

  bind('addReceiptBtn', 'click', openNewReceiptModal);
  bind('searchInput', 'input', filterAndRender);
  bind('projectFilter', 'change', filterAndRender);
  bind('statusFilter', 'change', filterAndRender);
  bind('userFilter', 'change', filterAndRender);
  bind('refreshBtn', 'click', () => { loadData(); loadSuggestions(); });
  bind('importInput', 'change', handleImport);
  bind('recheckBtn', 'click', recheckIntegrity);
  bind('closeBannerBtn', 'click', () => { const b = $('integrityBanner'); if (b) b.style.display = 'none'; });
  bind('columnToggleBtn', 'click', () => { const p = $('columnPanel'); if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none'; });
  bind('closeColumnPanel', 'click', () => { const p = $('columnPanel'); if (p) p.style.display = 'none'; });
  bind('closeModal', 'click', closeOcrModal);
  bind('cancelModal', 'click', closeOcrModal);
  bind('ocrForm', 'submit', saveOcrData);

  const modal = $('ocrModal');
  if (modal) modal.addEventListener('click', e => { if (e.target === modal) closeOcrModal(); });

  qsa('.col-toggle').forEach(t => t.addEventListener('change', e => {
    const col = e.target.dataset.column; if (!col) return;
    if (e.target.checked) visibleColumns.add(col); else visibleColumns.delete(col);
    updateColumnVisibility();
  }));

  qsa('th.sortable').forEach(th => th.addEventListener('click', () => {
    const col = th.dataset.column; if (!col) return;
    if (currentSort.column === col) currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    else { currentSort.column = col; currentSort.direction = 'asc'; }
    updateSortIndicators(); filterAndRender();
  }));

  window.addEventListener('languageChanged', () => {
    filterAndRender();
    populateFilterDropdowns();
  });
}

function initApp() {
  console.log('[app] Initializing application');
  updateUI();
  loadData(); 
  loadSuggestions(); 
  setupEventListeners();
  
  // RM-80: Set app version
  const versionEl = $('appVersion');
  if (versionEl) versionEl.textContent = '1.0.0';
}

let domReady = false;
let i18nextReady = false;

function tryInitApp() {
  if (domReady && i18nextReady) {
    initApp();
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('[app] DOM ready');
    domReady = true;
    tryInitApp();
  });
} else {
  console.log('[app] DOM already ready');
  domReady = true;
}

window.addEventListener('i18nextReady', () => {
  console.log('[app] i18next ready');
  i18nextReady = true;
  tryInitApp();
});

setTimeout(() => {
  if (!i18nextReady) {
    console.warn('[app] i18next timeout, initializing anyway');
    i18nextReady = true;
    tryInitApp();
  }
}, 2000);