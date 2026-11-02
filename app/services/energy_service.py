"""
Energy Accounting Service.

Implements rigorous energy balance accounting:
Supplied Energy = Billed Energy + Technical Losses + Unexplained Losses
Values reconcile mathematically with explicit residual tracking.
"""

from typing import Dict, Any, List, Optional
import io
import csv
from database.db import query_db

class EnergyService:
    @staticmethod
    def get_accounting_summary(feeder_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Summary cards data with reconciled totals."""
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

        query = f"""
            SELECT
                SUM(supplied_energy_kwh) as supplied,
                SUM(billed_energy_kwh) as billed,
                SUM(cable_loss_kwh) as cable,
                SUM(transformer_core_loss_kwh) as core,
                SUM(transformer_copper_loss_kwh) as copper,
                SUM(technical_loss_kwh) as technical,
                SUM(unexplained_loss_kwh) as unexplained,
                SUM(total_distribution_loss_kwh) as total_loss,
                SUM(reconciliation_residual_kwh) as residual
            FROM loss_audit_logs
            {where_sql}
        """
        row = query_db(query, params, one=True) or {}

        supplied = float(row.get("supplied") or 0.0)
        billed = float(row.get("billed") or 0.0)
        cable = float(row.get("cable") or 0.0)
        core = float(row.get("core") or 0.0)
        copper = float(row.get("copper") or 0.0)
        technical = float(row.get("technical") or (cable + core + copper))
        unexplained = float(row.get("unexplained") or 0.0)
        total_loss = float(row.get("total_loss") or (technical + unexplained))
        residual = float(row.get("residual") or 0.0)

        loss_pct = (total_loss / supplied * 100.0) if supplied > 0 else 0.0
        tech_pct = (technical / supplied * 100.0) if supplied > 0 else 0.0
        unexplained_pct = (unexplained / supplied * 100.0) if supplied > 0 else 0.0

        return {
            "supplied_energy_kwh": round(supplied, 2),
            "billed_energy_kwh": round(billed, 2),
            "cable_loss_kwh": round(cable, 2),
            "transformer_core_loss_kwh": round(core, 2),
            "transformer_copper_loss_kwh": round(copper, 2),
            "total_technical_loss_kwh": round(technical, 2),
            "unexplained_loss_kwh": round(unexplained, 2),
            "total_distribution_loss_kwh": round(total_loss, 2),
            "loss_percentage": round(loss_pct, 2),
            "technical_loss_percentage": round(tech_pct, 2),
            "unexplained_loss_percentage": round(unexplained_pct, 2),
            "reconciliation_residual_kwh": round(residual, 4),
            "is_reconciled": abs(residual) < 1.0
        }

    @staticmethod
    def get_daily_accounting(
        feeder_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 15
    ) -> Dict[str, Any]:
        """Paginated daily accounting records with filters."""
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

        # Count total rows
        count_sql = f"SELECT COUNT(*) as c FROM loss_audit_logs {where_sql}"
        count_row = query_db(count_sql, params, one=True)
        total_rows = count_row["c"] if count_row else 0
        total_pages = (total_rows + per_page - 1) // per_page

        offset = (page - 1) * per_page
        query = f"""
            SELECT
                id, audit_date, feeder_id, day_number,
                supplied_energy_kwh, billed_energy_kwh,
                cable_loss_kwh, transformer_core_loss_kwh, transformer_copper_loss_kwh,
                technical_loss_kwh, unexplained_loss_kwh, total_distribution_loss_kwh,
                loss_percentage, reconciliation_residual_kwh
            FROM loss_audit_logs
            {where_sql}
            ORDER BY day_number ASC, feeder_id ASC
            LIMIT ? OFFSET ?
        """
        rows = query_db(query, params + [per_page, offset])

        return {
            "records": rows,
            "total_records": total_rows,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }

    @staticmethod
    def get_feeder_breakdown() -> List[Dict[str, Any]]:
        """Feeder-wise accounting breakdown cards."""
        query = """
            SELECT
                f.feeder_id,
                f.name,
                f.substation_name,
                f.length_km,
                SUM(l.supplied_energy_kwh) as supplied,
                SUM(l.billed_energy_kwh) as billed,
                SUM(l.technical_loss_kwh) as technical,
                SUM(l.unexplained_loss_kwh) as unexplained,
                SUM(l.total_distribution_loss_kwh) as total_loss
            FROM feeders f
            LEFT JOIN loss_audit_logs l ON f.feeder_id = l.feeder_id
            GROUP BY f.feeder_id, f.name, f.substation_name, f.length_km
            ORDER BY f.feeder_id
        """
        rows = query_db(query)
        result = []
        for r in rows:
            sup = float(r["supplied"] or 0)
            loss = float(r["total_loss"] or 0)
            pct = (loss / sup * 100.0) if sup > 0 else 0
            result.append({
                "feeder_id": r["feeder_id"],
                "name": r["name"],
                "substation": r["substation_name"],
                "length_km": r["length_km"],
                "supplied_kwh": round(sup, 2),
                "billed_kwh": round(float(r["billed"] or 0), 2),
                "technical_kwh": round(float(r["technical"] or 0), 2),
                "unexplained_kwh": round(float(r["unexplained"] or 0), 2),
                "total_loss_kwh": round(loss, 2),
                "loss_percentage": round(pct, 2)
            })
        return result

    @staticmethod
    def get_energy_flow_data() -> Dict[str, Any]:
        """
        Generates energy balance flow breakdown for visualizations:
        Supplied (100%) -> Billed (X%) + Technical (Y%) + Unexplained (Z%)
        Technical -> Cable Loss + Transformer Core + Transformer Copper
        """
        summary = EnergyService.get_accounting_summary()
        return {
            "supplied": summary["supplied_energy_kwh"],
            "billed": summary["billed_energy_kwh"],
            "technical": summary["total_technical_loss_kwh"],
            "unexplained": summary["unexplained_loss_kwh"],
            "cable": summary["cable_loss_kwh"],
            "core": summary["transformer_core_loss_kwh"],
            "copper": summary["transformer_copper_loss_kwh"]
        }

    @staticmethod
    def export_daily_csv(feeder_id: Optional[str] = None) -> str:
        """Generate CSV string of daily energy accounting logs."""
        where_sql = "WHERE feeder_id = ?" if (feeder_id and feeder_id != "all") else ""
        params = [feeder_id] if (feeder_id and feeder_id != "all") else []

        query = f"""
            SELECT
                audit_date, feeder_id, day_number,
                supplied_energy_kwh, billed_energy_kwh,
                cable_loss_kwh, transformer_core_loss_kwh, transformer_copper_loss_kwh,
                technical_loss_kwh, unexplained_loss_kwh, total_distribution_loss_kwh,
                loss_percentage, reconciliation_residual_kwh
            FROM loss_audit_logs
            {where_sql}
            ORDER BY day_number ASC, feeder_id ASC
        """
        rows = query_db(query, params)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Audit Date", "Feeder ID", "Day Number",
            "Supplied Energy (kWh)", "Billed Energy (kWh)",
            "Cable Loss (kWh)", "Transformer Core Loss (kWh)", "Transformer Copper Loss (kWh)",
            "Technical Loss (kWh)", "Unexplained Loss (kWh)", "Total Distribution Loss (kWh)",
            "Loss Percentage (%)", "Reconciliation Residual (kWh)"
        ])

        for r in rows:
            writer.writerow([
                r["audit_date"], r["feeder_id"], r["day_number"],
                r["supplied_energy_kwh"], r["billed_energy_kwh"],
                r["cable_loss_kwh"], r["transformer_core_loss_kwh"], r["transformer_copper_loss_kwh"],
                r["technical_loss_kwh"], r["unexplained_loss_kwh"], r["total_distribution_loss_kwh"],
                r["loss_percentage"], r["reconciliation_residual_kwh"]
            ])

        return output.getvalue()

