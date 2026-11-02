/**
 * Electricity Theft & Distribution Loss Detection - Core Frontend Utilities
 */

const App = {
  // Live Clock Updater
  initClock() {
    const clockEl = document.getElementById('live-clock');
    if (!clockEl) return;

    function update() {
      const now = new Date();
      clockEl.textContent = now.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    }
    update();
    setInterval(update, 1000);
  },

  // Mobile Sidebar Toggle
  initSidebar() {
    const toggleBtn = document.getElementById('mobile-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('show');
      });

      // Close on backdrop click on small screens
      document.addEventListener('click', (e) => {
        if (window.innerWidth <= 992 && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
          sidebar.classList.remove('show');
        }
      });
    }
  },

  // Toast Notification System
  showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✓';
    if (type === 'danger') icon = '⚠️';
    if (type === 'warning') icon = '⚡';

    toast.innerHTML = `
      <span style="font-weight: bold; font-size: 1.1rem;">${icon}</span>
      <div style="flex: 1;">${message}</div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  // Format numbers nicely
  formatKWh(val) {
    if (val === null || val === undefined || isNaN(val)) return '0.00 kWh';
    return Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' kWh';
  },

  formatNumber(val, decimals = 2) {
    if (val === null || val === undefined || isNaN(val)) return '0';
    return Number(val).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  },

  // Modal helpers
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
    }
  },

  // API helper with configurable timeout and detailed error extraction
  async fetchJson(url, options = {}, timeoutMs = 12000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      let data;
      try {
        data = await response.json();
      } catch (jsonErr) {
        data = null;
      }

      if (!response.ok) {
        const errorMsg = (data && (data.error || data.message))
          ? (data.error || data.message)
          : `HTTP Error: ${response.status} ${response.statusText}`;
        const err = new Error(errorMsg);
        err.status = response.status;
        err.data = data;
        throw err;
      }
      return data;
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        const timeoutErr = new Error(`Request timed out after ${timeoutMs / 1000}s on ${url}`);
        console.error(timeoutErr);
        App.showToast(`Request timed out: Server took too long to respond.`, 'danger');
        throw timeoutErr;
      }
      console.error(`API Fetch Error on ${url}:`, err);
      App.showToast(`Error: ${err.message}`, 'danger');
      throw err;
    }
  },

  initGlobalSearch() {
    const input = document.getElementById('global-search-input');
    if (!input) return;

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        input.focus();
        input.select();
      }
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = input.value.trim();
        if (query) {
          const localSearch = document.getElementById('search-input') || document.getElementById('insp-search');
          if (localSearch) {
            localSearch.value = query;
            if (typeof Detection !== 'undefined' && Detection.onSearchInput) Detection.onSearchInput();
            if (typeof Inspection !== 'undefined' && Inspection.onSearchInput) Inspection.onSearchInput();
          } else {
            window.location.href = `/ai-detection?search=${encodeURIComponent(query)}`;
          }
        }
      }
    });
  },
};

document.addEventListener('DOMContentLoaded', () => {
  App.initClock();
  App.initSidebar();
  App.initGlobalSearch();

  // Global modal escape key and backdrop dismiss listeners
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.active').forEach(m => {
        App.closeModal(m.id);
      });
    }
  });

  document.addEventListener('click', (e) => {
    if (e.target.classList && e.target.classList.contains('modal-overlay')) {
      App.closeModal(e.target.id);
    }
  });
});

