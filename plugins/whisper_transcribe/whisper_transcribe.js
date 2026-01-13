(function () {
  'use strict';

  // Try both common plugin IDs:
  // - folder name ("whisper_transcribe")
  // - YAML name ("WhisperTranscribe")
  const PLUGIN_IDS = ['whisper_transcribe', 'WhisperTranscribe'];
  const DROPDOWN_ID = 'whisper-transcribe-dropdown-container';

  function getSceneIdFromURL() {
    try {
      // Try pathname first: /scenes/123
      const pathMatch = window.location.pathname.match(/\/scenes\/(\d+)/);
      if (pathMatch) return parseInt(pathMatch[1], 10);

      // Fallback to hash routes: #/scenes/123
      const hashMatch = window.location.hash.match(/\/scenes\/(\d+)/);
      if (hashMatch) return parseInt(hashMatch[1], 10);
    } catch (e) {
      console.warn('[WhisperTranscribe] Failed to parse scene id from URL:', e);
    }
    return undefined;
  }

  async function resolvePluginId(graphqlURL) {
    const query = `query { plugins { id name } }`;
    try {
      const res = await fetch(graphqlURL, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
      const json = await res.json();
      if (json.errors || !json.data || !json.data.plugins) return null;

      const plugins = json.data.plugins;

      // Prefer exact id matches first
      for (const p of plugins) {
        if (PLUGIN_IDS.includes(p.id)) return p.id;
      }
      // Then match by name
      for (const p of plugins) {
        if (PLUGIN_IDS.includes(p.name)) return p.id;
      }
      // Heuristic fallback: anything containing "whisper"
      for (const p of plugins) {
        const n = (p.name || '').toLowerCase();
        const i = (p.id || '').toLowerCase();
        if (n.includes('whisper') || i.includes('whisper')) return p.id;
      }
      return null;
    } catch (e) {
      console.error('[WhisperTranscribe] Failed to resolve plugin id:', e);
      return null;
    }
  }

  async function runTranscribe(sceneId) {
    const mutation = `
      mutation RunPluginOperation($plugin_id: ID!, $args: Map!) {
        runPluginOperation(plugin_id: $plugin_id, args: $args)
      }
    `;
    const args = { mode: 'transcribe_scene_task', scene_id: sceneId };
    const base = document.querySelector('base')?.getAttribute('href') || '/';
    const graphqlURL = new URL('graphql', new URL(base, window.location.href)).toString();

    // Resolve plugin id; if not found, abort to avoid server-side panic on unknown id.
    const resolvedId = await resolvePluginId(graphqlURL);
    if (!resolvedId) {
      console.error('[WhisperTranscribe] Could not resolve plugin id. Aborting to avoid server error.');
      alert('Whisper Transcribe plugin not found on server. Try reloading plugins and refreshing the page.');
      return;
    }

    try {
      const res = await fetch(graphqlURL, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: mutation, variables: { plugin_id: resolvedId, args } }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
      const json = await res.json();
      if (json.errors) {
        console.error('[WhisperTranscribe] GraphQL errors:', json.errors);
        alert('Failed to start transcription. See console for details.');
        return;
      }
      console.debug('[WhisperTranscribe] Transcription started:', json.data);
    } catch (e) {
      console.error('[WhisperTranscribe] Request failed:', e);
      alert('Failed to start transcription. See console for details.');
    }
  }

  function buildDropdown(targetTitleEl) {
    if (!targetTitleEl || document.getElementById(DROPDOWN_ID)) return;

    const container = document.createElement('div');
    container.id = DROPDOWN_ID;
    container.className = 'wt-dropdown';

    container.innerHTML = `
      <button class="wt-dropbtn btn btn-secondary btn-sm" type="button" title="Whisper Transcribe">
        Transcribe
        <span class="wt-caret">▾</span>
      </button>
      <div class="wt-dropdown-content">
        <a href="#" id="wt-transcribe-action">Transcribe scene (Whisper)</a>
      </div>
    `;

    // Place next to the scene title, similar to the RenameFile plugin's target
    const parent = targetTitleEl.parentElement || targetTitleEl;
    parent.appendChild(container);

    // Wire up actions
    const actionEl = container.querySelector('#wt-transcribe-action');
    actionEl.addEventListener('click', function (ev) {
      ev.preventDefault();
      const sceneId = getSceneIdFromURL();
      if (!sceneId) {
        alert('Whisper Transcribe: could not determine scene id from URL.');
        return;
      }
      runTranscribe(sceneId);
      // hide menu after click
      container.classList.remove('wt-open');
    });

    // Dropdown toggle
    const btn = container.querySelector('.wt-dropbtn');
    btn.addEventListener('click', function (ev) {
      ev.preventDefault();
      container.classList.toggle('wt-open');
    });

    // Close when clicking outside
    document.addEventListener('click', function (ev) {
      if (!container.contains(ev.target)) {
        container.classList.remove('wt-open');
      }
    });
  }

  function mountIfPossible() {
    // Match the same area the RenameFile script targets
    const titleEl = document.querySelector('.scene-header div.TruncatedText');
    if (titleEl) {
      buildDropdown(titleEl);
      return true;
    }
    return false;
  }

  // Initial attempt
  if (!mountIfPossible()) {
    // Observe DOM changes for SPA navigation and render timing
    const observer = new MutationObserver((mutationsList) => {
      for (const mutation of mutationsList) {
        for (const addedNode of mutation.addedNodes) {
          if (addedNode.nodeType === Node.ELEMENT_NODE) {
            const q = addedNode.querySelector?.('.scene-header div.TruncatedText');
            if (q) {
              buildDropdown(q);
            }
          }
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  console.debug('[WhisperTranscribe] UI script initialized');
})();
