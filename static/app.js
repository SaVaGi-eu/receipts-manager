    let currentLanguage = localStorage.getItem('preferredLanguage') || 'en';

    function t(key, params = {}) {
      let text = translations[currentLanguage]?.[key] || translations['en'][key] || key;
      Object.keys(params).forEach(param => {
        text = text.replace(`{${param}}`, params[param]);
      });
      return text;
    }

    function updateUI() {
      // Update all elements with data-i18n attribute
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (el.tagName === 'INPUT' && el.type !== 'button' && el.type !== 'submit') {
          return; // Skip input fields text content
        }
        el.textContent = t(key);
      });

      // Update placeholders
      document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        el.placeholder = t(key);
      });

      // Update item count
      const count = allData.items?.length || 0;
      const itemCountEl = document.getElementById('itemCount');
      if (itemCountEl) {
        itemCountEl.textContent = t('itemCount', { count });
      }

      // Update buttons in table
      document.querySelectorAll('.btn-edit').forEach(btn => btn.textContent = t('edit'));
      document.querySelectorAll('.btn-delete').forEach(btn => btn.textContent = t('delete'));
    }

    function changeLanguage(lang) {
      currentLanguage = lang;
      localStorage.setItem('preferredLanguage', lang);
      updateUI();
    }

    // Initialize language selector
    document.getElementById('languageSelect').value = currentLanguage;
    document.getElementById('languageSelect').addEventListener('change', (e) => {
      changeLanguage(e.target.value);
    });

    // ===== Original Application Logic =====
    let allData = { receipts: [], items: [], next_id: 1, integrity_issues: [] };
    let suggestions = { shops: [], brands: [], models: [], locations: [], documentation: [], projects: [], users: [] };
    let currentSort = { column: 'id', direction: 'asc' };
    let visibleColumns = new Set([
      'id', 'receipt_group_id', 'brand', 'model', 'location', 'users',
      'project', 'shop', 'purchase_date', 'documentation', 'guarantee_end_date', 'file', 'actions'
    ]);

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
          if ($('integrityMessage'))
            $('integrityMessage').textContent = issues.length > 0 ? t('integrityIssues', { count: issues.length }) : '';
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
    }

    function populateFilterDropdowns() {
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
            r.id, r.receipt_group_id, r.brand, r.model, r.location, r.project,
            r.shop, r.purchase_date, r.documentation, r.guarantee_end_date,
            normalizeUsers(r.users).join('; '), r.file
          ].map(x => String(x || '').toLowerCase()).join(' | ');
          if (!hay.includes(q)) return false;
        }
        return true;
      });
    }

    function sortRows(rows) {
      const col = currentSort.column;
      const dir = currentSort.direction === 'desc' ? -1 : 1;
      return [...rows].sort((a, b) => String(a?.[col] ?? '').localeCompare(String(b?.[col] ?? '')) * dir);
    }

    function buildRows() {
      const rmap = receiptMap();
      return (allData.items || []).map(it => {
        const r = rmap.get(it.receipt_group_id) || {};
        return {
          id: it.id, receipt_group_id: it.receipt_group_id,
          brand: it.brand || '', model: it.model || '', location: it.location || '',
          users: it.users || [], project: it.project || '',
          shop: r.shop || '', purchase_date: r.purchase_date || '',
          documentation: r.documentation || '', guarantee_end_date: it.guarantee_end_date || '',
          file: r.receipt_filename || it.receipt_relative_path || '',
          receipt_relative_path: r.receipt_relative_path || it.receipt_relative_path || ''
        };
      });
    }

    function renderTable(rows) {
      const tbody = $('tableBody');
      if (!tbody) return;
      if (!rows || rows.length === 0) {
        tbody.innerHTML = `<tr class="empty-state"><td colspan="13"><div class="empty-message"><span class="empty-icon">📦</span><p>${t('noItems')}</p></div></td></tr>`;
        if ($('itemCount')) $('itemCount').textContent = t('itemCount', { count: 0 });
        return;
      }
      tbody.innerHTML = rows.map(r => {
        const fileCell = r.receipt_relative_path
          ? `<a href="${API.fileUrl(r.receipt_relative_path)}" target="_blank" class="file-link" title="${r.receipt_relative_path}">${r.file || r.receipt_relative_path}</a>`
          : (r.file ? r.file : '');

        return `
        <tr>
          <td data-column="id">${r.id ?? ''}</td>
          <td data-column="receipt_group_id">${r.receipt_group_id ?? ''}</td>
          <td data-column="brand">${r.brand ?? ''}</td>
          <td data-column="model">${r.model ?? ''}</td>
          <td data-column="location">${r.location ?? ''}</td>
          <td data-column="users">${normalizeUsers(r.users).join('; ')}</td>
          <td data-column="project">${r.project ?? ''}</td>
          <td data-column="shop">${r.shop ?? ''}</td>
          <td data-column="purchase_date">${r.purchase_date ?? ''}</td>
          <td data-column="documentation">${r.documentation ?? ''}</td>
          <td data-column="guarantee_end_date">${r.guarantee_end_date ?? ''}</td>
          <td data-column="file">${fileCell}</td>
          <td data-column="actions">
            <button type="button" class="btn-small btn-edit" onclick="editItem(${r.id})">${t('edit')}</button>
            <button type="button" class="btn-small btn-delete" onclick="deleteItem(${r.id})">${t('delete')}</button>
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
        showOcrModal(result);
      } catch (err) { console.error('Upload error:', err); alert(`Upload failed: ${err.message}`); }
      finally { const fi = $('fileInput'); if (fi) fi.value = ''; }
    }

    function showOcrModal(uploadResult) {
      const modal = $('ocrModal'); if (!modal) return;
      const ocr = uploadResult.ocr_data || {};
      $('modalItemId').value         = uploadResult.item_id;
      $('modalReceiptGroupId').value = uploadResult.receipt_group_id;
      $('modalShop').value           = ocr.shop || '';
      const pd = ocr.purchase_date || '';
      if (pd && pd !== 'N/A') {
        try { $('modalPurchaseDate').value = new Date(pd.replace(/-/g, ' ')).toISOString().split('T')[0]; }
        catch { $('modalPurchaseDate').value = ''; }
      }
      $('modalWarranty').value = '';
      $('modalBrand').value = ''; $('modalModel').value = ''; $('modalLocation').value = '';
      $('modalProject').value = ''; $('modalDocumentation').value = ''; $('modalUsers').value = '';
      const itemsPreview = $('modalItemsPreview');
      const itemsList    = $('modalItemsList');
      if (ocr.items && ocr.items.length > 0) {
        itemsList.innerHTML = ocr.items.map(i => `<li>${i.name} - ${i.price}</li>`).join('');
        itemsPreview.style.display = 'block';
      } else { itemsPreview.style.display = 'none'; }
      modal.style.display = 'flex';
    }

    function closeOcrModal() {
      const modal = $('ocrModal');
      if (modal) { modal.style.display = 'none'; $('ocrForm').reset(); }
    }

    async function saveOcrData(e) {
      e.preventDefault();
      const itemId         = parseInt($('modalItemId').value);
      const receiptGroupId = $('modalReceiptGroupId').value;
      if (!itemId || !receiptGroupId) { alert('Invalid item or receipt ID'); return; }

      const shop          = $('modalShop').value.trim();
      const purchaseDate  = $('modalPurchaseDate').value;
      const warranty      = parseInt($('modalWarranty').value) || 0;
      const brand         = $('modalBrand').value.trim()         || 'N/A';
      const model         = $('modalModel').value.trim()         || 'N/A';
      const location      = $('modalLocation').value.trim()      || 'N/A';
      const project       = $('modalProject').value.trim()       || 'N/A';
      const documentation = $('modalDocumentation').value.trim() || 'N/A';
      const usersInput    = $('modalUsers').value.trim();
      const users         = usersInput ? usersInput.split(',').map(u => u.trim()).filter(Boolean) : [];

      if (!shop || !purchaseDate) { alert('Shop and Purchase Date are required'); return; }

      let formattedDate = purchaseDate;
      try {
        const d = new Date(purchaseDate + 'T00:00:00');
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        formattedDate = `${d.getFullYear()}-${months[d.getMonth()]}-${String(d.getDate()).padStart(2,'0')}`;
      } catch { /* keep original */ }

      try {
        const resp = await fetchJson(API.updateItem(itemId), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            shop,
            purchase_date: formattedDate,
            brand,
            model,
            location,
            project,
            documentation,
            users,
            guarantee_duration: warranty,
            guarantee_unit: 'months'
          })
        });
        if (!resp.success) { alert(`Save failed: ${resp.error || 'Unknown error'}`); return; }
        closeOcrModal();
        await loadData(); await loadSuggestions();
      } catch (err) { console.error('Save error:', err); alert(`Save failed: ${err.message}`); }
    }

    async function editItem(itemId) {
      const item = allData.items.find(i => i.id === itemId);
      if (!item) { alert('Item not found'); return; }
      const receipt = allData.receipts.find(r => r.receipt_group_id === item.receipt_group_id);
      if (!receipt) { alert('Receipt not found'); return; }

      $('modalItemId').value         = item.id;
      $('modalReceiptGroupId').value = item.receipt_group_id;
      $('modalShop').value           = receipt.shop          !== 'N/A' ? receipt.shop          : '';
      $('modalBrand').value          = item.brand            !== 'N/A' ? item.brand            : '';
      $('modalModel').value          = item.model            !== 'N/A' ? item.model            : '';
      $('modalLocation').value       = item.location         !== 'N/A' ? item.location         : '';
      $('modalProject').value        = item.project          !== 'N/A' ? item.project          : '';
      $('modalDocumentation').value  = receipt.documentation !== 'N/A' ? receipt.documentation : '';
      $('modalUsers').value          = (item.users || []).join(', ');

      const warranty = item.guarantee_unit === 'months' ? (item.guarantee_duration || 0) : 0;
      $('modalWarranty').value = warranty > 0 ? warranty : '';

      const pd = receipt.purchase_date || '';
      if (pd && pd !== 'N/A') {
        try { $('modalPurchaseDate').value = new Date(pd.replace(/-/g, ' ')).toISOString().split('T')[0]; }
        catch { $('modalPurchaseDate').value = ''; }
      } else { $('modalPurchaseDate').value = ''; }

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

    // Make functions globally accessible
    window.editItem = editItem;
    window.deleteItem = deleteItem;

    function setupEventListeners() {
      ['dragenter','dragover','dragleave','drop'].forEach(ev =>
        window.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); }, false)
      );

      const dropZone  = $('dropZone');
      const fileInput = $('fileInput');
      if (dropZone && fileInput) {
        const browseLink = qs('.browse-link');
        if (browseLink) browseLink.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); fileInput.click(); });
        dropZone.addEventListener('click',     e => { if (!e.target.classList.contains('browse-link')) fileInput.click(); });
        dropZone.addEventListener('dragover',  () => dropZone.classList.add('drag-over'));
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop',      e => { dropZone.classList.remove('drag-over'); const f = e.dataTransfer?.files?.[0]; if (f) handleFile(f); });
        fileInput.addEventListener('change',   e => { const f = e.target.files?.[0]; if (f) handleFile(f); });
      }

      bind('searchInput',   'input',  filterAndRender);
      bind('projectFilter', 'change', filterAndRender);
      bind('statusFilter',  'change', filterAndRender);
      bind('userFilter',    'change', filterAndRender);
      bind('refreshBtn',    'click',  () => { loadData(); loadSuggestions(); });
      bind('exportJsonBtn', 'click',  exportJson);
      bind('exportCsvBtn',  'click',  exportCsv);
      bind('importBtn',     'click',  () => $('importInput')?.click());
      bind('importInput',   'change', handleImport);
      bind('recheckBtn',    'click',  recheckIntegrity);
      bind('closeBannerBtn','click',  () => { const b = $('integrityBanner'); if (b) b.style.display = 'none'; });
      bind('columnToggleBtn','click', () => { const p = $('columnPanel'); if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none'; });
      bind('closeColumnPanel','click',() => { const p = $('columnPanel'); if (p) p.style.display = 'none'; });

      bind('closeModal',  'click',  closeOcrModal);
      bind('cancelModal', 'click',  closeOcrModal);
      bind('ocrForm',     'submit', saveOcrData);

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
    }

    document.addEventListener('DOMContentLoaded', () => {
      updateUI();
      loadData(); loadSuggestions(); setupEventListeners();
    });
