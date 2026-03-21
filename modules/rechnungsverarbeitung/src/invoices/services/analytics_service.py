"Dashboard Analytics Service — KPIs, Charts, Trends."
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import text
from shared.db.session import get_session
logger = logging.getLogger(__name__)

class AnalyticsService:
    def get_dashboard(self, tenant_id: str, days: int = 90) -> dict[str, Any]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        return {"kpis": self._get_kpis(tenant_id, cutoff), "status_distribution": self._get_status_distribution(tenant_id), "timeline": self._get_timeline(tenant_id, cutoff), "kontierung_performance": self._get_kontierung_performance(tenant_id, cutoff), "recent_activity": self._get_recent_activity(tenant_id, limit=15), "processing_speed": self._get_processing_speed(tenant_id, cutoff), "period_days": days, "generated_at": datetime.utcnow().isoformat()}

    def _get_kpis(self, tenant_id, cutoff):
        with get_session() as s:
            total = s.execute(text("SELECT COUNT(*) FROM invoices WHERE tenant_id = :t"), {"t": tenant_id}).scalar() or 0
            period_total = s.execute(text("SELECT COUNT(*) FROM invoices WHERE tenant_id = :t AND uploaded_at >= :cutoff"), {"t": tenant_id, "cutoff": cutoff}).scalar() or 0
            pending = s.execute(text("SELECT COUNT(*) FROM invoices WHERE tenant_id = :t AND status IN ('uploaded','classified','validated','suggested')"), {"t": tenant_id}).scalar() or 0
            approved = s.execute(text("SELECT COUNT(*) FROM invoices WHERE tenant_id = :t AND status = 'approved'"), {"t": tenant_id}).scalar() or 0
            exported = s.execute(text("SELECT COUNT(*) FROM invoices WHERE tenant_id = :t AND status IN ('exported','archived')"), {"t": tenant_id}).scalar() or 0
            total_events = s.execute(text("SELECT COUNT(*) FROM invoice_events WHERE tenant_id = :t AND created_at >= :cutoff"), {"t": tenant_id, "cutoff": cutoff}).scalar() or 0
        rate = (exported / total * 100) if total > 0 else 0
        return {"total_invoices": total, "period_invoices": period_total, "pending_review": pending, "approved": approved, "exported": exported, "completion_rate": round(rate, 1), "total_events": total_events}

    def _get_status_distribution(self, tenant_id):
        with get_session() as s:
            rows = s.execute(text("SELECT status, COUNT(*) as cnt FROM invoices WHERE tenant_id = :t GROUP BY status ORDER BY cnt DESC"), {"t": tenant_id}).fetchall()
        colors = {"uploaded":"#3b82f6","classified":"#6366f1","validated":"#8b5cf6","suggested":"#f59e0b","approved":"#10b981","exported":"#06b6d4","archived":"#64748b","rejected":"#ef4444","error":"#dc2626"}
        return [{"status": r[0], "count": r[1], "color": colors.get(r[0], "#94a3b8")} for r in rows]

    def _get_timeline(self, tenant_id, cutoff):
        with get_session() as s:
            rows = s.execute(text("SELECT date_trunc('week', uploaded_at)::date as week, COUNT(*) as cnt FROM invoices WHERE tenant_id = :t AND uploaded_at >= :cutoff GROUP BY week ORDER BY week ASC"), {"t": tenant_id, "cutoff": cutoff}).fetchall()
        return [{"week": r[0].isoformat(), "count": r[1]} for r in rows]

    def _get_kontierung_performance(self, tenant_id, cutoff):
        with get_session() as s:
            rows = s.execute(text("SELECT e.details FROM invoice_events e WHERE e.tenant_id = :t AND e.event_type = 'kontierung_suggested' AND e.created_at >= :cutoff ORDER BY e.created_at DESC"), {"t": tenant_id, "cutoff": cutoff}).fetchall()
        models, confidences, konten, high_conf, low_conf = {}, [], {}, 0, 0
        for row in rows:
            d = row[0] if isinstance(row[0], dict) else {}
            m = d.get("model", "unknown"); models[m] = models.get(m, 0) + 1
            c = d.get("confidence", 0)
            if c:
                confidences.append(c)
                if c >= 0.85: high_conf += 1
                elif c < 0.7: low_conf += 1
            k = d.get("konto", "")
            if k: konten[k] = konten.get(k, 0) + 1
        avg = sum(confidences) / len(confidences) if confidences else 0
        top = sorted(konten.items(), key=lambda x: -x[1])[:8]
        return {"total": len(rows), "models": models, "avg_confidence": round(avg, 3), "high_confidence_count": high_conf, "low_confidence_count": low_conf, "top_konten": [{"konto": k, "count": v} for k, v in top], "confidence_distribution": {"high": high_conf, "medium": len(confidences) - high_conf - low_conf, "low": low_conf}}

    def _get_recent_activity(self, tenant_id, limit=15):
        with get_session() as s:
            rows = s.execute(text("SELECT e.document_id, e.event_type, e.status_from, e.status_to, e.actor, e.created_at, i.file_name FROM invoice_events e LEFT JOIN invoices i ON e.document_id = i.document_id AND e.tenant_id = i.tenant_id WHERE e.tenant_id = :t ORDER BY e.created_at DESC LIMIT :lim"), {"t": tenant_id, "lim": limit}).fetchall()
        icons = {"uploaded":"U","classified":"T","validated":"V","kontierung_suggested":"AI","approved":"OK","exported":"EX","archived":"AR","rejected":"X"}
        return [{"document_id": r[0][:12] if r[0] else "", "event_type": r[1], "icon": icons.get(r[1], "?"), "from": r[2], "to": r[3], "actor": r[4], "timestamp": r[5].isoformat() if r[5] else None, "file_name": r[6]} for r in rows]

    def _get_processing_speed(self, tenant_id, cutoff):
        with get_session() as s:
            result = s.execute(text("SELECT AVG(EXTRACT(EPOCH FROM ((SELECT MIN(e2.created_at) FROM invoice_events e2 WHERE e2.document_id = e1.document_id AND e2.tenant_id = e1.tenant_id AND e2.status_to = 'approved') - e1.created_at))) FROM invoice_events e1 WHERE e1.tenant_id = :t AND e1.event_type = 'uploaded' AND e1.created_at >= :cutoff AND EXISTS (SELECT 1 FROM invoice_events e2 WHERE e2.document_id = e1.document_id AND e2.tenant_id = e1.tenant_id AND e2.status_to = 'approved')"), {"t": tenant_id, "cutoff": cutoff}).scalar()
        avg_s = result or 0
        fmt = f"{avg_s:.0f}s" if avg_s < 60 else (f"{avg_s/60:.1f}min" if avg_s < 3600 else f"{avg_s/3600:.1f}h") if avg_s > 0 else "—"
        return {"avg_seconds_to_approval": round(avg_s, 1), "formatted": fmt}
