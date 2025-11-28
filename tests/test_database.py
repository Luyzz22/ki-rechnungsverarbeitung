"""
Tests für Repository-Funktionen in database.py
"""

import pytest
import database


class TestFindPotentialDuplicates:
    """Tests für find_potential_duplicates()"""
    
    def test_find_by_invoice_number(self, sample_invoices):
        """Findet Duplikate anhand Rechnungsnummer"""
        results = database.find_potential_duplicates(
            invoice_number="INV-001",
            supplier_name="Unbekannt",
            gross_amount=0
        )
        assert len(results) >= 1
        assert any(r["invoice_number"] == "INV-001" for r in results)
    
    def test_find_by_supplier_and_amount(self, sample_invoices):
        """Findet Duplikate anhand Lieferant + Betrag"""
        results = database.find_potential_duplicates(
            invoice_number="NICHT-EXISTENT",
            supplier_name="Lieferant A",
            gross_amount=119.0
        )
        assert len(results) >= 1
    
    def test_exclude_job(self, sample_invoices):
        """Excludiert bestimmten Job"""
        results = database.find_potential_duplicates(
            invoice_number="INV-001",
            supplier_name="",
            gross_amount=0,
            exclude_job_id="job-001"
        )
        # Sollte nur INV-001 aus job-002 finden
        assert all(r["job_id"] != "job-001" for r in results)


class TestGetInvoiceStats:
    """Tests für get_invoice_stats()"""
    
    def test_global_stats(self, sample_invoices):
        """Globale Statistiken ohne User-Filter"""
        stats = database.get_invoice_stats()
        assert stats["total_invoices"] == 6
        assert stats["total_gross"] > 0
        assert stats["unique_suppliers"] == 3
    
    def test_user_stats(self, sample_invoices):
        """Statistiken für bestimmten User"""
        stats = database.get_invoice_stats(user_id=1)
        assert stats["total_invoices"] == 5  # job-001 + job-002
    
    def test_empty_stats(self, test_db):
        """Leere Statistiken bei keinen Daten"""
        stats = database.get_invoice_stats()
        assert stats["total_invoices"] == 0


class TestGetJobsByStatus:
    """Tests für get_jobs_by_status()"""
    
    def test_get_completed_jobs(self, sample_jobs):
        """Findet alle completed Jobs"""
        results = database.get_jobs_by_status("completed")
        assert len(results) == 3
    
    def test_get_processing_jobs(self, sample_jobs):
        """Findet alle processing Jobs"""
        results = database.get_jobs_by_status("processing")
        assert len(results) == 1
        assert results[0]["job_id"] == "job-003"
    
    def test_filter_by_user(self, sample_jobs):
        """Filtert nach User"""
        results = database.get_jobs_by_status("completed", user_id=1)
        assert len(results) == 2
        assert all(r["user_id"] == 1 for r in results)


class TestGetInvoicesBySupplier:
    """Tests für get_invoices_by_supplier()"""
    
    def test_find_supplier(self, sample_invoices):
        """Findet Rechnungen eines Lieferanten"""
        results = database.get_invoices_by_supplier("Lieferant A")
        assert len(results) == 3
    
    def test_partial_match(self, sample_invoices):
        """Findet mit Teilstring"""
        results = database.get_invoices_by_supplier("Lieferant")
        assert len(results) == 6
    
    def test_not_found(self, sample_invoices):
        """Keine Ergebnisse bei unbekanntem Lieferant"""
        results = database.get_invoices_by_supplier("Nicht Existent GmbH")
        assert len(results) == 0


class TestGetMonthlySummary:
    """Tests für get_monthly_summary()"""
    
    def test_monthly_aggregation(self, sample_invoices):
        """Aggregiert nach Monat"""
        results = database.get_monthly_summary()
        assert len(results) >= 1
        assert all("month" in r for r in results)
        assert all("invoice_count" in r for r in results)
    
    def test_limit_months(self, sample_invoices):
        """Limitiert Anzahl Monate"""
        results = database.get_monthly_summary(months=1)
        assert len(results) <= 1


class TestDeleteJob:
    """Tests für delete_job()"""
    
    def test_delete_existing_job(self, sample_invoices):
        """Löscht Job und zugehörige Rechnungen"""
        result = database.delete_job("job-001")
        assert result is True
        
        # Job sollte weg sein
        job = database.get_job("job-001")
        assert job is None
    
    def test_delete_nonexistent_job(self, sample_jobs):
        """Gibt False bei nicht existentem Job"""
        result = database.delete_job("nicht-existent")
        assert result is False
    
    def test_delete_with_user_check(self, sample_jobs):
        """Prüft User-Berechtigung"""
        # User 2 darf job-001 (User 1) nicht löschen
        result = database.delete_job("job-001", user_id=2)
        assert result is False


class TestUpdateJobStatus:
    """Tests für update_job_status()"""
    
    def test_update_status(self, sample_jobs):
        """Aktualisiert Status"""
        result = database.update_job_status("job-003", "completed")
        assert result is True
        
        job = database.get_job("job-003")
        assert job["status"] == "completed"
    
    def test_update_with_extra_fields(self, sample_jobs):
        """Aktualisiert Status mit Extra-Feldern"""
        result = database.update_job_status(
            "job-003", 
            "completed",
            successful_files=10,
            failed_files=0
        )
        assert result is True
    
    def test_update_nonexistent_job(self, sample_jobs):
        """Gibt False bei nicht existentem Job"""
        result = database.update_job_status("nicht-existent", "completed")
        assert result is False
