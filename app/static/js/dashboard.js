/**
 * Executive Dashboard Interactive Logic & Charts
 * Electricity Theft & Distribution Loss Detection System
 */

const Dashboard = {
  charts: {},
  isLoading: false,

  init() {
    this.loadAll();
  },

  async refresh() {
    return this.loadAll();
  },

  async loadAll() {
    if (this.isLoading) {
      console.warn("Dashboard refresh already in progress. Ignoring duplicate request.");
      return;
    }
    this.isLoading = true;

    // Visual loading state on refresh button
    const refreshBtn = document.getElementById('btn-refresh-dashboard') || document.querySelector('button[title="Refresh Dashboard"]');
    const icon = refreshBtn ? refreshBtn.querySelector('i') : null;
    if (icon) icon.classList.add('fa-spin');
    if (refreshBtn) refreshBtn.disabled = true;

    const feederEl = document.getElementById('feeder-filter');
    const feeder = feederEl ? feederEl.value : 'all';

    try {
      await Promise.all([
        this.loadSummary(feeder),
        this.loadChartsAndAlerts(feeder)
      ]);
    } catch (e) {
      console.error("Dashboard reload error:", e);
    } finally {
      this.isLoading = false;
      if (icon) icon.classList.remove('fa-spin');
      if (refreshBtn) refreshBtn.disabled = false;
    }
  },

  async loadSummary(feederId) {
    try {
      const data = await App.fetchJson(`/api/dashboard/summary?feeder_id=${encodeURIComponent(feederId)}`);
      if (!data || !data.success) {
        console.error("API /api/dashboard/summary failed:", data);
        return;
      }
      const s = data.summary;

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
      };

      setVal('kpi-consumers', s.total_consumers != null ? Number(s.total_consumers).toLocaleString() : '--');
      setVal('kpi-feeders', s.total_feeders != null ? s.total_feeders : '--');
      setVal('kpi-supplied', s.total_electricity_supplied_kwh != null ? App.formatKWh(s.total_electricity_supplied_kwh) : '--');
      setVal('kpi-billed', s.total_electricity_billed_kwh != null ? App.formatKWh(s.total_electricity_billed_kwh) : '--');
      setVal('kpi-technical', s.technical_losses_kwh != null ? App.formatKWh(s.technical_losses_kwh) : '--');
      setVal('kpi-unexplained', s.unexplained_losses_kwh != null ? App.formatKWh(s.unexplained_losses_kwh) : '--');
      setVal('kpi-inspection', s.consumers_requiring_inspection != null ? Number(s.consumers_requiring_inspection).toLocaleString() : '--');
      setVal('kpi-loss-pct', s.overall_loss_percentage != null ? `${Number(s.overall_loss_percentage).toFixed(2)}%` : '--');
    } catch (err) {
      console.error("Error loading KPI summary data:", err);
    }
  },

  async loadChartsAndAlerts(feederId) {
    try {
      const data = await App.fetchJson(`/api/dashboard/energy-trend?feeder_id=${encodeURIComponent(feederId)}`);
      if (!data || !data.success) {
        console.error("API /api/dashboard/energy-trend failed:", data);
        return;
      }
      const c = data.charts;

      if (c.daily_trend) {
        this.renderSupplyBilledChart(c.daily_trend);
        this.renderLossBreakdownChart(c.daily_trend);
      }
      if (c.priority_distribution) {
        this.renderPriorityChart(c.priority_distribution);
      }
      if (c.feeder_distribution) {
        this.renderFeederChart(c.feeder_distribution);
      }
      if (c.recent_alerts) {
        this.renderAlertsTable(c.recent_alerts);
      }
    } catch (err) {
      console.error("Error loading charts & alerts data:", err);
    }
  },

  renderSupplyBilledChart(data) {
    const ctx = document.getElementById('chart-supply-billed');
    if (!ctx) return;
    if (typeof Chart === 'undefined') {
      console.warn("Chart.js not loaded. Skipping chart-supply-billed render.");
      return;
    }
    if (this.charts.supplyBilled) this.charts.supplyBilled.destroy();

    this.charts.supplyBilled = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Supplied Energy',
            data: data.supplied,
            borderColor: '#3B82F6',
            backgroundColor: 'rgba(59, 130, 246, 0.12)',
            fill: true,
            tension: 0.25,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 5
          },
          {
            label: 'Billed Energy',
            data: data.billed,
            borderColor: '#06B6D4',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.25,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
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
            borderWidth: 1,
            callbacks: {
              label: (item) => ` ${item.dataset.label}: ${Number(item.raw).toLocaleString()} kWh`
            }
          }
        },
        scales: {
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94A3B8', font: { size: 9 }, callback: (v) => `${(v/1000).toFixed(0)}k` }
          },
          x: {
            grid: { display: false },
            ticks: { color: '#94A3B8', font: { size: 9 }, maxRotation: 0 }
          }
        }
      }
    });
  },

  renderPriorityChart(dist) {
    const ctx = document.getElementById('chart-priority-dist');
    if (!ctx) return;
    if (typeof Chart === 'undefined') {
      console.warn("Chart.js not loaded. Skipping chart-priority-dist render.");
      return;
    }
    if (this.charts.priority) this.charts.priority.destroy();

    this.charts.priority = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Critical', 'High', 'Medium', 'Low'],
        datasets: [{
          data: [dist.Critical || 0, dist.High || 0, dist.Medium || 0, dist.Low || 0],
          backgroundColor: ['#EF4444', '#F59E0B', '#3B82F6', '#64748B'],
          borderWidth: 2,
          borderColor: '#111827',
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
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
              padding: 10,
              color: '#CBD5E1',
              font: { size: 10, family: "'Inter', sans-serif" }
            }
          },
          tooltip: {
            backgroundColor: '#0F172A',
            titleColor: '#F8FAFC',
            bodyColor: '#94A3B8',
            borderColor: '#1E293B',
            borderWidth: 1,
            callbacks: {
              label: (item) => ` ${item.label}: ${item.raw} consumers`
            }
          }
        }
      }
    });
  },

  renderFeederChart(data) {
    const ctx = document.getElementById('chart-feeder-dist');
    if (!ctx) return;
    if (typeof Chart === 'undefined') {
      console.warn("Chart.js not loaded. Skipping chart-feeder-dist render.");
      return;
    }
    if (this.charts.feeder) this.charts.feeder.destroy();

    this.charts.feeder = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Supplied Energy',
            data: data.supplied,
            backgroundColor: '#3B82F6',
            borderRadius: 4
          },
          {
            label: 'Billed Energy',
            data: data.billed,
            backgroundColor: '#06B6D4',
            borderRadius: 4
          },
          {
            label: 'Technical Loss',
            data: data.technical,
            backgroundColor: '#F59E0B',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
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
            ticks: { color: '#94A3B8', font: { size: 10, family: "'Inter', sans-serif" } }
          }
        }
      }
    });
  },

  renderLossBreakdownChart(data) {
    const ctx = document.getElementById('chart-loss-breakdown');
    if (!ctx) return;
    if (typeof Chart === 'undefined') {
      console.warn("Chart.js not loaded. Skipping chart-loss-breakdown render.");
      return;
    }
    if (this.charts.lossBreakdown) this.charts.lossBreakdown.destroy();

    this.charts.lossBreakdown = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Technical Loss (Physical)',
            data: data.technical,
            borderColor: '#F59E0B',
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.25,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 5
          },
          {
            label: 'Unexplained Loss (Commercial)',
            data: data.unexplained,
            borderColor: '#EF4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.25,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
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
            ticks: { color: '#94A3B8', font: { size: 9 }, maxRotation: 0 }
          }
        }
      }
    });
  },

  renderAlertsTable(alerts) {
    const tbody = document.getElementById('alerts-table-body');
    if (!tbody) return;

    if (!alerts || alerts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No active anomaly alerts detected for this feeder.</td></tr>`;
      return;
    }

    tbody.innerHTML = alerts.map(a => {
      let badgeClass = 'badge-low';
      if (a.review_priority === 'Critical') badgeClass = 'badge-critical';
      else if (a.review_priority === 'High') badgeClass = 'badge-high';
      else if (a.review_priority === 'Medium') badgeClass = 'badge-medium';

      return `
        <tr>
          <td><strong style="color: var(--navy-dark);">${a.consumer_id}</strong></td>
          <td><span style="font-weight: 500;">${a.feeder_id}</span></td>
          <td>${a.tariff_category}</td>
          <td>${a.sanctioned_load_kw} kW</td>
          <td>
            <strong>${a.anomaly_score.toFixed(3)}</strong>
            <div class="score-bar-container">
              <div class="score-bar-fill fill-${a.review_priority.toLowerCase()}" style="width: ${Math.round(a.anomaly_score * 100)}%;"></div>
            </div>
          </td>
          <td><span class="badge-priority ${badgeClass}">${a.review_priority}</span></td>
          <td style="max-width: 280px; font-size: 0.8rem; color: var(--text-muted);">${a.diagnostic_reason}</td>
          <td>
            <button class="btn-custom btn-outline-custom" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;" onclick="Dashboard.viewConsumerModal('${a.consumer_id}')">
              <i class="fa-solid fa-eye"></i> Inspect
            </button>
          </td>
        </tr>
      `;
    }).join('');
  },

  isInspecting: false,

  async viewConsumerModal(consumerId) {
    if (this.isInspecting) {
      console.warn("Inspection request already in progress. Ignoring duplicate click.");
      return;
    }
    this.isInspecting = true;

    // Immediately destroy any previous modal chart instance
    if (this.charts.modal) {
      try {
        this.charts.modal.destroy();
      } catch (err) {
        console.warn("Error destroying previous modal chart:", err);
      }
      this.charts.modal = null;
    }

    const titleEl = document.getElementById('modal-consumer-title');
    const bodyEl = document.getElementById('modal-consumer-body');

    if (titleEl) titleEl.textContent = `Consumer Profile: ${consumerId}`;
    if (bodyEl) {
      bodyEl.innerHTML = `
        <div class="spinner-container" id="modal-spinner" style="padding: 2.5rem 1rem; text-align: center;">
          <div class="spinner"></div>
          <div style="margin-top: 0.75rem; color: var(--text-muted); font-size: 0.85rem;">Fetching telemetry and features for ${consumerId}...</div>
        </div>
      `;
    }

    App.openModal('consumer-modal');

    try {
      const resp = await App.fetchJson(`/api/consumers/${encodeURIComponent(consumerId)}`, {}, 10000);
      if (!resp || !resp.success || !resp.data) {
        const errorMsg = (resp && resp.error) ? resp.error : `Consumer ${consumerId} could not be retrieved.`;
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

      let priorityBadge = 'badge-low';
      if (c.review_priority === 'Critical') priorityBadge = 'badge-critical';
      else if (c.review_priority === 'High') priorityBadge = 'badge-high';
      else if (c.review_priority === 'Medium') priorityBadge = 'badge-medium';

      const anomalyScoreStr = (c.anomaly_score != null && !isNaN(c.anomaly_score))
        ? Number(c.anomaly_score).toFixed(4)
        : '--';

      if (bodyEl) {
        bodyEl.innerHTML = `
          <!-- Primary Meta Attributes Grid -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem; background: #0D1526; padding: 1rem; border-radius: var(--radius-md); border: 1px solid #1E2E4E;">
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Feeder</span><br><strong style="color: #FFFFFF;">${c.feeder_id || '--'}</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Meter ID</span><br><strong style="color: #FFFFFF;">${c.meter_id || '--'}</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Tariff</span><br><strong style="color: #FFFFFF;">${c.tariff_category || '--'}</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Sanctioned</span><br><strong style="color: #FFFFFF;">${c.sanctioned_load_kw || 0} kW</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Anomaly Score</span><br><strong style="color: #38BDF8; font-family: var(--font-mono);">${anomalyScoreStr}</strong></div>
            <div><span style="font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase;">Triage Priority</span><br><span class="badge-priority ${priorityBadge}">${c.review_priority || 'Low'}</span></div>
          </div>

          <!-- Diagnostic Explanation -->
          <div style="margin-bottom: 1rem;">
            <h6 style="font-size: 0.8rem; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.35rem;">Diagnostic Explanation</h6>
            <p style="font-size: 0.825rem; color: #F8FAFC; background: rgba(245, 158, 11, 0.1); padding: 0.65rem 0.85rem; border-left: 3px solid #F59E0B; border-radius: 4px; margin: 0; line-height: 1.45;">
              ${c.diagnostic_reason || 'Normative consumption profile across all baseline parameters.'}
            </p>
          </div>

          <!-- Recommended Field Action -->
          <div style="margin-bottom: 1.25rem;">
            <h6 style="font-size: 0.8rem; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.35rem;">Recommended Field Action</h6>
            <p style="font-size: 0.825rem; color: #F8FAFC; background: rgba(59, 130, 246, 0.1); padding: 0.65rem 0.85rem; border-left: 3px solid #3B82F6; border-radius: 4px; margin: 0; line-height: 1.45;">
              ${c.recommended_action || 'Routine automated AMR telemetry surveillance.'}
            </p>
          </div>

          <!-- Engineered Feature Indicators -->
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
              <span style="color: var(--text-secondary);">Peer Relative:</span> <strong style="color: #FFFFFF;">${f.peer_relative_deviation != null ? f.peer_relative_deviation.toFixed(3) : '--'}</strong>
            </div>
          </div>

          <!-- 30-Day Consumption Trend Chart -->
          <h6 style="font-size: 0.8rem; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem;">30-Day Billed Consumption Trend</h6>
          <div style="height: 180px; position: relative;">
            <canvas id="modal-chart"></canvas>
          </div>
        `;
      }

      // Render modal chart safely
      const modalCanvas = document.getElementById('modal-chart');
      if (modalCanvas && daily && daily.labels && daily.labels.length > 0 && typeof Chart !== 'undefined') {
        if (this.charts.modal) {
          this.charts.modal.destroy();
        }
        this.charts.modal = new Chart(modalCanvas, {
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
      const errorMsg = e.message || 'An unexpected error occurred while fetching the consumer profile.';
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
  }
};

document.addEventListener('DOMContentLoaded', () => {
  Dashboard.init();
});
