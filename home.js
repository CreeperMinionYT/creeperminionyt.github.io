/* =============================================================
   HOMEPAGE VIDEO CARDS
   Edit content/latest-videos.json to change the displayed videos.
   A scheduled GitHub Action will refresh that JSON automatically.
   YouTube's actual player loads only after someone presses Play.
   ============================================================= */
(() => {
  'use strict';
  const FALLBACK = {
    featured: { id: 'Bs9qGUM0R7U', title: 'C25 Review Video', type: 'featured' },
    shorts: [
      { id: 'UnW7HUaMybI', title: 'AK47 Build' },
      { id: 'yydeKXlapq0', title: 'Insane Automag III Build' }
    ]
  };
  const validId = value => typeof value === 'string' && /^[A-Za-z0-9_-]{11}$/.test(value);
  const videos = new Map();
  function setCard(slot, entry, isShort) {
    if (!entry || !validId(entry.id)) return;
    const id = entry.id;
    const title = typeof entry.title === 'string' && entry.title.trim() ? entry.title.trim() : 'Watch on YouTube';
    videos.set(slot, id);
    const thumb = document.getElementById(`${slot}-thumb`);
    const headline = document.getElementById(`${slot}-title`);
    const link = document.getElementById(`${slot}-link`);
    if (headline) headline.textContent = title;
    if (thumb) {
      // maxresdefault is not guaranteed; hqdefault is available for most videos.
      thumb.src = `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
      thumb.alt = `${title} thumbnail`;
    }
    if (link) link.href = isShort ? `https://www.youtube.com/shorts/${id}` : `https://www.youtube.com/watch?v=${id}`;
    if (slot === 'featured') {
      const typeEl = document.getElementById('featured-type');
      if (typeEl) typeEl.textContent = entry.type === 'video' ? 'LATEST VIDEO' : entry.type === 'upload' ? 'LATEST UPLOAD' : 'FEATURED VIDEO';
    }
  }
  function applyFeed(data) {
    setCard('featured', data?.featured || FALLBACK.featured, false);
    const shorts = Array.isArray(data?.shorts) ? data.shorts : FALLBACK.shorts;
    setCard('short-1', shorts[0] || FALLBACK.shorts[0], true);
    setCard('short-2', shorts[1] || FALLBACK.shorts[1], true);
  }
  // Attach Play once: reveal the official privacy-enhanced YouTube iframe.
  document.querySelectorAll('[data-play]').forEach(button => {
    button.addEventListener('click', () => {
      const id = videos.get(button.dataset.play);
      if (!validId(id)) return;
      const media = button.closest('.home-media');
      if (!media) return;
      const iframe = document.createElement('iframe');
      iframe.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`;
      iframe.title = 'YouTube video player';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      iframe.allowFullscreen = true;
      iframe.referrerPolicy = 'strict-origin-when-cross-origin';
      media.replaceChildren(iframe);
    });
  });
  applyFeed(FALLBACK);
  fetch('content/latest-videos.json', { cache: 'no-cache' })
    .then(r => { if (!r.ok) throw new Error(`Feed HTTP ${r.status}`); return r.json(); })
    .then(applyFeed)
    .catch(e => console.warn('Using fallback video cards:', e));
})();
