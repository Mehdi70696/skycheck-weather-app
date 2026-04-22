/**
 * toggle.js — SkyCheck Temperature Unit Toggle
 * Uses data-celsius / data-fahrenheit attributes pre-computed
 * by the Python backend. No arithmetic in JavaScript.
 *
 * COMP1682 Final Year Project — Mohammadmehdi Mohammad Zadeh (001125181)
 */

let currentUnit = 'c';

function setUnit(unit) {
  if (unit === currentUnit) return;
  currentUnit = unit;

  // Update all temperature elements
  document.querySelectorAll('[data-celsius][data-fahrenheit]').forEach(el => {
    el.textContent = el.textContent.replace(/[\d.-]+°[CF]?/, '') +
      (unit === 'c'
        ? el.dataset.celsius + (el.dataset.celsius.length > 0 ? '°C' : '')
        : el.dataset.fahrenheit + (el.dataset.fahrenheit.length > 0 ? '°F' : ''));
  });

  // Simpler: replace text content entirely with the right unit
  document.querySelectorAll('[data-celsius]').forEach(el => {
    const val = unit === 'c' ? el.dataset.celsius : el.dataset.fahrenheit;
    // Check if this is a temp-main, feels-like span, or forecast temp
    const txt = el.textContent;
    if (txt.includes('°')) {
      el.textContent = val + '°' + unit.toUpperCase();
    } else {
      el.textContent = val;
    }
  });

  // Update wind speed too
  document.querySelectorAll('.wind-kmh').forEach(el => {
    el.textContent = unit === 'c'
      ? el.dataset.kmh + ' km/h'
      : el.dataset.mph + ' mph';
  });

  // Update toggle button states
  document.getElementById('btn-c').classList.toggle('active', unit === 'c');
  document.getElementById('btn-f').classList.toggle('active', unit === 'f');
}
