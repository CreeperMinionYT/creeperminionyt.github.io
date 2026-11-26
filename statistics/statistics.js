/* ================================================================
   CREEPERMINION / SORTABLE WEAPON STATISTICS
   Main data source: /content/weapon-stats.json (one per gun).
   Reads /weapons.json ONLY for optional already-made art and armory links.
   To edit source statistics, update Google Sheet and reimport JSON.
   ================================================================ */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const search = $('stats-search');
  const slotSelect = $('stats-slot');
  const classSelect = $('stats-class');
  const referenceSelect = $('stats-reference');
  const head = $('stats-head');
  const body = $('stats-body');
  const count = $('stats-count');
  const dialog = $('stats-notes');
  const dialogTitle = $('stats-dialog-title');
  const dialogMeta = $('stats-dialog-meta');
  const dialogBody = $('stats-dialog-body');
  const dialogLinks = $('stats-dialog-links');
  const close = $('stats-notes-close');
  const state = { rows: [], columns: [], art: new Map(), sortKey: 'weapon', descending: false };
  const normId = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
  const colByKey = key => state.columns.find(c => c.key === key);
  const numeric = value => {
    // Sort '1.93s' as 1.93 and '1.4x' as 1.4; blank is not zero.
    if (value === null || value === undefined || String(value).trim() === '') return null;
    const num = Number(String(value).replaceAll(',', '').match(/^\s*([-+]?\d+(?:\.\d+)?)/)?.[1]);
    return Number.isFinite(num) ? num : null;
  };
  const display = val => val === null || val === undefined || val === '' ? '—' : String(val);
  const create = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  };

  function setOptions(select, choices) {
    for (const choice of [...new Set(choices.filter(Boolean))].sort((a,b)=>a.localeCompare(b))) {
      const opt = document.createElement('option'); opt.value = choice; opt.textContent = choice;
      select.append(opt);
    }
  }
  function sortRows(rows) {
    const key = state.sortKey;
    const col = colByKey(key);
    const isNum = col?.type === 'number';
    const multiplier = state.descending ? -1 : 1;
    return [...rows].sort((a, b) => {
      const a0 = a[key], b0 = b[key];
      const av = isNum ? numeric(a0) : (a0 == null ? null : String(a0));
      const bv = isNum ? numeric(b0) : (b0 == null ? null : String(b0));
      if (av == null && bv == null) return a.weapon.localeCompare(b.weapon);
      if (av == null) return 1;
      if (bv == null) return -1;
      const compare = isNum ? av - bv : av.localeCompare(bv, undefined, {numeric:true, sensitivity:'base'});
      return compare * multiplier || a.weapon.localeCompare(b.weapon);
    });
  }
  function filteredRows() {
    const query = search.value.trim().toLowerCase();
    return state.rows.filter(w =>
      (!query || w.weapon.toLowerCase().includes(query)) &&
      (!slotSelect.value || w.slot === slotSelect.value) &&
      (!classSelect.value || w.class === classSelect.value)
    );
  }
  function referenceStats(row, key) {
    if (referenceSelect.value === 'none') return null;
    // Compare to ALL canonical rows, not the user-filtered subset. Filters don't change colors.
    const group = state.rows.filter(w => referenceSelect.value === 'all' || (w.class === row.class && w.slot === row.slot));
    const vals = group.map(w => numeric(w[key])).filter(v => v !== null);
    if (vals.length < 2) return null;
    const average = vals.reduce((sum, v) => sum + v, 0) / vals.length;
    const squared = vals.reduce((sum, v) => sum + (v - average) ** 2, 0) / vals.length;
    const spread = Math.sqrt(squared);
    return { average, spread, n: vals.length };
  }
  function heatmap(row, column, element) {
    if (!column.heatmap) return;
    const value = numeric(row[column.key]);
    const summary = referenceStats(row, column.key);
    if (value === null || !summary || summary.spread === 0) return;
    // Standardized against peer values, with a muted red/green scale.
    const z = Math.max(-2, Math.min(2, (value - summary.average) / summary.spread)) * (column.better === 'lower' ? -1 : 1);
    const intensity = Math.round(11 + Math.abs(z) / 2 * 42);
    element.style.backgroundColor = z >= 0 ? `hsl(155 46% ${intensity * .48 + 12}% / .58)` : `hsl(3 47% ${intensity * .46 + 12}% / .62)`;
    const delta = summary.average ? ((value - summary.average) / Math.abs(summary.average) * 100) : 0;
    element.title = `${Math.abs(delta).toFixed(1)}% ${delta >= 0 ? 'above' : 'below'} reference mean (${summary.n} weapons). ${column.better === 'lower' ? 'Lower is favorable.' : 'Higher is favorable for this raw metric.'}`;
  }
  function openNotes(row) {
    dialogTitle.textContent = row.weapon;
    dialogMeta.textContent = `${row.slot || 'Unclassified'} · ${row.class || 'Unclassified'} · Rank ${display(row.unlock_rank)}`;
    dialogBody.textContent = row.notes?.trim() || 'No notes have been added to the master spreadsheet for this weapon yet.';
    dialogBody.classList.toggle('is-empty', !row.notes?.trim());
    dialogLinks.replaceChildren();
    const art = state.art.get(row.id);
    if (art) {
      const link = create('a', '', 'Find in Armory ↗');
      link.href = `/armory/?weapon=${encodeURIComponent(art.id)}`;
      dialogLinks.append(link);
    }
    // Deep link lets a future comparison/build page open the same note panel.
    const u = new URL(location.href); u.searchParams.set('weapon', row.id);
    history.replaceState(null, '', u);
    dialog.showModal();
  }
  function renderHead() {
    const tr = document.createElement('tr');
    for (const col of state.columns) {
      const th = document.createElement('th'); th.scope = 'col';
      th.setAttribute('aria-sort', col.key !== state.sortKey ? 'none' : state.descending ? 'descending' : 'ascending');
      const button = create('button'); button.type = 'button';
      button.setAttribute('aria-label', `Sort by ${col.label}`);
      button.append(document.createTextNode(col.label));
      if (col.key === state.sortKey) button.append(create('span','stats-sort-mark',state.descending?'▼':'▲'));
      button.addEventListener('click', () => {
        state.descending = state.sortKey === col.key ? !state.descending : (col.type === 'number');
        state.sortKey = col.key;
        render();
      });
      th.append(button); tr.append(th);
    }
    head.replaceChildren(tr);
  }
  function render() {
    renderHead();
    const rows = sortRows(filteredRows());
    count.textContent = `${rows.length} of ${state.rows.length} weapons`;
    const frag = document.createDocumentFragment();
    if (!rows.length) {
      const tr = document.createElement('tr'); const td = create('td','','No matching weapons.'); td.colSpan = state.columns.length; tr.append(td); frag.append(tr);
    }
    for (const row of rows) {
      const tr = document.createElement('tr');
      for (const col of state.columns) {
        const td = document.createElement('td');
        const val = row[col.key];
        if (col.key === 'weapon') {
          const button = create('button','stats-name-link',row.weapon); button.type='button';
          button.setAttribute('aria-label',`Open notes for ${row.weapon}`);
          button.addEventListener('click', () => openNotes(row)); td.append(button);
        } else if (col.type === 'image') {
          const source = row.thumbnail || state.art.get(row.id)?.image;
          if (typeof source === 'string' && (/^https:\/\//i.test(source) || /^(?:assets\/|\/assets\/)/.test(source))) {
            const img = create('img','stats-image'); img.src = source; img.alt = `${row.weapon} illustration`;
            img.loading='lazy'; img.addEventListener('error',()=>img.replaceWith(create('span','stats-image-fallback','◇')));
            td.append(img);
          } else td.append(create('span','stats-image-fallback','◇'));
        } else if (col.key === 'rating') {
          // Independent subjective rating. Gold stars, not the class-relative heatmap.
          // Numeric sorting works because this column's type is 'number'.
          const rating = numeric(val);
          td.className = 'stats-rating-cell';
          if (Number.isInteger(rating) && rating >= 1 && rating <= 3) {
            const stars = create('span', 'stats-star-rating', '★'.repeat(rating));
            stars.title = `${rating} out of 3 stars`;
            stars.setAttribute('aria-label', stars.title);
            td.append(stars);
          } else {
            td.append(create('span', 'stats-unrated', '—'));
          }
        } else if (col.type === 'number') {
          td.className='stats-number';
          const span = create('span','stats-value',display(val)); heatmap(row,col,span); td.append(span);
        } else td.textContent=display(val);
        tr.append(td);
      }
      frag.append(tr);
    }
    body.replaceChildren(frag);
  }
  function closeNotes() {
    dialog.close();
  }
  close.addEventListener('click', closeNotes);
  dialog.addEventListener('click', event => { if (event.target === dialog) closeNotes(); });
  dialog.addEventListener('close', () => {
    const u = new URL(location.href); u.searchParams.delete('weapon');
    history.replaceState(null, '', u);
  });
  [search, slotSelect, classSelect, referenceSelect].forEach(input => input.addEventListener(input === search ? 'input' : 'change', render));
  async function initialize() {
    try {
      const response = await fetch('/content/weapon-stats.json', {cache:'no-cache'});
      if (!response.ok) throw new Error(`Database HTTP ${response.status}`);
      const data = await response.json();
      // Display a compact label without requiring a Google Sheet header rename.
      state.columns = (data.columns || []).map(col =>
        col.key === 'unlock_rank' ? { ...col, label: 'Unlock' } : col
      );
      // Show the Rating column even while waiting for the first sync of new data.
      // Once the importer has emitted it, reuse the imported column definition.
      if (!state.columns.some(col => col.key === 'rating')) {
        const ratingColumn = { key: 'rating', label: 'Rating', type: 'number', heatmap: false, better: 'higher' };
        const weaponIndex = state.columns.findIndex(col => col.key === 'weapon');
        state.columns.splice(weaponIndex + 1, 0, ratingColumn);
      }
      state.rows = data.weapons || [];
      if (!state.columns.length || !state.rows.length) throw new Error('No columns/weapon rows in master database');
      try {
        const armory = await fetch('/weapons.json', {cache:'no-cache'});
        if (armory.ok) {
          for (const w of (await armory.json()).weapons || []) {
            state.art.set(normId(w.id), w);
          }
        }
      } catch (error) { console.warn('Optional armory images unavailable:', error); }
      setOptions(slotSelect, state.rows.map(w => w.slot));
      setOptions(classSelect, state.rows.map(w => w.class));
      render();
      const sheetUrl = data.sheet_url;
      if (typeof sheetUrl === 'string' && /^https:\/\//.test(sheetUrl)) {
        const link = create('a','','View master Google Sheet ↗'); link.href=sheetUrl; link.target='_blank'; link.rel='noopener noreferrer';
        $('stats-source').append(link);
      }
      const requested = new URLSearchParams(location.search).get('weapon');
      const first = state.rows.find(w => w.id === normId(requested));
      if (first) openNotes(first);
    } catch (error) {
      console.error('Statistics database failed to load:', error);
      count.textContent = 'Statistics currently unavailable';
      body.replaceChildren(create('tr'));
      const td = create('td','',`Could not load the weapon database: ${error.message}`); td.colSpan=state.columns.length || 1;
      body.firstChild.append(td);
    }
  }
  initialize();
})();
