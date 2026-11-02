/**
 * AI Theft Detection Interactive Page Logic
 */

const Detection = {
  currentPage: 1,
  totalPages: 1,
  searchTimer: null,

  init() {
    this.loadPredictions(1);
  },

  onSearchInput() {
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.loadPredictions(1);
    }, 300);
  },

  async loadPredictions(page = 1) {
    this.currentPage = page;
    const feeder = document.getElementById('filter-feeder').value;
    const tariff = document.getElementById('filter-tariff').value;
    const priority = document.getElementById('filter-priority').value;
    const search = document.getElementById('filter-search').value.trim();
    const sort = document.getElementById('filter-sort').value;

    // Update CSV export link
    const exportBtn = document.getElementById('btn-export-predictions');
    if (exportBtn) {
      exportBtn.href = `/api/export/predictions?feeder_id=${feeder}&priority=${priority}`;
    }

    const tbody = document.getElementById('predictions-table-body');
    tbody.innerHTML = `<tr><td colspan="11" class="text-center" style="padding: 2.5rem;"><div class="spinner-container"><div class="spinner"></div><div>Filtering predictions...</div></div></td></tr>`;

    let url = `/api/ai/predictions?page=${page}&per_page=15&sort_by=anomaly_score&sort_order=${sort}`;
    if (feeder !== 'all') url += `&feeder_id=${feeder}`;
    if (tariff !== 'all') url += `&tariff=${tariff}`;
    if (priority !== 'all') url += `&priority=${priority}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    try {
      const resp = await App.fetchJson(url);
      if (!resp.success) return;

      const d = resp.data;
      this.totalPages = d.total_pages;

      if (!d.records || d.records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" class="empty-state">No matching consumer predictions found.</td></tr>`;
        return;
      }

      tbody.innerHTML = d.records.map(r => {
        let badgeClass = 'badge-low';
        if (r.review_priority === 'Critical') badgeClass = 'badge-critical';
        else if (r.review_priority === 'High') badgeClass = 'badge-high';
        else if (r.review_priority === 'Medium') badgeClass = 'badge-medium';

        const rfProb = (r.rf_probability !== null && r.rf_probability !== undefined)
          ? `${(r.rf_probability * 100).toFixed(1)}%`
          : '--';

        return `
          <tr>
            <td><strong style="color: #FFFFFF;">${r.consumer_id}</strong></td>
            <td style="font-size: 0.78rem; color: var(--text-muted);">${r.meter_id}</td>
            <td><span style="font-weight: 500; color: #CBD5E1;">${r.feeder_id}</span></td>
            <td>${r.tariff_category}</td>
            <td>${r.sanctioned_load_kw} kW</td>
            <td style="font-size: 0.78rem; color: var(--text-muted); font-family: var(--font-mono);">${r.iforest_raw_score.toFixed(3)}</td>
            <td>
              <strong style="color: #FFFFFF; font-family: var(--font-mono);">${r.anomaly_score.toFixed(4)}</strong>
              <div class="score-bar-container">
                <div class="score-bar-fill fill-${r.review_priority.toLowerCase()}" style="width: ${Math.round(r.anomaly_score * 100)}%;"></div>
              </div>
            </td>
            <td><span class="badge-priority ${badgeClass}">${r.review_priority}</span></td>
            <td><span style="font-size: 0.8rem; font-weight: 600; font-family: var(--font-mono); color: ${r.rf_probability > 0.5 ? 'var(--danger)' : 'var(--text-muted)'};">${rfProb}</span></td>
            <td style="max-width: 260px; font-size: 0.78rem; color: var(--text-secondary);">${r.diagnostic_reason}</td>
            <td>
              <button class="btn-custom btn-outline-custom" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;" onclick="Detection.viewConsumerModal('${r.consumer_id}')">
                <i class="fa-solid fa-chart-simple"></i> Details
              </button>
            </td>
          </tr>
        `;
      }).join('');

      document.getElementById('pred-page-info').textContent = `Showing page ${d.page} of ${d.total_pages} (${d.total_records} consumers)`;
      document.getElementById('pred-btn-prev').disabled = d.page <= 1;
      document.getElementById('pred-btn-next').disabled = d.page >= d.total_pages;

    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="11" class="alert alert-danger">Error loading predictions.</td></tr>`;
    }
  },

  changePage(delta) {
    const newPage = this.currentPage + delta;
    if (newPage >= 1 && newPage <= this.totalPages) {
      this.loadPredictions(newPage);
    }
  },

  modalChart: null,
  isInspecting: false,

  async viewConsumerModal(consumerId) {
    if (this.isInspecting) {
      console.warn("Inspection request already in progress. Ignoring duplicate click.");
      return;
    }
    this.isInspecting = true;

    // Immediately destroy any previous modal chart instance
    if (this.modalChart) {
      try {
        this.modalChart.destroy();
      } catch (err) {
        console.warn("Error destroying modal chart:", err);
      }
      this.modalChart = null;
    }

    const titleEl = document.getElementById('modal-consumer-title');
    const bodyEl = document.getElementById('modal-consumer-body');

    if (titleEl) titleEl.textContent = `Diagnostic Inspection Profile: ${consumerId}`;
    if (bodyEl) {
      bodyEl.innerHTML = `
        <div class="spinner-container" id="modal-spinner" style="padding: 2.5rem 1rem; text-align: center;">
          <div class="spinner"></div>
          <div style="margin-top: 0.75rem; color: var(--text-muted); font-size: 0.85rem;">Loading consumer engineered features & telemetry for ${consumerId}...</div>
        </div>
      `;
    }

    App.openModal('consumer-modal');

    try {
      const resp = await App.fetchJson(`/api/consumers/${encodeURIComponent(consumerId)}`, {}, 10000);
      if (!resp || !resp.success || !resp.data) {
        const errorMsg = (resp && resp.error) ? resp.error : `Consumer ${consumerId} not found or failed to load.`;
        if (bodyEl) {
          bodyEl.innerHTML = `
            <div class="alert alert-danger" style="margin: 1.5rem 0; padding: 1rem; border-radius: 6px; background: #FEF2F2; color: #991B1B; border: 1px solid #FCA5A5;">
              <div style="font-weight: 600; margin-bottom: 0.25rem;"><i class="fa-solid fa-triangle-exclamation"></i> Error</div>
              <div style="font-size: 0.85rem;">${errorMsg}</div>
            </div>
          `;
        }
        return;
      }
      const c = resp.data.consumer;
      const f = resp.data.features || {};
      const daily = resp.data.daily_trend;
      const hourly = resp.data.hourly_profile;

      let priorityBadge = 'badge-low';
      if (c.review_priority === 'Critical') priorityBadge = 'badge-critical';
      else if (c.review_priority === 'High') priorityBadge = 'badge-high';
      else if (c.review_priority === 'Medium') priorityBadge = 'badge-medium';

      if (bodyEl) {
        bodyEl.innerHTML = `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem; background: #0D1526; padding: 1rem; border-radius: var(--radius-md); border: 1px solid #1E2E4E;">
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Feeder:</span><br><strong style="color: #FFFFFF;">${c.feeder_id || '--'}</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Meter ID:</span><br><strong style="color: #FFFFFF;">${c.meter_id || '--'}</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Tariff:</span><br><strong style="color: #FFFFFF;">${c.tariff_category || '--'}</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Sanctioned:</span><br><strong style="color: #FFFFFF;">${c.sanctioned_load_kw || 0} kW</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Anomaly Score:</span><br><strong style="color: #38BDF8; font-family: var(--font-mono);">${c.anomaly_score != null ? c.anomaly_score.toFixed(4) : '--'}</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Triage Priority:</span><br><span class="badge-priority ${priorityBadge}">${c.review_priority || 'Low'}</span></div>
          </div>

          <div style="margin-bottom: 1rem;">
            <h6 style="font-size: 0.8rem; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.35rem;">Diagnostic Explanation</h6>
            <p style="font-size: 0.825rem; color: #F8FAFC; background: rgba(245, 158, 11, 0.1); padding: 0.65rem 0.85rem; border-left: 3px solid #F59E0B; border-radius: 4px; margin: 0; line-height: 1.45;">
              ${c.diagnostic_reason || 'Normative consumption profile across all baseline parameters.'}
            </p>
          </div>

          <div style="margin-bottom: 1.25rem;">
            <h6 style="font-size: 0.8rem; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.35rem;">Recommended Field Action</h6>
            <p style="font-size: 0.825rem; color: #F8FAFC; background: rgba(59, 130, 246, 0.1); padding: 0.65rem 0.85rem; border-left: 3px solid #3B82F6; border-radius: 4px; margin: 0; line-height: 1.45;">
              ${c.recommended_action || 'Routine automated AMR telemetry surveillance.'}
            </p>
          </div>

          <!-- 10 Engineered Features Grid -->
          <h6 style="font-size: 0.8rem; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.4rem;">Engineered ML Feature Signatures</h6>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.4rem; margin-bottom: 1.25rem; font-size: 0.75rem;">
            <div style="background: #0D1526; border: 1px solid #1E2E4E; padding: 0.4rem 0.65rem; border-radius: 4px;">
              <span style="color: var(--text-secondary);">Mean Daily:</span> <strong style="color: #FFFFFF;">${f.mean_daily_consumption != null ? f.mean_daily_consumption.toFixed(2) : '--'} kWh</strong>
            </div>
            <div style="background: #0D1526; border: 1px solid #1E2E4E; padding: 0.4rem 0.65rem; border-radius: 4px;">
              <span style="color: var(--text-secondary);">Rolling 7D:</span> <strong style="color: #FFFFFF;">${f.rolling_avg_7d != null ? f.rolling_avg_7d.toFixed(2) : '--'} kWh</strong>
            </div>
            <div style="background: #0D1526; border: 1px solid #1E2E4E; padding: 0.4rem 0.65rem; border-radius: 4px;">
              <span style="color: var(--text-secondary);">Drop Ratio:</span> <strong style="color: #FFFFFF;">${f.drop_ratio != null ? f.drop_ratio.toFixed(3) : '--'}</strong>
            </div>
            <div style="background: #0D1526; border: 1px solid #1E2E4E; padding: 0.4rem 0.65rem; border-radius: 4px;">
              <span style="color: var(--text-secondary);">CV (σ/μ):</span> <strong style="color: #FFFFFF;">${f.cv_consumption != null ? f.cv_consumption.toFixed(3) : '--'}</strong>
            </div>
            <div style="background: #0D1526; border: 1px solid #1E2E4E; padding: 0.4rem 0.65rem; border-radius: 4px;">
              <span style="color: var(--text-secondary);">Load Factor:</span> <strong style="color: #FFFFFF;">${f.load_factor != null ? f.load_factor.toFixed(3) : '--'}</strong>
            </div>
            <div style="background: #0D1526; border: 1px solid #1E2E4E; padding: 0.4rem 0.65rem; border-radius: 4px;">
              <span style="color: var(--text-secondary);">Peak-to-Avg:</span> <strong style="color: #FFFFFF;">${f.peak_to_average_ratio != null ? f.peak_to_average_ratio.toFixed(3) : '--'}</strong>
            </div>
            <div style="background: #0D1526; border: 1px solid #1E2E4E; padding: 0.4rem 0.65rem; border-radius: 4px;">
              <span style="color: var(--text-secondary);">Missing %:</span> <strong style="color: #FFFFFF;">${f.missing_reading_pct != null ? f.missing_reading_pct.toFixed(2) : '0'}%</strong>
            </div>
            <div style="background: #0D1526; border: 1px solid #1E2E4E; padding: 0.4rem 0.65rem; border-radius: 4px;">
              <span style="color: var(--text-secondary);">Peer Relative:</span> <strong style="color: #FFFFFF;">${f.peer_relative_deviation != null ? f.peer_relative_deviation.toFixed(3) : '--'}</strong>
            </div>
          </div>

          <h6 style="font-size: 0.8rem; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem;">30-Day Billed Consumption Trend</h6>
          <div style="height: 180px; position: relative;">
            <canvas id="det-modal-chart"></canvas>
          </div>
        `;
      }

      const canvas = document.getElementById('det-modal-chart');
      if (canvas && daily && daily.labels && daily.labels.length > 0 && typeof Chart !== 'undefined') {
        if (this.modalChart) {
          this.modalChart.destroy();
        }
        this.modalChart = new Chart(canvas, {
          type: 'bar',
          data: {
            labels: daily.labels,
            datasets: [{
              label: 'Billed Consumption',
              data: daily.billed,
              backgroundColor: '#3B82F6',
              borderRadius: 3
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: '#0F172A',
                titleColor: '#F8FAFC',
                bodyColor: '#94A3B8',
                borderColor: '#1E293B',
                borderWidth: 1,
                callbacks: {
                  label: (item) => ` ${item.dataset.label}: ${Number(item.raw).toFixed(2)} kWh`
                }
              }
            },
            scales: {
              y: {
                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                ticks: { color: '#94A3B8', font: { size: 9 }, callback: (v) => `${v} kWh` }
              },
              x: {
                grid: { display: false },
                ticks: { color: '#94A3B8', font: { size: 8 }, maxRotation: 0 }
              }
            }
          }
        });
      }

    } catch (e) {
      console.error(`Error loading profile for ${consumerId}:`, e);
      const errorMsg = e.message || 'Failed to load consumer profile.';
      if (bodyEl) {
        bodyEl.innerHTML = `
          <div class="alert alert-danger" style="margin: 1.5rem 0; padding: 1.25rem; border-radius: 6px; background: #FEF2F2; color: #991B1B; border: 1px solid #FCA5A5;">
            <div style="font-weight: 600; margin-bottom: 0.35rem; font-size: 0.9rem;">
              <i class="fa-solid fa-triangle-exclamation" style="margin-right: 0.4rem;"></i>
              Failed to Load Consumer Profile
            </div>
            <div style="font-size: 0.825rem; color: #7F1D1D;">${errorMsg}</div>
          </div>
        `;
      }
    } finally {
      this.isInspecting = false;
    }
  },

  async retrainPipeline() {
    const btn = document.getElementById('btn-retrain');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Retraining ML Pipeline...`;
    App.showToast("Training Isolation Forest and Random Forest benchmark...", "info", 4000);

    try {
      const resp = await App.fetchJson('/api/ai/train', { method: 'POST' });
      if (resp.success) {
        App.showToast("ML pipeline retrained successfully!", "success");
        this.loadPredictions(this.currentPage);
      }
    } catch (e) {
      App.showToast("Retraining failed: " + e.message, "danger");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-arrows-spin"></i> <span>Retrain Pipeline</span>`;
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  Detection.init();
});

