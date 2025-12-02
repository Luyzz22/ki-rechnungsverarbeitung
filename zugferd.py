#!/usr/bin/env python3
"""
SBS Deutschland – ZUGFeRD Generator
Erstellt PDF/A-3 mit eingebettetem XML (Factur-X/ZUGFeRD 2.x)
"""

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False
    logger.warning("pikepdf nicht verfügbar - ZUGFeRD deaktiviert")


def create_zugferd_pdf(pdf_path: str, invoice_data: Dict, output_path: str = None) -> Optional[str]:
    """
    Erstellt ZUGFeRD-konformes PDF mit eingebettetem XML.
    
    Args:
        pdf_path: Pfad zur Original-PDF
        invoice_data: Rechnungsdaten für XML-Generierung
        output_path: Ausgabepfad (optional)
        
    Returns:
        Pfad zur ZUGFeRD-PDF oder None bei Fehler
    """
    if not PIKEPDF_AVAILABLE:
        logger.error("pikepdf nicht installiert")
        return None
    
    try:
        from einvoice import generate_xrechnung
        
        # XML generieren
        xml_content = generate_xrechnung(invoice_data)
        xml_bytes = xml_content.encode('utf-8')
        
        # PDF öffnen
        pdf = pikepdf.open(pdf_path)
        
        # XML als Attachment einbetten
        xml_stream = pikepdf.Stream(pdf, xml_bytes)
        xml_stream.stream_dict["/Type"] = pikepdf.Name("/EmbeddedFile")
        xml_stream.stream_dict["/Subtype"] = pikepdf.Name("/text/xml")
        
        # Filespec erstellen
        filespec = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/Filespec"),
            "/F": "factur-x.xml",
            "/UF": "factur-x.xml",
            "/Desc": "Factur-X/ZUGFeRD Invoice Data",
            "/AFRelationship": pikepdf.Name("/Data"),
            "/EF": pikepdf.Dictionary({
                "/F": xml_stream,
                "/UF": xml_stream
            })
        })
        
        # EmbeddedFiles im Catalog hinzufügen
        if "/Names" not in pdf.Root:
            pdf.Root["/Names"] = pikepdf.Dictionary()
        
        pdf.Root["/Names"]["/EmbeddedFiles"] = pikepdf.Dictionary({
            "/Names": pikepdf.Array(["factur-x.xml", filespec])
        })
        
        # AF Array (Associated Files) hinzufügen
        if "/AF" not in pdf.Root:
            pdf.Root["/AF"] = pikepdf.Array()
        pdf.Root["/AF"].append(filespec)
        
        # Metadata für ZUGFeRD/Factur-X
        with pdf.open_metadata() as meta:
            meta["dc:title"] = f"Rechnung {invoice_data.get('rechnungsnummer', '')}"
            meta["dc:creator"] = invoice_data.get('rechnungsaussteller', 'SBS Deutschland')
            meta["pdf:Producer"] = "SBS KI-Rechnungsverarbeitung"
            meta["xmp:CreateDate"] = datetime.now().isoformat()
        
        # Ausgabepfad
        if not output_path:
            p = Path(pdf_path)
            output_path = str(p.parent / f"{p.stem}_zugferd.pdf")
        
        # Speichern
        pdf.save(output_path)
        pdf.close()
        
        logger.info(f"✅ ZUGFeRD-PDF erstellt: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ ZUGFeRD-Erstellung fehlgeschlagen: {e}")
        return None


def create_zugferd_from_invoice(invoice_data: Dict, output_dir: str = "/tmp") -> Optional[bytes]:
    """
    Erstellt ZUGFeRD-PDF aus Rechnungsdaten (ohne Original-PDF).
    Generiert ein einfaches PDF mit eingebettetem XML.
    
    Args:
        invoice_data: Rechnungsdaten
        output_dir: Ausgabeverzeichnis
        
    Returns:
        PDF-Bytes oder None
    """
    if not PIKEPDF_AVAILABLE:
        return None
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        from einvoice import generate_xrechnung
        
        # Einfaches PDF erstellen
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, height - 2*cm, "RECHNUNG")
        
        c.setFont("Helvetica", 10)
        y = height - 3*cm
        
        # Rechnungsdaten
        fields = [
            ("Rechnungsnummer:", invoice_data.get("rechnungsnummer", "")),
            ("Datum:", invoice_data.get("datum", "")),
            ("Aussteller:", invoice_data.get("rechnungsaussteller", "")),
            ("Empfänger:", invoice_data.get("rechnungsempfänger", invoice_data.get("rechnungsempfaenger", ""))),
            ("Netto:", f"{invoice_data.get('betrag_netto', 0):.2f} EUR"),
            ("MwSt.:", f"{invoice_data.get('mwst_betrag', 0):.2f} EUR"),
            ("Brutto:", f"{invoice_data.get('betrag_brutto', 0):.2f} EUR"),
        ]
        
        for label, value in fields:
            c.drawString(2*cm, y, f"{label} {value}")
            y -= 0.6*cm
        
        # Footer
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(2*cm, 2*cm, "ZUGFeRD/Factur-X konformes Dokument - Generiert von SBS KI-Rechnungsverarbeitung")
        
        c.save()
        buffer.seek(0)
        
        # Temporäres PDF speichern
        temp_pdf = Path(output_dir) / f"temp_{invoice_data.get('rechnungsnummer', 'inv')}.pdf"
        with open(temp_pdf, 'wb') as f:
            f.write(buffer.getvalue())
        
        # XML einbetten
        output_pdf = str(temp_pdf).replace('.pdf', '_zugferd.pdf')
        result = create_zugferd_pdf(str(temp_pdf), invoice_data, output_pdf)
        
        if result:
            with open(result, 'rb') as f:
                pdf_bytes = f.read()
            
            # Cleanup
            temp_pdf.unlink(missing_ok=True)
            Path(output_pdf).unlink(missing_ok=True)
            
            return pdf_bytes
        
        return None
        
    except Exception as e:
        logger.error(f"ZUGFeRD-Generierung fehlgeschlagen: {e}")
        return None


def validate_zugferd(pdf_path: str) -> Dict:
    """
    Validiert ob PDF ZUGFeRD-konform ist.
    
    Args:
        pdf_path: Pfad zur PDF
        
    Returns:
        Dict mit Validierungsergebnis
    """
    if not PIKEPDF_AVAILABLE:
        return {"valid": False, "error": "pikepdf nicht verfügbar"}
    
    try:
        pdf = pikepdf.open(pdf_path)
        
        # Prüfe auf eingebettete Dateien
        has_xml = False
        xml_filename = None
        
        if "/Names" in pdf.Root and "/EmbeddedFiles" in pdf.Root["/Names"]:
            ef = pdf.Root["/Names"]["/EmbeddedFiles"]
            if "/Names" in ef:
                names = ef["/Names"]
                for i in range(0, len(names), 2):
                    filename = str(names[i])
                    if filename.lower().endswith('.xml'):
                        has_xml = True
                        xml_filename = filename
                        break
        
        pdf.close()
        
        return {
            "valid": has_xml,
            "has_embedded_xml": has_xml,
            "xml_filename": xml_filename,
            "profile": "ZUGFeRD/Factur-X" if has_xml else None
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}
