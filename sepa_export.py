#!/usr/bin/env python3
"""
SBS Deutschland – SEPA-XML Generator
Erstellt SEPA Credit Transfer (SCT) XML für Überweisungen.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_iban(iban: str) -> bool:
    """Validiert IBAN-Format."""
    if not iban:
        return False
    iban = iban.replace(" ", "").upper()
    if len(iban) < 15 or len(iban) > 34:
        return False
    if not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]+$', iban):
        return False
    return True


def validate_bic(bic: str) -> bool:
    """Validiert BIC-Format."""
    if not bic:
        return True  # BIC ist optional bei SEPA
    bic = bic.replace(" ", "").upper()
    return bool(re.match(r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$', bic))


def clean_sepa_string(text: str, max_length: int = 70) -> str:
    """Bereinigt String für SEPA-Kompatibilität."""
    if not text:
        return ""
    # Erlaubte Zeichen: a-z, A-Z, 0-9, /-?:().,'+ und Leerzeichen
    allowed = re.sub(r'[^a-zA-Z0-9\s/\-?:().,\'+]', '', text)
    return allowed[:max_length].strip()


def generate_message_id() -> str:
    """Generiert eindeutige Message-ID."""
    return f"SBS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{id(datetime.now()) % 10000:04d}"


def generate_sepa_xml(
    payments: List[Dict],
    debtor_name: str,
    debtor_iban: str,
    debtor_bic: str = None,
    execution_date: str = None,
    batch_booking: bool = True
) -> str:
    """
    Generiert SEPA Credit Transfer XML (pain.001.003.03).
    
    Args:
        payments: Liste von Zahlungen [{creditor_name, creditor_iban, amount, reference, ...}]
        debtor_name: Name des Zahlers (Ihr Unternehmen)
        debtor_iban: IBAN des Zahlers
        debtor_bic: BIC des Zahlers (optional)
        execution_date: Ausführungsdatum (YYYY-MM-DD), Standard: morgen
        batch_booking: Sammelüberweisung (True) oder Einzelbuchungen (False)
        
    Returns:
        SEPA-XML als String
    """
    if not payments:
        raise ValueError("Keine Zahlungen angegeben")
    
    if not validate_iban(debtor_iban):
        raise ValueError(f"Ungültige Absender-IBAN: {debtor_iban}")
    
    # Ausführungsdatum
    if not execution_date:
        execution_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Namespace
    ns = "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03"
    
    # Root Element
    root = ET.Element("Document", xmlns=ns)
    cstmr_cdt_trf_initn = ET.SubElement(root, "CstmrCdtTrfInitn")
    
    # === Group Header ===
    grp_hdr = ET.SubElement(cstmr_cdt_trf_initn, "GrpHdr")
    
    msg_id = generate_message_id()
    ET.SubElement(grp_hdr, "MsgId").text = msg_id
    ET.SubElement(grp_hdr, "CreDtTm").text = datetime.now().isoformat()
    ET.SubElement(grp_hdr, "NbOfTxs").text = str(len(payments))
    
    # Gesamtsumme berechnen
    total_amount = sum(float(p.get('amount', 0)) for p in payments)
    ET.SubElement(grp_hdr, "CtrlSum").text = f"{total_amount:.2f}"
    
    # Initiator
    initg_pty = ET.SubElement(grp_hdr, "InitgPty")
    ET.SubElement(initg_pty, "Nm").text = clean_sepa_string(debtor_name, 70)
    
    # === Payment Information ===
    pmt_inf = ET.SubElement(cstmr_cdt_trf_initn, "PmtInf")
    
    ET.SubElement(pmt_inf, "PmtInfId").text = f"PMT-{msg_id}"
    ET.SubElement(pmt_inf, "PmtMtd").text = "TRF"  # Transfer
    ET.SubElement(pmt_inf, "BtchBookg").text = "true" if batch_booking else "false"
    ET.SubElement(pmt_inf, "NbOfTxs").text = str(len(payments))
    ET.SubElement(pmt_inf, "CtrlSum").text = f"{total_amount:.2f}"
    
    # Payment Type Information
    pmt_tp_inf = ET.SubElement(pmt_inf, "PmtTpInf")
    svc_lvl = ET.SubElement(pmt_tp_inf, "SvcLvl")
    ET.SubElement(svc_lvl, "Cd").text = "SEPA"
    
    # Requested Execution Date
    ET.SubElement(pmt_inf, "ReqdExctnDt").text = execution_date
    
    # Debtor (Zahler)
    dbtr = ET.SubElement(pmt_inf, "Dbtr")
    ET.SubElement(dbtr, "Nm").text = clean_sepa_string(debtor_name, 70)
    
    # Debtor Account
    dbtr_acct = ET.SubElement(pmt_inf, "DbtrAcct")
    dbtr_id = ET.SubElement(dbtr_acct, "Id")
    ET.SubElement(dbtr_id, "IBAN").text = debtor_iban.replace(" ", "").upper()
    
    # Debtor Agent (Bank)
    dbtr_agt = ET.SubElement(pmt_inf, "DbtrAgt")
    fin_instn_id = ET.SubElement(dbtr_agt, "FinInstnId")
    if debtor_bic:
        ET.SubElement(fin_instn_id, "BIC").text = debtor_bic.replace(" ", "").upper()
    else:
        ET.SubElement(fin_instn_id, "Othr").text = "NOTPROVIDED"
    
    ET.SubElement(pmt_inf, "ChrgBr").text = "SLEV"  # Shared charges
    
    # === Credit Transfer Transactions ===
    for i, payment in enumerate(payments):
        cdt_trf_tx_inf = ET.SubElement(pmt_inf, "CdtTrfTxInf")
        
        # Payment ID
        pmt_id = ET.SubElement(cdt_trf_tx_inf, "PmtId")
        end_to_end_id = payment.get('end_to_end_id') or f"E2E-{msg_id}-{i+1:04d}"
        ET.SubElement(pmt_id, "EndToEndId").text = clean_sepa_string(end_to_end_id, 35)
        
        # Amount
        amt = ET.SubElement(cdt_trf_tx_inf, "Amt")
        instd_amt = ET.SubElement(amt, "InstdAmt", Ccy="EUR")
        instd_amt.text = f"{float(payment.get('amount', 0)):.2f}"
        
        # Creditor Agent (Empfängerbank)
        creditor_bic = payment.get('creditor_bic', '')
        if creditor_bic and validate_bic(creditor_bic):
            cdtr_agt = ET.SubElement(cdt_trf_tx_inf, "CdtrAgt")
            cdtr_fin_instn = ET.SubElement(cdtr_agt, "FinInstnId")
            ET.SubElement(cdtr_fin_instn, "BIC").text = creditor_bic.replace(" ", "").upper()
        
        # Creditor (Empfänger)
        cdtr = ET.SubElement(cdt_trf_tx_inf, "Cdtr")
        creditor_name = payment.get('creditor_name') or payment.get('rechnungsaussteller', 'Unbekannt')
        ET.SubElement(cdtr, "Nm").text = clean_sepa_string(creditor_name, 70)
        
        # Creditor Account
        creditor_iban = payment.get('creditor_iban') or payment.get('iban', '')
        if creditor_iban and validate_iban(creditor_iban):
            cdtr_acct = ET.SubElement(cdt_trf_tx_inf, "CdtrAcct")
            cdtr_acct_id = ET.SubElement(cdtr_acct, "Id")
            ET.SubElement(cdtr_acct_id, "IBAN").text = creditor_iban.replace(" ", "").upper()
        
        # Remittance Information (Verwendungszweck)
        rmt_inf = ET.SubElement(cdt_trf_tx_inf, "RmtInf")
        reference = payment.get('reference') or payment.get('rechnungsnummer', '')
        ustrd_text = f"Rechnung {reference}" if reference else "Zahlung"
        ET.SubElement(rmt_inf, "Ustrd").text = clean_sepa_string(ustrd_text, 140)
    
    # Pretty print
    xml_string = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_string)
    return dom.toprettyxml(indent="  ", encoding=None)


def export_invoices_to_sepa(
    invoices: List[Dict],
    debtor_config: Dict,
    output_path: str = None
) -> Dict:
    """
    Exportiert Rechnungen als SEPA-XML.
    
    Args:
        invoices: Rechnungen mit IBAN
        debtor_config: {name, iban, bic}
        output_path: Ausgabepfad (optional)
        
    Returns:
        Dict mit path, count, total, warnings
    """
    warnings = []
    valid_payments = []
    
    for inv in invoices:
        iban = inv.get('iban') or inv.get('creditor_iban', '')
        amount = inv.get('betrag_brutto') or inv.get('amount', 0)
        
        if not iban:
            warnings.append(f"Rechnung {inv.get('rechnungsnummer', '?')}: Keine IBAN")
            continue
        
        if not validate_iban(iban):
            warnings.append(f"Rechnung {inv.get('rechnungsnummer', '?')}: Ungültige IBAN")
            continue
        
        if not amount or float(amount) <= 0:
            warnings.append(f"Rechnung {inv.get('rechnungsnummer', '?')}: Kein Betrag")
            continue
        
        valid_payments.append({
            'creditor_name': inv.get('rechnungsaussteller', 'Unbekannt'),
            'creditor_iban': iban,
            'creditor_bic': inv.get('bic', ''),
            'amount': float(amount),
            'reference': inv.get('rechnungsnummer', ''),
            'end_to_end_id': f"INV-{inv.get('rechnungsnummer', '')}"[:35]
        })
    
    if not valid_payments:
        return {
            'success': False,
            'error': 'Keine gültigen Zahlungen',
            'warnings': warnings
        }
    
    # XML generieren
    xml_content = generate_sepa_xml(
        payments=valid_payments,
        debtor_name=debtor_config.get('name', 'Unbekannt'),
        debtor_iban=debtor_config.get('iban', ''),
        debtor_bic=debtor_config.get('bic', '')
    )
    
    # Speichern
    if not output_path:
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = str(output_dir / f"sepa_payment_{timestamp}.xml")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    total_amount = sum(p['amount'] for p in valid_payments)
    
    logger.info(f"SEPA-XML erstellt: {output_path} ({len(valid_payments)} Zahlungen, {total_amount:.2f} EUR)")
    
    return {
        'success': True,
        'path': output_path,
        'count': len(valid_payments),
        'total': round(total_amount, 2),
        'warnings': warnings,
        'xml': xml_content
    }


def validate_sepa_file(xml_path: str) -> Dict:
    """Validiert eine SEPA-XML Datei."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Namespace entfernen für einfacheres Parsen
        ns = {'pain': 'urn:iso:std:iso:20022:tech:xsd:pain.001.003.03'}
        
        # Basic validation
        grp_hdr = root.find('.//pain:GrpHdr', ns) or root.find('.//GrpHdr')
        if grp_hdr is None:
            return {'valid': False, 'error': 'GrpHdr nicht gefunden'}
        
        nb_of_txs = grp_hdr.find('NbOfTxs') or grp_hdr.find('pain:NbOfTxs', ns)
        ctrl_sum = grp_hdr.find('CtrlSum') or grp_hdr.find('pain:CtrlSum', ns)
        
        return {
            'valid': True,
            'transactions': int(nb_of_txs.text) if nb_of_txs is not None else 0,
            'total': float(ctrl_sum.text) if ctrl_sum is not None else 0
        }
        
    except Exception as e:
        return {'valid': False, 'error': str(e)}
