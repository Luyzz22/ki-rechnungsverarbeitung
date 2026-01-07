"""
sevDesk API Integration Module
==============================
REST API Integration für sevDesk (sevdesk.de)
API Docs: https://api.sevdesk.de/

Features:
- Voucher Import (Eingangsrechnungen)
- Contact Sync (Lieferanten)
- Payment Status
- Document Upload
"""

import os
import json
import logging
import requests
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

SEVDESK_API_BASE = "https://my.sevdesk.de/api/v1"

@dataclass
class SevdeskConfig:
    """sevDesk API Konfiguration"""
    api_token: str
    
    @property
    def base_url(self) -> str:
        return SEVDESK_API_BASE


# =============================================================================
# API CLIENT
# =============================================================================

class SevdeskClient:
    """sevDesk REST API Client"""
    
    def __init__(self, config: SevdeskConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": config.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                 params: Optional[Dict] = None, files: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.config.base_url}/{endpoint}"
        
        try:
            if files:
                headers = {"Authorization": self.config.api_token}
                response = requests.request(method, url, headers=headers, 
                                          data=data, files=files, params=params)
            else:
                response = self.session.request(method, url, json=data, params=params)
            
            response.raise_for_status()
            
            if response.status_code == 204:
                return {"success": True}
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
            logger.error(f"sevDesk API Error: {e} - {error_detail}")
            raise SevdeskAPIError(f"API Error: {e}", error_detail)
        except Exception as e:
            logger.error(f"sevDesk Request Error: {e}")
            raise SevdeskAPIError(f"Request Error: {e}")
    
    # -------------------------------------------------------------------------
    # Contacts (Lieferanten)
    # -------------------------------------------------------------------------
    
    def get_contact(self, contact_id: int) -> Dict[str, Any]:
        """Get contact by ID"""
        result = self._request("GET", f"Contact/{contact_id}")
        return result.get("objects", [{}])[0] if result.get("objects") else {}
    
    def search_contacts(self, name: str = None, category: str = "3") -> List[Dict]:
        """
        Search contacts
        category: 3 = Lieferant, 2 = Kunde, 4 = Partner
        """
        params = {"depth": "1"}
        if name:
            params["name"] = name
        if category:
            params["category[id]"] = category
            params["category[objectName]"] = "Category"
        
        result = self._request("GET", "Contact", params=params)
        return result.get("objects", [])
    
    def create_contact(self, name: str, category_id: int = 3, 
                      tax_number: str = None, vat_number: str = None,
                      email: str = None) -> Dict[str, Any]:
        """
        Create new contact
        category_id: 3 = Lieferant
        """
        data = {
            "name": name,
            "category": {
                "id": category_id,
                "objectName": "Category"
            },
            "taxNumber": tax_number,
            "vatNumber": vat_number
        }
        
        result = self._request("POST", "Contact", data)
        return result.get("objects", {})
    
    def find_or_create_supplier(self, name: str, vat_number: str = None) -> int:
        """Find supplier by name or create new, return ID"""
        results = self.search_contacts(name=name, category="3")
        
        for contact in results:
            if contact.get("name", "").lower() == name.lower():
                return int(contact["id"])
        
        # Create new
        result = self.create_contact(name=name, category_id=3, vat_number=vat_number)
        return int(result.get("id", 0))
    
    # -------------------------------------------------------------------------
    # Vouchers (Belege)
    # -------------------------------------------------------------------------
    
    def get_voucher(self, voucher_id: int) -> Dict[str, Any]:
        """Get voucher by ID"""
        result = self._request("GET", f"Voucher/{voucher_id}")
        return result.get("objects", [{}])[0] if result.get("objects") else {}
    
    def create_voucher(self, supplier_id: int, voucher_date: date,
                      description: str = None, document_number: str = None,
                      status: int = 50) -> Dict[str, Any]:
        """
        Create voucher (Beleg)
        status: 50 = Entwurf, 100 = Offen, 1000 = Bezahlt
        """
        data = {
            "voucherDate": voucher_date.strftime("%Y-%m-%d"),
            "supplier": {
                "id": supplier_id,
                "objectName": "Contact"
            },
            "description": description or "Eingangsrechnung",
            "document": document_number,
            "status": status,
            "voucherType": "VOU",  # Voucher
            "creditDebit": "D",    # Debit (Ausgabe)
            "taxType": "default",
            "mapAll": True
        }
        
        result = self._request("POST", "Voucher", data)
        return result.get("objects", {})
    
    def create_voucher_position(self, voucher_id: int, net_amount: float,
                                tax_rate: float = 19.0, 
                                account_id: int = None,
                                name: str = "Position") -> Dict[str, Any]:
        """Create voucher position (Belegposition)"""
        
        # Standard-Konto für Eingangsrechnungen: 3400 (Wareneingang)
        if not account_id:
            account_id = self._get_default_account()
        
        data = {
            "voucher": {
                "id": voucher_id,
                "objectName": "Voucher"
            },
            "accountingType": {
                "id": account_id,
                "objectName": "AccountingType"
            },
            "taxRate": tax_rate,
            "net": True,
            "sumNet": net_amount,
            "name": name,
            "mapAll": True
        }
        
        result = self._request("POST", "VoucherPos", data)
        return result.get("objects", {})
    
    def _get_default_account(self) -> int:
        """Get default expense account ID"""
        # Suche nach Konto 3400 oder 4900
        result = self._request("GET", "AccountingType", 
                              params={"accountNumber": "4900"})
        objects = result.get("objects", [])
        if objects:
            return int(objects[0]["id"])
        return 1  # Fallback
    
    def book_voucher(self, voucher_id: int) -> Dict[str, Any]:
        """Book voucher (Status auf 100 = Offen setzen)"""
        return self._request("PUT", f"Voucher/{voucher_id}/bookAmount", 
                           data={"amount": 0})
    
    # -------------------------------------------------------------------------
    # Documents
    # -------------------------------------------------------------------------
    
    def upload_document(self, voucher_id: int, file_path: str) -> Dict[str, Any]:
        """Upload PDF to voucher"""
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            data = {
                "object[id]": voucher_id,
                "object[objectName]": "Voucher"
            }
            return self._request("POST", "Voucher/Factory/uploadTempFile", 
                               data=data, files=files)
    
    # -------------------------------------------------------------------------
    # Profile / Info
    # -------------------------------------------------------------------------
    
    def get_sev_user(self) -> Dict[str, Any]:
        """Get current user info"""
        result = self._request("GET", "SevUser")
        return result.get("objects", [{}])[0] if result.get("objects") else {}
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            user = self.get_sev_user()
            logger.info(f"sevDesk connected: {user.get('email', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"sevDesk connection test failed: {e}")
            return False


# =============================================================================
# INVOICE SYNC
# =============================================================================

class SevdeskInvoiceSync:
    """Sync invoices from SBS to sevDesk"""
    
    def __init__(self, client: SevdeskClient):
        self.client = client
    
    def sync_invoice(self, invoice_data: Dict[str, Any],
                     pdf_path: str = None) -> Dict[str, Any]:
        """Sync single invoice to sevDesk"""
        try:
            # 1. Find or create supplier
            supplier_name = invoice_data.get('rechnungsaussteller', 'Unbekannt')
            vat_id = invoice_data.get('ust_idnr')
            
            supplier_id = None
            if supplier_name and supplier_name != 'Unbekannt':
                try:
                    supplier_id = self.client.find_or_create_supplier(
                        name=supplier_name,
                        vat_number=vat_id
                    )
                except Exception as e:
                    logger.warning(f"Could not create supplier: {e}")
            
            if not supplier_id:
                return {
                    "success": False,
                    "error": "Kein Lieferant gefunden/erstellt"
                }
            
            # 2. Parse date
            voucher_date = date.today()
            if invoice_data.get('datum'):
                try:
                    voucher_date = datetime.strptime(
                        invoice_data['datum'], '%Y-%m-%d'
                    ).date()
                except:
                    pass
            
            # 3. Create voucher
            voucher_result = self.client.create_voucher(
                supplier_id=supplier_id,
                voucher_date=voucher_date,
                description=f"Rechnung {invoice_data.get('rechnungsnummer', '')}",
                document_number=invoice_data.get('rechnungsnummer'),
                status=50  # Entwurf
            )
            
            voucher_id = int(voucher_result.get('id', 0))
            if not voucher_id:
                return {
                    "success": False,
                    "error": "Voucher konnte nicht erstellt werden"
                }
            
            # 4. Create position
            gross_amount = float(invoice_data.get('betrag_brutto', 0) or 0)
            tax_amount = float(invoice_data.get('mwst_betrag', 0) or 0)
            net_amount = gross_amount - tax_amount
            tax_rate = float(invoice_data.get('mwst_satz', 19) or 19)
            
            self.client.create_voucher_position(
                voucher_id=voucher_id,
                net_amount=net_amount,
                tax_rate=tax_rate,
                name=invoice_data.get('rechnungsaussteller', 'Eingangsrechnung')
            )
            
            # 5. Upload PDF
            if pdf_path and os.path.exists(pdf_path):
                try:
                    self.client.upload_document(voucher_id, pdf_path)
                except Exception as e:
                    logger.warning(f"Could not upload PDF: {e}")
            
            return {
                "success": True,
                "sevdesk_id": voucher_id,
                "supplier_id": supplier_id,
                "message": f"Rechnung {invoice_data.get('rechnungsnummer')} zu sevDesk übertragen"
            }
            
        except Exception as e:
            logger.error(f"sevDesk sync error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_batch(self, invoices: List[Dict], pdf_dir: str = None) -> Dict[str, Any]:
        """Sync multiple invoices"""
        results = {
            "total": len(invoices),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for invoice in invoices:
            pdf_path = None
            if pdf_dir and invoice.get('pdf_filename'):
                pdf_path = os.path.join(pdf_dir, invoice['pdf_filename'])
            
            result = self.sync_invoice(invoice, pdf_path)
            results["details"].append({
                "invoice_id": invoice.get('id'),
                "rechnungsnummer": invoice.get('rechnungsnummer'),
                **result
            })
            
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SevdeskAPIError(Exception):
    """sevDesk API Error"""
    def __init__(self, message: str, detail: Any = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_sevdesk_client(api_token: str) -> SevdeskClient:
    """Create sevDesk client"""
    config = SevdeskConfig(api_token=api_token)
    return SevdeskClient(config)


def test_sevdesk_connection(api_token: str) -> Dict[str, Any]:
    """Test sevDesk API connection"""
    try:
        client = create_sevdesk_client(api_token)
        user = client.get_sev_user()
        return {
            "success": True,
            "email": user.get("email"),
            "user_id": user.get("id")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("sevDesk Integration Module")
    print("=" * 50)
    print("API Base:", SEVDESK_API_BASE)
    print()
    print("Klassen:")
    print("  - SevdeskConfig")
    print("  - SevdeskClient")
    print("  - SevdeskInvoiceSync")
    print()
    print("Verwendung:")
    print("  client = create_sevdesk_client('YOUR_API_TOKEN')")
    print("  client.test_connection()")
    print("  sync = SevdeskInvoiceSync(client)")
    print("  sync.sync_invoice(invoice_data)")
