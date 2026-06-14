/* Muscles FW runtime */
// Feather Wiki — Muscles (JS runtime)
// Exposes the global FW object: FW.ready(), FW.state, FW.emitter, FW.html
//
// Extensions pattern:
//   FW.ready(() => {
//     const { state, emitter } = FW;
//     ['DOMContentLoaded','render'].forEach(ev => {
//       emitter.on(ev, () => { setTimeout(() => { myExt(); }, 50); });
//     });
//     emitter.emit('DOMContentLoaded');
//     function myExt() { /* DOM work after render */ }
//   });
(function () {
  'use strict';

  // ── Minimal event emitter ────────────────────────────────────────────
  function createEmitter() {
    const _l = {};
    return {
      on(ev, fn) { (_l[ev] = _l[ev] || []).push(fn); },
      off(ev, fn) { if (_l[ev]) _l[ev] = _l[ev].filter(f => f !== fn); },
      emit(ev, ...args) { (_l[ev] || []).forEach(fn => fn(...args)); }
    };
  }

  // ── nanohtml-like tagged template literal ───────────────────────────
  function html(strings, ...values) {
    const raw = strings.reduce((acc, s, i) => acc + (values[i - 1] ?? '') + s);
    const tpl = document.createElement('template');
    tpl.innerHTML = raw.trim();
    return tpl.content.firstChild;
  }

  // ── Parse URL query string ──────────────────────────────────────────
  function parseQuery() {
    const q = {};
    new URLSearchParams(window.location.search).forEach((v, k) => { q[k] = v; });
    return q;
  }

  // ── Short artifact ID (first 10 chars of UUID) ──────────────────────
  function shortId(uuid) {
    return (uuid || '').replace(/-/g, '').slice(0, 10);
  }

  // ── Relative time ────────────────────────────────────────────────────
  function relativeTime(isoDate) {
    const diff = Date.now() - new Date(isoDate).getTime();
    const mins  = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days  = Math.floor(diff / 86400000);
    if (mins  < 1)  return 'just now';
    if (mins  < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days  < 30) return `${days}d ago`;
    return new Date(isoDate).toLocaleDateString();
  }

  // ── Markdown → HTML ─────────────────────────────────────────────────
  function renderMarkdown(text) {
    let h = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    h = h.replace(/```[\w]*\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    h = h.replace(/^###### (.*)$/gm,'<h6>$1</h6>');
    h = h.replace(/^##### (.*)$/gm, '<h5>$1</h5>');
    h = h.replace(/^#### (.*)$/gm,  '<h4>$1</h4>');
    h = h.replace(/^### (.*)$/gm,   '<h3>$1</h3>');
    h = h.replace(/^## (.*)$/gm,    '<h2>$1</h2>');
    h = h.replace(/^# (.*)$/gm,     '<h1>$1</h1>');
    h = h.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\*(.*?)\*/g,     '<em>$1</em>');
    h = h.replace(/`(.*?)`/g,       '<code>$1</code>');
    h = h.replace(/^> (.*)$/gm,     '<blockquote>$1</blockquote>');
    h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    h = h.replace(/^[-*] (.*)$/gm,  '<li>$1</li>');
    h = h.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
    h = h.replace(/<\/ul>\s*<ul>/g, '');
    h = h.split('\n\n').map(p => {
      p = p.trim();
      if (!p || p.startsWith('<')) return p;
      return '<p>' + p.replace(/\n/g,'<br>') + '</p>';
    }).join('\n');
    return h;
  }

  // ── Render a single page card ────────────────────────────────────────
  function renderPageCard(page) {
    const body = page.type === 'text/html' ? page.content : renderMarkdown(page.content || '');
    const tags = (page.tags || []).map(t =>
      `<span class="fw-tag" data-tag="${t}">${t}</span>`).join('');
    const date = page.modified ? new Date(page.modified).toLocaleDateString() : '';
    return `
      <article class="fw-page" id="page-${page.slug}">
        <div class="fw-page-header">
          <span class="fw-page-title db" data-slug="${page.slug}">${page.title}</span>
          <div class="fw-page-meta">
            <span>${date}</span>
            <div class="fw-page-tags">${tags}</div>
          </div>
        </div>
        <div class="fw-page-body">${body}</div>
      </article>`;
  }

  // ── Views ────────────────────────────────────────────────────────────
  function renderStoryView(pages, query) {
    const slug = query.page;
    const toShow = slug ? pages.filter(p => p.slug === slug) : pages.slice(0, 5);
    if (!toShow.length)
      return '<p style="padding:2rem;color:var(--fw-muted)">No pages found.</p>';
    return toShow.map(renderPageCard).join('');
  }

  // ── Fossil-style timeline view ───────────────────────────────────────
  function renderTimelineView(timeline, pages) {
    if (!timeline.length)
      return '<p style="padding:2rem;color:var(--fw-muted)">No timeline entries.</p>';

    const sorted = timeline.slice().sort((a, b) =>
      new Date(b.date).getTime() - new Date(a.date).getTime());

    // Group by date for day headers
    const groups = {};
    sorted.forEach(e => {
      const day = new Date(e.date).toDateString();
      (groups[day] = groups[day] || []).push(e);
    });

    let html = '<div class="fw-fossil-timeline">';
    Object.entries(groups).forEach(([day, entries]) => {
      html += `<div class="fw-fossil-day-header">${day}</div>`;
      entries.forEach(e => {
        const sid     = shortId(e.uuid);
        const branch  = e.branch || 'trunk';
        const isTrunk = branch === 'trunk';
        const page    = e.pageSlug ? pages.find(p => p.slug === e.pageSlug) : null;
        html += `
          <div class="fw-fossil-entry" data-uuid="${e.uuid}">
            <div class="fw-fossil-spine">
              <div class="fw-fossil-line${isTrunk ? '' : ' fw-fossil-line-branch'}"></div>
              <div class="fw-fossil-dot${isTrunk ? '' : ' fw-fossil-dot-branch'}"></div>
              <div class="fw-fossil-line${isTrunk ? '' : ' fw-fossil-line-branch'}"></div>
            </div>
            <div class="fw-fossil-body">
              <div class="fw-fossil-meta">
                <code class="fw-artifact-id" data-uuid="${e.uuid}" title="${e.uuid}">${sid}</code>
                <span class="fw-branch-badge${isTrunk ? ' fw-branch-trunk' : ''}">${branch}</span>
                <span class="fw-fossil-user">${e.user}</span>
                <span class="fw-fossil-time">${relativeTime(e.date)}</span>
              </div>
              <div class="fw-fossil-comment">${e.comment}</div>
              ${page ? `<div class="fw-fossil-page-link" data-slug="${page.slug}">→ ${page.title}</div>` : ''}
              ${(e.tags || []).length ? `<div class="fw-fossil-tags">${e.tags.map(t=>`<span class="fw-tag">${t}</span>`).join('')}</div>` : ''}
            </div>
          </div>`;
      });
    });
    html += '</div>';
    return html;
  }

  function renderAllPages(pages) {
    return '<div class="fw-page-index">' + pages.map(p => `
      <div class="fw-index-card" data-slug="${p.slug}">
        <h4>${p.title}</h4>
        <div class="fw-excerpt">${p.content.replace(/[#*\`>]/g,'').slice(0,120)}…</div>
        <div class="fw-page-tags" style="margin-top:0.5rem">
          ${(p.tags||[]).map(t=>`<span class="fw-tag">${t}</span>`).join('')}
        </div>
        ${(p.history||[]).length ? `<div class="fw-page-checkin-count">${p.history.length} checkin${p.history.length!==1?'s':''}</div>` : ''}
      </div>`).join('') + '</div>';
  }

  // ── Sidebar helpers ──────────────────────────────────────────────────
  function renderTagCloud(pages) {
    const freq = {};
    pages.forEach(p => (p.tags||[]).forEach(t => { freq[t]=(freq[t]||0)+1; }));
    return Object.entries(freq).sort((a,b)=>b[1]-a[1])
      .map(([t])=>`<li data-tag="${t}">${t}</li>`).join('');
  }

  function renderRecentPages(pages) {
    return pages.slice().sort((a,b)=>
      new Date(b.modified).getTime()-new Date(a.modified).getTime()
    ).slice(0,6).map(p=>`<li data-slug="${p.slug}">${p.title}</li>`).join('');
  }

  // ── Main render ──────────────────────────────────────────────────────
  function render(FW) {
    const { state } = FW;
    const { manifest } = state;
    const mainEl = document.getElementById('fw-main');
    if (!mainEl) return;

    const view = state.query.view || 'story';
    document.querySelectorAll('.fw-nav-btn').forEach(btn =>
      btn.classList.toggle('active', btn.dataset.view === view));

    if (view === 'timeline')
      mainEl.innerHTML = renderTimelineView(manifest.timeline||[], manifest.pages||[]);
    else if (view === 'all')
      mainEl.innerHTML = renderAllPages(manifest.pages||[]);
    else
      mainEl.innerHTML = renderStoryView(manifest.pages||[], state.query);

    const tagList  = document.getElementById('fw-tag-list');
    const pageList = document.getElementById('fw-page-list');
    if (tagList)  tagList.innerHTML  = renderTagCloud(manifest.pages||[]);
    if (pageList) pageList.innerHTML = renderRecentPages(manifest.pages||[]);

    // Show manifest artifact info in sidebar
    const artEl = document.getElementById('fw-artifact-info');
    if (artEl && manifest.artifactId) {
      artEl.textContent = `artifact: ${shortId(manifest.artifactId)} · ${manifest.branch||'trunk'}`;
    }

    // Bind interactions
    mainEl.querySelectorAll('[data-slug]').forEach(el =>
      el.addEventListener('click', () => navigate(FW, { page: el.dataset.slug })));
    mainEl.querySelectorAll('[data-tag]').forEach(el =>
      el.addEventListener('click', () => filterByTag(FW, el.dataset.tag)));
    mainEl.querySelectorAll('.fw-fossil-page-link[data-slug]').forEach(el =>
      el.addEventListener('click', () => navigate(FW, { page: el.dataset.slug })));
    mainEl.querySelectorAll('.fw-artifact-id[data-uuid]').forEach(el =>
      el.addEventListener('click', () => showArtifact(FW, el.dataset.uuid)));
    document.querySelectorAll('#fw-tag-list [data-tag]').forEach(el =>
      el.addEventListener('click', () => filterByTag(FW, el.dataset.tag)));
    document.querySelectorAll('#fw-page-list [data-slug]').forEach(el =>
      el.addEventListener('click', () => navigate(FW, { page: el.dataset.slug })));
  }

  // ── Show page content at a specific checkin artifact ─────────────────
  function showArtifact(FW, uuid) {
    const entry = (FW.state.manifest.timeline||[]).find(e => e.uuid === uuid);
    if (!entry || !entry.pageSlug) return;
    const page = (FW.state.manifest.pages||[]).find(p => p.slug === entry.pageSlug);
    if (!page) return;
    // Find the version in page history
    const version = (page.history||[]).find(v => v.versionId === uuid);
    const content = version ? version.content : page.content;
    const mainEl  = document.getElementById('fw-main');
    if (!mainEl) return;
    const fakeVersion = { ...page, content, modified: entry.date };
    mainEl.innerHTML = `
      <div style="padding:1rem;background:var(--fw-bg-sidebar);border-bottom:1px solid var(--fw-border);margin-bottom:1rem;display:flex;gap:1rem;align-items:center;flex-wrap:wrap">
        <code style="font-size:0.8rem">artifact: ${shortId(uuid)}</code>
        <span class="fw-branch-badge">${entry.branch||'trunk'}</span>
        <span style="font-size:0.8rem;color:var(--fw-muted)">${new Date(entry.date).toLocaleString()}</span>
        <span style="font-size:0.8rem;color:var(--fw-muted)">${entry.comment}</span>
        <button onclick="FW.emitter.emit('render')" style="margin-left:auto;padding:0.25rem 0.6rem;border:1px solid var(--fw-border);border-radius:4px;background:var(--fw-bg-card);cursor:pointer;font-size:0.8rem">← Back to current</button>
      </div>
      ${renderPageCard(fakeVersion)}`;
  }

  // ── Navigation ───────────────────────────────────────────────────────
  function navigate(FW, params) {
    const qs = new URLSearchParams(params).toString();
    history.pushState({}, '', qs ? '?' + qs : window.location.pathname);
    FW.state.query = parseQuery();
    FW.emitter.emit('render');
  }

  function filterByTag(FW, tag) {
    const pages = (FW.state.manifest.pages||[]).filter(p=>(p.tags||[]).includes(tag));
    FW.state.query = { view: 'all', tag };
    FW.emitter.emit('render');
    const mainEl = document.getElementById('fw-main');
    if (mainEl) mainEl.innerHTML = renderAllPages(pages);
  }

  // ── Skins ────────────────────────────────────────────────────────────
  const SKINS = {
    default: {},
    dark: {
      '--fw-bg':'#1a202c','--fw-bg-card':'#2d3748','--fw-bg-sidebar':'#171e2c',
      '--fw-bg-header':'#0d1117','--fw-text':'#e2e8f0','--fw-muted':'#a0aec0',
      '--fw-border':'#4a5568','--fw-link':'#63b3ed','--fw-accent':'#7f9cf5'
    },
    forest: {
      '--fw-bg':'#f0f4f0','--fw-bg-card':'#ffffff','--fw-bg-sidebar':'#e8f0e8',
      '--fw-bg-header':'#2f4a2f','--fw-accent':'#48bb78','--fw-link':'#38a169'
    },
    amber: {
      '--fw-bg':'#fffbf0','--fw-bg-card':'#ffffff','--fw-bg-sidebar':'#fef3c7',
      '--fw-bg-header':'#92400e','--fw-accent':'#d97706','--fw-link':'#b45309'
    }
  };

  function applySkin(name, extra) {
    const vars = { ...(SKINS[name]||{}), ...(extra||{}) };
    Object.entries(vars).forEach(([k,v]) =>
      document.documentElement.style.setProperty(k,v));
  }

  function renderSkinSelector(FW) {
    const el = document.getElementById('fw-skin-selector');
    if (!el) return;
    el.innerHTML = Object.keys(SKINS).map(name =>
      `<button class="fw-skin-btn${name===FW.state.currentSkin?' active':''}" data-skin="${name}">${name}</button>`
    ).join('');
    el.querySelectorAll('.fw-skin-btn').forEach(btn =>
      btn.addEventListener('click', () => {
        FW.state.currentSkin = btn.dataset.skin;
        applySkin(btn.dataset.skin, FW.state.manifest.plumage?.cssVars);
        renderSkinSelector(FW);
      }));
  }

  // ── Search ───────────────────────────────────────────────────────────
  function setupSearch(FW) {
    const input = document.getElementById('fw-search');
    if (!input) return;
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase().trim();
      if (!q) { FW.state.query = parseQuery(); FW.emitter.emit('render'); return; }
      const results = (FW.state.manifest.pages||[]).filter(p =>
        p.title.toLowerCase().includes(q) || p.content.toLowerCase().includes(q));
      const mainEl = document.getElementById('fw-main');
      if (mainEl) mainEl.innerHTML = renderAllPages(results);
    });
  }

  function setupNav(FW) {
    document.querySelectorAll('.fw-nav-btn').forEach(btn =>
      btn.addEventListener('click', () => navigate(FW, { view: btn.dataset.view })));
  }

  // ── Boot ─────────────────────────────────────────────────────────────
  function boot() {
    const manifest = window.__FW_MANIFEST__ || {
      title: 'Feather Wiki', pages: [], timeline: [],
      plumage: { name: 'default', cssVars: {} },
      extensions: [], defaultPage: '', version: '0.1.0',
      branch: 'trunk', artifactId: '', generatedAt: new Date().toISOString()
    };

    const emitter = createEmitter();
    const state = {
      manifest,
      query: parseQuery(),
      currentSkin: manifest.plumage?.name || 'default'
    };

    const FW = {
      state, emitter, html,
      ready(fn) {
        if (document.readyState === 'loading')
          document.addEventListener('DOMContentLoaded', fn);
        else fn();
      }
    };
    window.FW = FW;

    emitter.on('render', () => render(FW));

    FW.ready(() => {
      const titleEl = document.getElementById('fw-wiki-title');
      if (titleEl) titleEl.textContent = manifest.title;

      applySkin(state.currentSkin, manifest.plumage?.cssVars);
      renderSkinSelector(FW);
      setupSearch(FW);
      setupNav(FW);

      if (!state.query.page && manifest.defaultPage)
        state.query = { page: manifest.defaultPage };

      emitter.emit('render');
      emitter.emit('DOMContentLoaded');
    });

    window.addEventListener('popstate', () => {
      state.query = parseQuery();
      emitter.emit('render');
    });
  }

  boot();
})();

/* Extensions */