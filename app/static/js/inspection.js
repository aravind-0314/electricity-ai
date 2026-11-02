/**
 * Inspection Worklist Interactive Management Logic
 */

const Inspection = {
  currentPage: 1,
  totalPages: 1,
  searchTimer: null,
  cachedRecords: {},

  init() {
    this.loadWorklist(1);
  },

  onSearchInput() {
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.loadWorklist(1);
    }, 300);
  },

  async loadWorklist(page = 1) {
    this.currentPage = page;
    const feeder = document.getElementById('insp-feeder').value;
    const priority = document.getElementById('insp-priority').value;
    const status = document.getElementById('insp-status').value;
    const search = document.getElementById('insp-search').value.trim();
    const sort = document.getElementById('insp-sort').value;

    // Update CSV export link
    const exportBtn = document.getElementById('btn-export-inspection');
    if (exportBtn) {
      exportBtn.href = `/api/export/inspection?feeder_id=${feeder}&priority=${priority}&status=${status}`;
    }

    const tbody = document.getElementById('worklist-table-body');
    tbody.innerHTML = `<tr><td colspan="11" class="text-center" style="padding: 2.5rem;"><div class="spinner-container"><div class="spinner"></div><div>Loading inspection worklist...</div></div></td></tr>`;

    let url = `/api/inspection?page=${page}&per_page=12&sort_by=anomaly_score&sort_order=${sort}`;
    if (feeder !== 'all') url += `&feeder_id=${feeder}`;
    if (priority !== 'all') url += `&priority=${priority}`;
    if (status !== 'all') url += `&status=${status}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    try {
      const resp = await App.fetchJson(url);
      if (!resp.success) return;

      const d = resp.data;
      this.totalPages = d.total_pages;

      // Update status summary counters
      if (d.status_summary) {
        document.getElementById('status-pending').textContent = d.status_summary['Pending'] || 0;
        document.getElementById('status-scheduled').textContent = d.status_summary['Scheduled'] || 0;
        document.getElementById('status-progress').textContent = d.status_summary['In Progress'] || 0;
        document.getElementById('status-completed').textContent = d.status_summary['Completed'] || 0;
        document.getElementById('status-verified').textContent = d.status_summary['Not Suspicious After Verification'] || 0;
      }

      if (!d.records || d.records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" class="empty-state">No matching inspection records found.</td></tr>`;
        return;
      }

      this.cachedRecords = {};
      tbody.innerHTML = d.records.map(r => {
        this.cachedRecords[r.inspection_id] = r;

        let priorityBadge = 'badge-low';
        if (r.priority === 'Critical') priorityBadge = 'badge-critical';
        else if (r.priority === 'High') priorityBadge = 'badge-high';
        else if (r.priority === 'Medium') priorityBadge = 'badge-medium';

        let statusBadge = 'badge-pending';
        if (r.inspection_status === 'Scheduled') statusBadge = 'badge-scheduled';
        else if (r.inspection_status === 'In Progress') statusBadge = 'badge-in-progress';
        else if (r.inspection_status === 'Completed') statusBadge = 'badge-completed';
        else if (r.inspection_status === 'Not Suspicious After Verification') statusBadge = 'badge-verified';

        return `
          <tr>
            <td><strong style="color: #FFFFFF;">${r.consumer_id}</strong></td>
            <td><span style="font-weight: 500; color: #CBD5E1;">${r.feeder_id}</span></td>
            <td>${r.tariff_category}</td>
            <td>${r.sanctioned_load_kw} kW</td>
            <td style="font-family: var(--font-mono);">${r.mean_daily_consumption.toFixed(2)} kWh</td>
            <td><strong style="color: #FFFFFF; font-family: var(--font-mono);">${r.anomaly_score.toFixed(3)}</strong></td>
            <td><span class="badge-priority ${priorityBadge}">${r.priority}</span></td>
            <td style="max-width: 240px; font-size: 0.78rem; color: var(--text-secondary);">${r.diagnostic_reason}</td>
            <td><span class="badge-status ${statusBadge}">${r.inspection_status}</span></td>
            <td style="max-width: 180px; font-size: 0.78rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${r.remarks || ''}">
              ${r.remarks ? r.remarks : '<em>None</em>'}
            </td>
            <td>
              <button class="btn-custom btn-primary-custom" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="Inspection.openEditModal('${r.inspection_id}')">
                <i class="fa-solid fa-pen-to-square"></i> Update
              </button>
            </td>
          </tr>
        `;
      }).join('');

      document.getElementById('insp-page-info').textContent = `Showing page ${d.page} of ${d.total_pages} (${d.total_records} candidates)`;
      document.getElementById('insp-btn-prev').disabled = d.page <= 1;
      document.getElementById('insp-btn-next').disabled = d.page >= d.total_pages;

    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="11" class="alert alert-danger">Error loading inspection records.</td></tr>`;
    }
  },

  changePage(delta) {
    const newPage = this.currentPage + delta;
    if (newPage >= 1 && newPage <= this.totalPages) {
      this.loadWorklist(newPage);
    }
  },

  openEditModal(inspectionId) {
    const r = this.cachedRecords[inspectionId];
    if (!r) return;

    document.getElementById('edit-inspection-id').value = r.inspection_id;
    document.getElementById('edit-consumer-id').value = `${r.consumer_id} (${r.feeder_id})`;
    document.getElementById('edit-status-select').value = r.inspection_status;
    document.getElementById('edit-inspector').value = r.inspected_by || '';
    document.getElementById('edit-remarks').value = r.remarks || '';

    App.openModal('edit-inspection-modal');
  },

  async submitUpdate(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-save-inspection');
    btn.disabled = true;
    btn.textContent = "Saving...";

    const inspectionId = document.getElementById('edit-inspection-id').value;
    const status = document.getElementById('edit-status-select').value;
    const inspector = document.getElementById('edit-inspector').value.trim();
    const remarks = document.getElementById('edit-remarks').value.trim();

    try {
      const resp = await App.fetchJson(`/api/inspection/${inspectionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inspection_status: status,
          inspected_by: inspector,
          remarks: remarks
        })
      });

      if (resp.success) {
        App.showToast(`Inspection status for ${resp.record.consumer_id} updated to "${status}"!`, "success");
        App.closeModal('edit-inspection-modal');
        this.loadWorklist(this.currentPage);
      }
    } catch (err) {
      App.showToast("Update failed: " + err.message, "danger");
    } finally {
      btn.disabled = false;
      btn.textContent = "Save & Persist Changes";
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  Inspection.init();
});

