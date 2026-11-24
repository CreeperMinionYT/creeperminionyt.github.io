/* ================================================================
   CREEPERMINION — COLLAPSIBLE SITE NAVIGATION
   - Runs independently of the armory's script.js.
   - Add real pages by changing a "soon" item to an item with "href".
   - Home is now /, and the original armory is at /armory/.
   ================================================================ */
(() => {
  'use strict';
  // EDIT HERE: Sidebar items and their destinations.
  // "soon: true" displays an inactive placeholder, NOT a broken link.
  // When a page exists, replace "soon: true" with href: '/builds/' etc.
  const items = [
    { label: 'Home', href: '/' },
    { label: 'Armory', href: '/armory/' },
    { label: 'Builds', soon: true },
    { label: 'Tier Lists', soon: true },
    { label: 'Statistics', soon: true },
    { label: "What's New", soon: true }
  ];
  // EDIT HERE: Swap this destination if your YouTube channel URL changes.
  const channelUrl = 'https://www.youtube.com/@creeper_minion';
  const toggle = document.createElement('button');
  toggle.id = 'cm-menu-toggle';
  toggle.type = 'button';
  toggle.setAttribute('aria-label', 'Open navigation');
  toggle.setAttribute('aria-controls', 'cm-sidebar');
  toggle.setAttribute('aria-expanded', 'false');
  toggle.innerHTML = '<span class="cm-menu-bars" aria-hidden="true"><span></span><span></span><span></span></span>';

  const shade = document.createElement('div');
  shade.id = 'cm-nav-shade';
  shade.setAttribute('aria-hidden', 'true');
  const sidebar = document.createElement('aside');
  sidebar.id = 'cm-sidebar';
  sidebar.setAttribute('aria-label', 'Site navigation');
  sidebar.setAttribute('aria-hidden', 'true');
  sidebar.inert = true; // Hidden links are excluded from keyboard navigation.
  const brand = document.createElement('div');
  brand.className = 'cm-nav-brand';
  const brandName = document.createElement('strong');
  brandName.textContent = 'CREEPERMINION';
  const brandDetail = document.createElement('small');
  brandDetail.textContent = 'PHANTOM FORCES';
  brand.append(brandName, brandDetail);

  const nav = document.createElement('nav');
  nav.className = 'cm-nav-links';
  nav.setAttribute('aria-label', 'Pages');
  const currentPath = window.location.pathname.replace(/index\.html$/, '') || '/';
  for (const item of items) {
    let element;
    if (item.soon) {
      element = document.createElement('span');
      element.className = 'cm-nav-soon';
      element.textContent = item.label;
      const soon = document.createElement('em');
      soon.textContent = 'Soon';
      element.append(soon);
    } else {
      element = document.createElement('a');
      element.className = 'cm-nav-link';
      element.textContent = item.label;
      element.href = item.href;
      if (currentPath === item.href) element.setAttribute('aria-current', 'page');
      element.addEventListener('click', () => setOpen(false));
    }
    nav.append(element);
  }
  const footer = document.createElement('div');
  footer.className = 'cm-nav-footer';
  const channel = document.createElement('a');
  channel.className = 'cm-nav-link';
  channel.textContent = 'Watch on YouTube ↗';
  channel.href = channelUrl;
  channel.target = '_blank';
  channel.rel = 'noopener noreferrer';
  footer.append(channel);
  const logoLink = document.createElement('a');
  logoLink.className = 'cm-nav-logo';
  logoLink.href = channelUrl;
  logoLink.target = '_blank';
  logoLink.rel = 'noopener noreferrer';
  logoLink.setAttribute('aria-label', 'Visit CreeperMinion on YouTube');
  sidebar.append(brand, nav, footer, logoLink);
  document.body.append(toggle, shade, sidebar);
  function setOpen(open) {
    // Don't leave a gun popup open under the navigation overlay.
    // Clicking its existing close button preserves script.js behavior and URL state.
    if (open) {
      const infoPanel = document.getElementById('panel');
      if (infoPanel && !infoPanel.hidden) {
        document.getElementById('close')?.click();
      }
    }
    document.body.classList.toggle('cm-nav-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    sidebar.setAttribute('aria-hidden', String(!open));
    sidebar.inert = !open;
  }
  toggle.addEventListener('click', () => setOpen(!document.body.classList.contains('cm-nav-open')));
  shade.addEventListener('click', () => setOpen(false));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.body.classList.contains('cm-nav-open')) {
      setOpen(false);
      toggle.focus();
    }
  });
})();
