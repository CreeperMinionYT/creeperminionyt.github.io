/* ================================================================
   OPTIONAL ARMORY DATABASE BRIDGE — no edits to existing script.js.
   When the selected armory gun has an entry in weapon-stats.json, add
   a "View Weapon Statistics" link to the existing resource panel.
   The website's master stats file remains the single numeric source.
   ================================================================ */
(() => {
  'use strict';
  const panel = document.getElementById('panel');
  const title = document.getElementById('panel-title');
  const statsList = document.getElementById('stats');
  if (!panel || !title || !statsList) return;
  const ids = new Set();
  const idFromName = name => String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
  let loaded = false;
  const update = () => {
    if (!loaded || panel.hidden) return;
    const id = idFromName(title.textContent);
    // Remove only the link inserted by this bridge. Leave the user's popup intact.
    statsList.querySelector('.cm-database-link')?.remove();
    if (!ids.has(id)) return;
    // Add a normal link using the popup's existing CSS classes.
    const link = document.createElement('a');
    link.className = 'resource cm-database-link';
    link.href = `/statistics/?weapon=${encodeURIComponent(id)}`;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    const content = document.createElement('span'); content.className = 'resource-content';
    const heading = document.createElement('span'); heading.className = 'resource-title';
    heading.textContent = 'View weapon statistics';
    content.append(heading); link.append(content);
    const arrow = document.createElement('span'); arrow.className = 'resource-arrow'; arrow.textContent = '↗';
    link.append(arrow);
    const placeholder = statsList.querySelector('.empty');
    if (placeholder && statsList.children.length === 1) placeholder.remove();
    statsList.prepend(link);
  };
  // Original armory modifies the title and then opens panel synchronously.
  // MutationObserver runs afterward, once it has finished redrawing resources.
  const observer = new MutationObserver(update);
  observer.observe(title, {childList: true, characterData:true, subtree:true});
  observer.observe(panel, {attributes: true, attributeFilter: ['hidden']});
  fetch('/content/weapon-stats.json', {cache: 'no-cache'})
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
    .then(data => { (data.weapons || []).forEach(w => ids.add(w.id)); loaded=true; update(); })
    .catch(error => console.warn('Optional armory stats link unavailable:', error));
})();
