// ==UserScript==
// @name         SICOES - Descargar DBC visibles
// @namespace    https://www.sicoes.gob.bo/
// @version      0.1.0
// @description  Agrega un boton para hacer click masivo sobre los enlaces "Documento Base de Contratacion" visibles en la tabla de resultados.
// @match        https://www.sicoes.gob.bo/portal/contrataciones/*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const BUTTON_ID = 'dip03-download-dbc-visible';
  const PANEL_ID = 'dip03-download-dbc-panel';
  const LINK_LABEL = 'documento base de contratacion';
  const CLICK_DELAY_MS = 8000;

  function sleep(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function normalizeText(value) {
    return (value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  function extractCuce(row) {
    const firstCell = row.querySelector('td');
    if (!firstCell) {
      return null;
    }

    const raw = firstCell.textContent.replace(/\s+/g, '');
    return /^\d{2}-/.test(raw) ? raw : null;
  }

  function getVisibleRows() {
    return Array.from(document.querySelectorAll('tr')).filter((row) => {
      const style = window.getComputedStyle(row);
      if (style.display === 'none' || style.visibility === 'hidden') {
        return false;
      }

      const rect = row.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
  }

  function getVisibleDbcTargets() {
    const matches = [];

    for (const row of getVisibleRows()) {
      const cuce = extractCuce(row);
      if (!cuce) {
        continue;
      }

      for (const link of row.querySelectorAll('a')) {
        const label = normalizeText(link.textContent);
        if (label === LINK_LABEL) {
          matches.push({
            cuce,
            label: link.textContent.trim(),
            link,
          });
        }
      }
    }

    return matches;
  }

  function renderStatus(message, tone = 'info') {
    const panel = document.getElementById(PANEL_ID);
    if (!panel) {
      return;
    }

    const palette = {
      info: { bg: '#eff6ff', color: '#0f172a', border: '#93c5fd' },
      warn: { bg: '#fff7ed', color: '#7c2d12', border: '#fdba74' },
      ok: { bg: '#ecfdf5', color: '#14532d', border: '#86efac' },
    };

    const selected = palette[tone] || palette.info;
    panel.textContent = message;
    panel.style.background = selected.bg;
    panel.style.color = selected.color;
    panel.style.borderColor = selected.border;
  }

  function printPlanToConsole(items) {
    console.group('SICOES DBC visibles');
    console.table(
      items.map((item, index) => ({
        orden: index + 1,
        cuce: item.cuce,
        tipo: item.label,
      }))
    );
    console.groupEnd();
  }

  async function triggerVisibleDbcDownloads() {
    const button = document.getElementById(BUTTON_ID);
    const items = getVisibleDbcTargets();

    if (items.length === 0) {
      renderStatus('No se encontraron enlaces visibles "Documento Base de Contratacion".', 'warn');
      return;
    }

    printPlanToConsole(items);
    renderStatus(`Preparando ${items.length} descargas visibles. Revisa la consola para el detalle por CUCE.`, 'info');

    if (button) {
      button.disabled = true;
      button.textContent = 'Descargando...';
    }

    for (let index = 0; index < items.length; index += 1) {
      const item = items[index];
      renderStatus(`Descargando ${index + 1}/${items.length}: ${item.cuce}`, 'info');
      item.link.click();
      await sleep(CLICK_DELAY_MS);
    }

    renderStatus(`Descarga masiva finalizada. Total de DBC disparados: ${items.length}.`, 'ok');

    if (button) {
      button.disabled = false;
      button.textContent = 'Descargar DBC visibles';
    }
  }

  function mountControls() {
    if (document.getElementById(BUTTON_ID)) {
      return;
    }

    const wrapper = document.createElement('div');
    wrapper.style.position = 'fixed';
    wrapper.style.top = '120px';
    wrapper.style.right = '24px';
    wrapper.style.zIndex = '99999';
    wrapper.style.display = 'flex';
    wrapper.style.flexDirection = 'column';
    wrapper.style.gap = '8px';
    wrapper.style.maxWidth = '320px';

    const button = document.createElement('button');
    button.id = BUTTON_ID;
    button.type = 'button';
    button.textContent = 'Descargar DBC visibles';
    button.style.padding = '10px 14px';
    button.style.background = '#0b6aa2';
    button.style.color = '#ffffff';
    button.style.border = 'none';
    button.style.borderRadius = '6px';
    button.style.boxShadow = '0 2px 8px rgba(0,0,0,0.18)';
    button.style.cursor = 'pointer';
    button.style.fontSize = '14px';
    button.style.fontWeight = '600';
    button.addEventListener('click', triggerVisibleDbcDownloads);

    const panel = document.createElement('div');
    panel.id = PANEL_ID;
    panel.style.padding = '10px 12px';
    panel.style.border = '1px solid #93c5fd';
    panel.style.borderRadius = '6px';
    panel.style.background = '#eff6ff';
    panel.style.color = '#0f172a';
    panel.style.boxShadow = '0 2px 8px rgba(0,0,0,0.12)';
    panel.style.fontSize = '12px';
    panel.style.lineHeight = '1.4';
    panel.textContent = 'El boton descargara los "Documento Base de Contratacion" visibles en la tabla actual con una pausa de 2.5 s entre clicks.';

    wrapper.appendChild(button);
    wrapper.appendChild(panel);
    document.body.appendChild(wrapper);
  }

  const observer = new MutationObserver(() => {
    mountControls();
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });

  mountControls();
})();
