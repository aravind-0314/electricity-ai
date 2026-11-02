"""
Inspection Management Service.

Handles consumer inspection records, status transitions, remarks, and scheduling.
Persists all updates to SQLite table: inspection_records.
"""

import io
import csv
import datetime
from typing import Dict, Any, List, Optional
from database.db import query_db, execute_db

VALID_STATUSES = [
    "Pending",
    "Scheduled",
    "In Progress",
    "Completed",
    "Not Suspicious After Verification"
]

class InspectionService:
    @staticmethod
    def get_worklist(
        feeder_id: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "anomaly_score",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 15
    ) -> Dict[str, Any]:
        """Paginated, filtered, and sorted inspection candidates."""
        where_clauses = []
        params = []

        if feeder_id and feeder_id != "all":
            where_clauses.append("i.feeder_id = ?")
            params.append(feeder_id)
        if priority and priority != "all":
            where_clauses.append("i.priority = ?")
            params.append(priority)
        if status and status != "all":
            where_clauses.append("i.inspection_status = ?")
            params.append(status)
        if search:
            where_clauses.append("(i.consumer_id LIKE ? OR i.inspection_id LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        allowed_sort = {
            "consumer_id": "i.consumer_id",
            "feeder_id": "i.feeder_id",
            "tariff_category": "i.tariff_category",
            "sanctioned_load_kw": "i.sanctioned_load_kw",
            "mean_daily_consumption": "i.mean_daily_consumption",
            "anomaly_score": "i.anomaly_score",
            "priority": "i.anomaly_score",
            "inspection_status": "i.inspection_status",
            "updated_at": "i.updated_at"
        }
        order_col = allowed_sort.get(sort_by, "i.anomaly_score")
        order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

        count_sql = f"SELECT COUNT(*) as c FROM inspection_records i {where_sql}"
        count_row = query_db(count_sql, params, one=True)
        total_rows = count_row["c"] if count_row else 0
        total_pages = (total_rows + per_page - 1) // per_page

        offset = (page - 1) * per_page
        query = f"""
            SELECT
                i.inspection_id,
                i.consumer_id,
                i.feeder_id,
                i.tariff_category,
                i.sanctioned_load_kw,
                i.mean_daily_consumption,
                i.anomaly_score,
                i.priority,
                i.diagnostic_reason,
                i.recommended_action,
                i.inspection_status,
                i.remarks,
                i.scheduled_date,
                i.inspected_by,
                i.updated_at
            FROM inspection_records i
            {where_sql}
            ORDER BY {order_col} {order_dir}
            LIMIT ? OFFSET ?
        """
        rows = query_db(query, params + [per_page, offset])

        # Status summary counts
        status_counts_query = "SELECT inspection_status, COUNT(*) as c FROM inspection_records GROUP BY inspection_status"
        status_rows = query_db(status_counts_query)
        status_summary = {s: 0 for s in VALID_STATUSES}
        for r in status_rows:
            if r["inspection_status"] in status_summary:
                status_summary[r["inspection_status"]] = r["c"]

        return {
            "records": rows,
            "total_records": total_rows,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "status_summary": status_summary
        }

    @staticmethod
    def update_inspection(
        inspection_id: str,
        status: Optional[str] = None,
        remarks: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        inspected_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update inspection status and remarks in SQLite."""
        existing = query_db("SELECT * FROM inspection_records WHERE inspection_id = ?", (inspection_id,), one=True)
        if not existing:
            return {"success": False, "error": f"Inspection record {inspection_id} not found."}

        new_status = status if (status in VALID_STATUSES) else existing["inspection_status"]
        new_remarks = remarks if remarks is not None else existing["remarks"]
        new_date = scheduled_date if scheduled_date is not None else existing["scheduled_date"]
        new_inspector = inspected_by if inspected_by is not None else existing["inspected_by"]
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        execute_db(
            """UPDATE inspection_records
               SET inspection_status = ?, remarks = ?, scheduled_date = ?, inspected_by = ?, updated_at = ?
               WHERE inspection_id = ?""",
            (new_status, new_remarks, new_date, new_inspector, now_str, inspection_id)
        )

        updated = query_db("SELECT * FROM inspection_records WHERE inspection_id = ?", (inspection_id,), one=True)
        return {"success": True, "record": updated}

    @staticmethod
    def export_worklist_csv(
        feeder_id: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None
    ) -> str:
        """Export inspection worklist to CSV."""
        where_clauses = []
        params = []
        if feeder_id and feeder_id != "all":
            where_clauses.append("i.feeder_id = ?")
            params.append(feeder_id)
        if priority and priority != "all":
            where_clauses.append("i.priority = ?")
            params.append(priority)
        if status and status != "all":
            where_clauses.append("i.inspection_status = ?")
            params.append(status)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        query = f"""
            SELECT
                i.inspection_id, i.consumer_id, i.feeder_id, i.tariff_category,
                i.sanctioned_load_kw, i.mean_daily_consumption, i.anomaly_score,
                i.priority, i.diagnostic_reason, i.recommended_action,
                i.inspection_status, i.remarks, i.scheduled_date, i.inspected_by, i.updated_at
            FROM inspection_records i
            {where_sql}
            ORDER BY i.anomaly_score DESC
        """
        rows = query_db(query, params)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Inspection ID", "Consumer ID", "Feeder ID", "Tariff Category",
            "Sanctioned Load (kW)", "Mean Daily (kWh)", "Anomaly Score", "Priority",
            "Diagnostic Reason", "Recommended Action", "Status", "Remarks",
            "Scheduled Date", "Inspected By", "Last Updated"
        ])

        for r in rows:
            writer.writerow([
                r["inspection_id"], r["consumer_id"], r["feeder_id"], r["tariff_category"],
                r["sanctioned_load_kw"], r["mean_daily_consumption"], r["anomaly_score"], r["priority"],
                r["diagnostic_reason"], r["recommended_action"], r["inspection_status"], r["remarks"],
                r["scheduled_date"], r["inspected_by"], r["updated_at"]
            ])

        return output.getvalue()

