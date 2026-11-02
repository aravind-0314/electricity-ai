/**
 * Energy Accounting Interactive Logic & Tables
 */

const Energy = {
  currentPage: 1,
  totalPages: 1,
  charts: {},

  init() {
    this.loadAll();
  },

  async loadAll() {
    const feeder = document.getElementById('energy-feeder-filter').value;
    // Update CSV export link
    const exportBtn = document.getElementById('btn-export-energy');
    if (exportBtn) {
      exportBtn.href = `/api/export/energy${feeder !== 'all' ? `?feeder_id=${feeder}` : ''}`;
    }

    try {
      await Promise.all([
        this.loadSummaryAndFeeders(feeder),
        this.loadDailyTable(feeder, this.currentPage)
      ]);
    } catch (e) {
      console.error("Energy accounting load error:", e);
    }
  },

  async loadSummaryAndFeeders(feederId) {
    const data = await App.fetchJson(`/api/energy-accounting?feeder_id=${feederId}`);
    if (!data.success) return;

    const s = data.summary;

    document.getElementById('acc-supplied').textContent = App.formatKWh(s.supplied_energy_kwh);
    document.getElementById('acc-billed').textContent = App.formatKWh(s.billed_energy_kwh);
    document.getElementById('acc-tech').textContent = App.formatKWh(s.total_technical_loss_kwh);
    document.getElementById('acc-unexplained').textContent = App.formatKWh(s.unexplained_loss_kwh);

    const billedPct = s.supplied_energy_kwh > 0 ? (s.billed_energy_kwh / s.supplied_energy_kwh * 100).toFixed(1) : 0;
    const techPct = s.supplied_energy_kwh > 0 ? (s.total_technical_loss_kwh / s.supplied_energy_kwh * 100).toFixed(1) : 0;
    const unexpPct = s.supplied_energy_kwh > 0 ? (s.unexplained_loss_kwh / s.supplied_energy_kwh * 100).toFixed(1) : 0;

    document.getElementById('acc-billed-pct').textContent = `${billedPct}% Billed`;
    document.getElementById('acc-tech-pct').textContent = `${techPct}% Technical Loss`;
    document.getElementById('acc-unexplained-pct').textContent = `${unexpPct}% Unexplained Loss`;

    // Detailed physics losses
    document.getElementById('acc-cable').textContent = App.formatKWh(s.cable_loss_kwh);
    document.getElementById('acc-core').textContent = App.formatKWh(s.transformer_core_loss_kwh);
    document.getElementById('acc-copper').textContent = App.formatKWh(s.transformer_copper_loss_kwh);

    // Reconciliation badge
    const badgeEl = document.getElementById('reconciliation-badge');
    if (badgeEl) {
      badgeEl.textContent = `Balanced (Residual: ${s.reconciliation_residual_kwh} kWh)`;
    }

    // Render Pie Chart
    this.renderPieChart(s);

    // Render Feeder Cards
    this.renderFeederCards(data.feeders);
  },

  renderPieChart(s) {
    const ctx = document.getElementById('chart-accounting-pie');
    if (!ctx) return;
    if (typeof Chart === 'undefined') {
      console.warn("Chart.js not loaded.");
      return;
    }
    if (this.charts.pie) this.charts.pie.destroy();

    this.charts.pie = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Billed Energy', 'Cable Losses', 'Transformer Core', 'Transformer Copper', 'Unexplained Losses'],
        datasets: [{
          data: [
            s.billed_energy_kwh,
            s.cable_loss_kwh,
            s.transformer_core_loss_kwh,
            s.transformer_copper_loss_kwh,
            s.unexplained_loss_kwh
          ],
          backgroundColor: [
            '#06B6D4', // Billed Cyan
            '#3B82F6', // Cable Blue
            '#8B5CF6', // Core Purple
            '#F59E0B', // Copper Amber
            '#EF4444'  // Unexplained Red
          ],
          borderWidth: 2,
          borderColor: '#111827',
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '66%',
        layout: {
          padding: 6
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 8,
              boxHeight: 8,
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 8,
              color: '#CBD5E1',
              font: { size: 10, family: "'Inter', sans-serif" }
            }
          },
          tooltip: {
            backgroundColor: '#0F172A',
            titleColor: '#F8FAFC',
            bodyColor: '#94A3B8',
            borderColor: '#1E293B',
            borderWidth: 1
          }
        }
      }
    });
  },

  renderFeederCards(feeders) {
    const container = document.getElementById('feeder-cards-container');
    if (!container || !feeders) return;

    container.innerHTML = feeders.map(f => `
      <div class="panel-card" style="padding: 1rem; background: #11192C; border: 1px solid #1E2B45;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <h5 style="margin: 0; font-size: 0.95rem; font-weight: 700; color: #FFFFFF;">${f.feeder_id}</h5>
          <span style="font-size: 0.72rem; background: #16223B; padding: 0.2rem 0.5rem; border-radius: 4px; color: #38BDF8; font-weight: 600; border: 1px solid #1E2E4E;">${f.substation}</span>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.75rem;">Length: ${f.length_km} km • 11 kV Substation</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem;">
          <div><span style="color: var(--text-secondary);">Supplied:</span><br><strong style="color: #FFFFFF;">${App.formatNumber(f.supplied_kwh, 1)}</strong></div>
          <div><span style="color: var(--text-secondary);">Billed:</span><br><strong style="color: #FFFFFF;">${App.formatNumber(f.billed_kwh, 1)}</strong></div>
          <div><span style="color: var(--text-secondary);">Technical:</span><br><strong style="color: var(--warning);">${App.formatNumber(f.technical_kwh, 1)}</strong></div>
          <div><span style="color: var(--text-secondary);">Unexplained:</span><br><strong style="color: var(--danger);">${App.formatNumber(f.unexplained_kwh, 1)}</strong></div>
        </div>
        <div style="margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid rgba(255, 255, 255, 0.06); display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary);">Total Loss %:</span>
          <span style="font-size: 0.95rem; font-weight: 700; color: ${f.loss_percentage > 15 ? 'var(--danger)' : 'var(--warning)'};">${f.loss_percentage}%</span>
        </div>
      </div>
    `).join('');
  },

  async loadDailyTable(feederId, page = 1) {
    this.currentPage = page;
    const tbody = document.getElementById('daily-accounting-body');
    tbody.innerHTML = `<tr><td colspan="13" class="text-center" style="padding: 2rem;"><div class="spinner-container"><div class="spinner"></div><div>Loading logs...</div></div></td></tr>`;

    const data = await App.fetchJson(`/api/energy-accounting/daily?feeder_id=${feederId}&page=${page}&per_page=10`);
    if (!data.success) return;

    const d = data.data;
    this.totalPages = d.total_pages;

    // Render table rows
    tbody.innerHTML = d.records.map(r => `
      <tr>
        <td><strong>${r.audit_date}</strong></td>
        <td><span style="font-weight: 600; color: var(--navy-dark);">${r.feeder_id}</span></td>
        <td>Day ${r.day_number}</td>
        <td>${App.formatNumber(r.supplied_energy_kwh, 2)}</td>
        <td>${App.formatNumber(r.billed_energy_kwh, 2)}</td>
        <td>${App.formatNumber(r.cable_loss_kwh, 2)}</td>
        <td>${App.formatNumber(r.transformer_core_loss_kwh, 2)}</td>
        <td>${App.formatNumber(r.transformer_copper_loss_kwh, 2)}</td>
        <td style="color: var(--warning); font-weight: 600;">${App.formatNumber(r.technical_loss_kwh, 2)}</td>
        <td style="color: var(--danger); font-weight: 600;">${App.formatNumber(r.unexplained_loss_kwh, 2)}</td>
        <td><strong>${App.formatNumber(r.total_distribution_loss_kwh, 2)}</strong></td>
        <td><span style="font-weight: 700; color: ${r.loss_percentage > 14 ? 'var(--danger)' : 'var(--text-main)'};">${r.loss_percentage}%</span></td>
        <td style="font-size: 0.75rem; color: #16A36A;">${r.reconciliation_residual_kwh.toFixed(4)}</td>
      </tr>
    `).join('');

    // Pagination controls
    document.getElementById('page-info').textContent = `Showing page ${d.page} of ${d.total_pages} (${d.total_records} daily audits)`;
    document.getElementById('btn-prev').disabled = d.page <= 1;
    document.getElementById('btn-next').disabled = d.page >= d.total_pages;

    // Render 30-day Trend Chart from all daily data
    this.renderDailyTrendChart(d.records);
  },

  renderDailyTrendChart(records) {
    const ctx = document.getElementById('chart-accounting-trend');
    if (!ctx || !records || records.length === 0) return;
    if (typeof Chart === 'undefined') {
      console.warn("Chart.js not loaded.");
      return;
    }
    if (this.charts.trend) this.charts.trend.destroy();

    const labels = records.map(r => `${r.feeder_id} D${r.day_number}`);
    const cable = records.map(r => r.cable_loss_kwh);
    const core = records.map(r => r.transformer_core_loss_kwh);
    const copper = records.map(r => r.transformer_copper_loss_kwh);
    const unexp = records.map(r => r.unexplained_loss_kwh);

    this.charts.trend = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          { label: 'Unexplained Loss', data: unexp, borderColor: '#EF4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderWidth: 2, pointRadius: 2, tension: 0.25 },
          { label: 'Cable Ohmic Loss', data: cable, borderColor: '#3B82F6', borderWidth: 1.5, pointRadius: 1.5, tension: 0.25 },
          { label: 'Transformer Copper', data: copper, borderColor: '#F59E0B', borderWidth: 1.5, pointRadius: 1.5, tension: 0.25 },
          { label: 'Transformer Core', data: core, borderColor: '#8B5CF6', borderWidth: 1.5, pointRadius: 1.5, tension: 0.25 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 8,
              boxHeight: 8,
              usePointStyle: true,
              pointStyle: 'circle',
              color: '#CBD5E1',
              font: { size: 10, family: "'Inter', sans-serif" }
            }
          },
          tooltip: {
            backgroundColor: '#0F172A',
            titleColor: '#F8FAFC',
            bodyColor: '#94A3B8',
            borderColor: '#1E293B',
            borderWidth: 1
          }
        },
        scales: {
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94A3B8', font: { size: 9 } }
          },
          x: {
            grid: { display: false },
            ticks: { color: '#94A3B8', font: { size: 9 }, maxRotation: 45 }
          }
        }
      }
    });
  },

  changePage(delta) {
    const newPage = this.currentPage + delta;
    if (newPage >= 1 && newPage <= this.totalPages) {
      const feeder = document.getElementById('energy-feeder-filter').value;
      this.loadDailyTable(feeder, newPage);
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  Energy.init();
});

