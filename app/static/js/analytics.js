/**
 * Analytics and Model Insights Visualizations
 */

const Analytics = {
  charts: {},

  init() {
    this.loadData();
  },

  async loadData() {
    try {
      const resp = await App.fetchJson('/api/analytics');
      if (!resp.success) return;

      const a = resp.analytics;

      // Populate Metric Cards
      document.getElementById('metric-accuracy').textContent = `${(a.metrics.accuracy * 100).toFixed(2)}%`;
      document.getElementById('metric-precision').textContent = `${(a.metrics.precision * 100).toFixed(2)}%`;
      document.getElementById('metric-recall').textContent = `${(a.metrics.recall * 100).toFixed(2)}%`;
      document.getElementById('metric-f1').textContent = a.metrics.f1_score.toFixed(4);
      document.getElementById('metric-roc').textContent = a.metrics.roc_auc ? a.metrics.roc_auc.toFixed(4) : 'N/A';

      // Populate Confusion Matrix
      const cm = a.metrics.confusion_matrix || [[130, 2], [2, 16]];
      document.getElementById('cm-tn').textContent = cm[0][0];
      document.getElementById('cm-fp').textContent = cm[0][1];
      document.getElementById('cm-fn').textContent = cm[1][0];
      document.getElementById('cm-tp').textContent = cm[1][1];

      // Render Charts
      this.renderGridDynamics(a.grid_dynamics);
      this.renderFeatureImportance(a.metrics.feature_importance);
      this.renderScoreDistribution(a.iforest_distribution);
      this.renderFeederLoss(a.feeder_loss_comparison);
      this.renderConsumptionDistribution(a.consumption_distribution);

    } catch (e) {
      console.error("Analytics load error:", e);
    }
  },

  renderGridDynamics(dyn) {
    const ctx = document.getElementById('chart-grid-dynamics');
    if (!ctx || !dyn) return;
    if (typeof Chart === 'undefined') return;
    if (this.charts.dynamics) this.charts.dynamics.destroy();

    this.charts.dynamics = new Chart(ctx, {
      type: 'line',
      data: {
        labels: dyn.labels,
        datasets: [
          {
            label: 'Peak Load (kWh/h)',
            data: dyn.peak_load,
            borderColor: '#EF4444',
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.25
          },
          {
            label: 'Average Load (kWh/h)',
            data: dyn.avg_load,
            borderColor: '#3B82F6',
            backgroundColor: 'rgba(59, 130, 246, 0.12)',
            fill: true,
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.25
          },
          {
            label: 'Baseload (kWh/h)',
            data: dyn.base_load,
            borderColor: '#06B6D4',
            backgroundColor: 'transparent',
            borderWidth: 1.75,
            pointRadius: 1.5,
            tension: 0.25
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

  renderFeatureImportance(fi) {
    const ctx = document.getElementById('chart-feature-importance');
    if (!ctx || !fi) return;
    if (typeof Chart === 'undefined') return;
    if (this.charts.fi) this.charts.fi.destroy();

    const labels = Object.keys(fi);
    const values = Object.values(fi);

    // Nicely format feature names
    const prettyLabels = labels.map(l => l.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));

    this.charts.fi = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: prettyLabels,
        datasets: [{
          label: 'Gini Importance',
          data: values,
          backgroundColor: '#06B6D4',
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0F172A',
            titleColor: '#F8FAFC',
            bodyColor: '#94A3B8',
            borderColor: '#1E293B',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94A3B8', font: { size: 9 } }
          },
          y: {
            grid: { display: false },
            ticks: { color: '#CBD5E1', font: { size: 9, family: "'Inter', sans-serif" } }
          }
        }
      }
    });
  },

  renderScoreDistribution(dist) {
    const ctx = document.getElementById('chart-score-dist');
    if (!ctx || !dist) return;
    if (typeof Chart === 'undefined') return;
    if (this.charts.scores) this.charts.scores.destroy();

    this.charts.scores = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: dist.labels,
        datasets: [{
          label: 'Number of Consumers',
          data: dist.counts,
          backgroundColor: dist.labels.map((_, i) => {
            if (i >= 7) return '#EF4444'; // Critical
            if (i >= 6) return '#F59E0B'; // High
            if (i >= 4) return '#3B82F6'; // Medium
            return '#64748B'; // Low
          }),
          borderRadius: 4
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
            ticks: { color: '#CBD5E1', font: { size: 9, family: "'Inter', sans-serif" } }
          }
        }
      }
    });
  },

  renderFeederLoss(comp) {
    const ctx = document.getElementById('chart-feeder-loss');
    if (!ctx || !comp) return;
    if (typeof Chart === 'undefined') return;
    if (this.charts.loss) this.charts.loss.destroy();

    this.charts.loss = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: comp.labels,
        datasets: [
          {
            label: 'Technical Loss (kWh)',
            data: comp.technical,
            backgroundColor: '#F59E0B',
            borderRadius: 4
          },
          {
            label: 'Unexplained Loss (kWh)',
            data: comp.unexplained,
            backgroundColor: '#EF4444',
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
            ticks: { color: '#CBD5E1', font: { size: 10, family: "'Inter', sans-serif" } }
          }
        }
      }
    });
  },

  renderConsumptionDistribution(dist) {
    const ctx = document.getElementById('chart-consumption-dist');
    if (!ctx || !dist) return;
    if (typeof Chart === 'undefined') return;
    if (this.charts.cons) this.charts.cons.destroy();

    this.charts.cons = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: dist.labels,
        datasets: [{
          label: 'Consumers',
          data: dist.counts,
          backgroundColor: '#6366F1',
          borderRadius: 4
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
            ticks: { color: '#CBD5E1', font: { size: 8 }, maxRotation: 45 }
          }
        }
      }
    });
  }
};

document.addEventListener('DOMContentLoaded', () => {
  Analytics.init();
});

