"""
Dashboard Service for Executive KPI and Overview Visualizations.
All values are queried live from the database.
"""

from typing import Dict, Any, List, Optional
from database.db import query_db

class DashboardService:
    @staticmethod
    def get_summary(feeder_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates 8 primary KPI metrics:
        1. Total Consumers (500)
        2. Total Feeders (5)
        3. Total Electricity Supplied (kWh)
        4. Total Electricity Billed (kWh)
        5. Technical Losses (kWh)
        6. Unexplained Losses (kWh)
        7. Consumers Requiring Inspection (Critical/High/Medium count)
        8. Overall Distribution Loss Percentage
        """
        # Consumer count
        if feeder_id and feeder_id != "all":
            cons_res = query_db("SELECT COUNT(*) as c FROM consumers WHERE feeder_id = ?", (feeder_id,), one=True)
            f_check = query_db("SELECT COUNT(*) as c FROM feeders WHERE feeder_id = ?", (feeder_id,), one=True)
            total_feeders = f_check["c"] if f_check else 0
        else:
            cons_res = query_db("SELECT COUNT(*) as c FROM consumers", one=True)
            fdr_res = query_db("SELECT COUNT(*) as c FROM feeders", one=True)
            total_feeders = fdr_res["c"] if fdr_res else 0

        total_consumers = cons_res["c"] if cons_res else 0

        # Consumers requiring inspection (Critical, High, Medium)
        if feeder_id and feeder_id != "all":
            insp_res = query_db(
                "SELECT COUNT(*) as c FROM theft_predictions WHERE feeder_id = ? AND review_priority IN ('Critical', 'High', 'Medium')",
                (feeder_id,), one=True
            )
        else:
            insp_res = query_db(
                "SELECT COUNT(*) as c FROM theft_predictions WHERE review_priority IN ('Critical', 'High', 'Medium')",
                one=True
            )
        consumers_requiring_inspection = insp_res["c"] if insp_res else 0

        # Energy totals from loss_audit_logs
        where_clauses = []
        params = []
        if feeder_id and feeder_id != "all":
            where_clauses.append("feeder_id = ?")
            params.append(feeder_id)
        if start_date:
            where_clauses.append("audit_date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("audit_date <= ?")
            params.append(end_date)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        audit_query = f"""
            SELECT
                SUM(supplied_energy_kwh) as total_supplied,
                SUM(billed_energy_kwh) as total_billed,
                SUM(cable_loss_kwh) as total_cable,
                SUM(transformer_core_loss_kwh) as total_core,
                SUM(transformer_copper_loss_kwh) as total_copper,
                SUM(technical_loss_kwh) as total_technical,
                SUM(unexplained_loss_kwh) as total_unexplained,
                SUM(total_distribution_loss_kwh) as total_loss
            FROM loss_audit_logs
            {where_sql}
        """
        audit_totals = query_db(audit_query, params, one=True) or {}

        supplied = float(audit_totals.get("total_supplied") or 0.0)
        billed = float(audit_totals.get("total_billed") or 0.0)
        technical = float(audit_totals.get("total_technical") or 0.0)
        unexplained = float(audit_totals.get("total_unexplained") or 0.0)
        total_loss = float(audit_totals.get("total_loss") or (technical + unexplained))

        loss_pct = (total_loss / supplied * 100.0) if supplied > 0 else 0.0

        # System settings for last updated timestamp
        last_run = query_db("SELECT value FROM system_settings WHERE key = 'last_simulation_run'", one=True)
        last_updated = last_run["value"] if last_run and last_run["value"] else "System Active"

        return {
            "total_consumers": total_consumers,
            "total_feeders": total_feeders,
            "total_electricity_supplied_kwh": round(supplied, 2),
            "total_electricity_billed_kwh": round(billed, 2),
            "technical_losses_kwh": round(technical, 2),
            "unexplained_losses_kwh": round(unexplained, 2),
            "total_distribution_losses_kwh": round(total_loss, 2),
            "overall_loss_percentage": round(loss_pct, 2),
            "consumers_requiring_inspection": consumers_requiring_inspection,
            "last_updated": last_updated
        }

    @staticmethod
    def get_charts_data(feeder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Provides datasets for all 6 Executive Dashboard charts:
        1. Electricity supply versus billed energy (30-day time series)
        2. Technical versus unexplained losses (daily comparison)
        3. Feeder-wise energy distribution (bar chart)
        4. 30-day electricity consumption trend
        5. Consumer inspection priority distribution (pie/doughnut)
        6. Recent anomaly detection alerts (top 8 consumers requiring review)
        """
        # Daily audit aggregations
        where_sql = "WHERE feeder_id = ?" if (feeder_id and feeder_id != "all") else ""
        params = [feeder_id] if (feeder_id and feeder_id != "all") else []

        daily_query = f"""
            SELECT
                audit_date,
                day_number,
                SUM(supplied_energy_kwh) as supplied,
                SUM(billed_energy_kwh) as billed,
                SUM(technical_loss_kwh) as technical,
                SUM(unexplained_loss_kwh) as unexplained,
                SUM(total_distribution_loss_kwh) as total_loss
            FROM loss_audit_logs
            {where_sql}
            GROUP BY audit_date, day_number
            ORDER BY day_number ASC
        """
        daily_rows = query_db(daily_query, params)

        dates = [f"Day {r['day_number']}" for r in daily_rows]
        dates_full = [r["audit_date"] for r in daily_rows]
        supplied_daily = [round(r["supplied"], 1) for r in daily_rows]
        billed_daily = [round(r["billed"], 1) for r in daily_rows]
        technical_daily = [round(r["technical"], 1) for r in daily_rows]
        unexplained_daily = [round(r["unexplained"], 1) for r in daily_rows]

        # Feeder-wise breakdown
        feeder_query = """
            SELECT
                f.feeder_id,
                f.name,
                SUM(l.supplied_energy_kwh) as supplied,
                SUM(l.billed_energy_kwh) as billed,
                SUM(l.technical_loss_kwh) as technical,
                SUM(l.unexplained_loss_kwh) as unexplained
            FROM feeders f
            LEFT JOIN loss_audit_logs l ON f.feeder_id = l.feeder_id
            GROUP BY f.feeder_id, f.name
            ORDER BY f.feeder_id
        """
        feeder_rows = query_db(feeder_query)

        feeder_labels = [r["feeder_id"] for r in feeder_rows]
        feeder_supplied = [round(r["supplied"] or 0, 1) for r in feeder_rows]
        feeder_billed = [round(r["billed"] or 0, 1) for r in feeder_rows]
        feeder_tech = [round(r["technical"] or 0, 1) for r in feeder_rows]
        feeder_unexplained = [round(r["unexplained"] or 0, 1) for r in feeder_rows]

        # Priority distribution
        priority_query = f"""
            SELECT review_priority, COUNT(*) as count
            FROM theft_predictions
            {where_sql}
            GROUP BY review_priority
        """
        priority_rows = query_db(priority_query, params)
        priority_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for r in priority_rows:
            priority_counts[r["review_priority"]] = r["count"]

        # Recent anomaly detection alerts (top 8 highest anomaly score)
        alert_where = "WHERE t.feeder_id = ?" if (feeder_id and feeder_id != "all") else ""
        alert_query = f"""
            SELECT
                t.consumer_id,
                t.feeder_id,
                t.tariff_category,
                t.anomaly_score,
                t.review_priority,
                t.diagnostic_reason,
                t.recommended_action,
                c.sanctioned_load_kw
            FROM theft_predictions t
            JOIN consumers c ON t.consumer_id = c.consumer_id
            {alert_where}
            ORDER BY t.anomaly_score DESC
            LIMIT 8
        """
        alerts = query_db(alert_query, params)

        return {
            "daily_trend": {
                "labels": dates,
                "dates_full": dates_full,
                "supplied": supplied_daily,
                "billed": billed_daily,
                "technical": technical_daily,
                "unexplained": unexplained_daily
            },
            "feeder_distribution": {
                "labels": feeder_labels,
                "supplied": feeder_supplied,
                "billed": feeder_billed,
                "technical": feeder_tech,
                "unexplained": feeder_unexplained
            },
            "priority_distribution": priority_counts,
            "recent_alerts": alerts
        }

