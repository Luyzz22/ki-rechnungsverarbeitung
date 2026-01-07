"""
Lexoffice API Integration Module
================================
REST API Integration für Lexoffice (lexoffice.de)
API Docs: https://developers.lexoffice.io/docs/

Features:
- Voucher Import (Eingangsrechnungen)
- Contact Sync (Lieferanten)
- Payment Status Updates
- Document Upload
"""

import os
import json
import logging
import requests
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from decimal import Decimal

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

LEXOFFICE_API_BASE = "https://api.lexoffice.io/v1"

@dataclass
class LexofficeConfig:
    """Lexoffice API Konfiguration"""
    api_key: str
    organization_id: Optional[str] = None
    sandbox: bool = False
    
    @property
    def base_url(self) -> str:
        return LEXOFFICE_API_BASE


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LexofficeAddress:
    """Adresse für Lexoffice"""
    street: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    countryCode: str = "DE"


@dataclass
class LexofficeContact:
    """Kontakt (Lieferant/Kunde) für Lexoffice"""
    id: Optional[str] = None
    version: Optional[int] = None
    name: str = ""
    taxNumber: Optional[str] = None
    vatRegistrationId: Optional[str] = None  # USt-IdNr
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[LexofficeAddress] = None
    
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to Lexoffice API format"""
        data = {
            "version": self.version or 0,
            "roles": {"vendor": {}},  # Lieferant
            "company": {
                "name": self.name,
                "taxNumber": self.taxNumber,
                "vatRegistrationId": self.vatRegistrationId,
            }
        }
        if self.address:
            data["addresses"] = {
                "billing": [{
                    "street": self.address.street,
                    "zip": self.address.zip,
                    "city": self.address.city,
                    "countryCode": self.address.countryCode
                }]
            }
        if self.email:
            data["emailAddresses"] = {"business": [self.email]}
        if self.phone:
            data["phoneNumbers"] = {"business": [self.phone]}
        return data


@dataclass 
class LexofficeLineItem:
    """Rechnungsposition"""
    name: str
    quantity: float = 1.0
    unitPrice: float = 0.0
    taxRate: float = 19.0
    unitName: str = "Stück"
    
    def to_api_dict(self) -> Dict[str, Any]:
        return {
            "type": "custom",
            "name": self.name,
            "quantity": self.quantity,
            "unitName": self.unitName,
            "unitPrice": {
                "currency": "EUR",
                "netAmount": self.unitPrice,
                "taxRatePercentage": self.taxRate
            }
        }


@dataclass
class LexofficeVoucher:
    """Beleg (Eingangsrechnung) für Lexoffice"""
    id: Optional[str] = None
    voucherNumber: Optional[str] = None  # Rechnungsnummer
    voucherDate: Optional[date] = None
    dueDate: Optional[date] = None
    contactId: Optional[str] = None
    contactName: Optional[str] = None
    totalGrossAmount: float = 0.0
    totalTaxAmount: float = 0.0
    taxRate: float = 19.0
    currency: str = "EUR"
    lineItems: Optional[List[LexofficeLineItem]] = None
    files: Optional[List[str]] = None  # PDF file IDs
    
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to Lexoffice Voucher API format"""
        data = {
            "type": "purchaseinvoice",  # Eingangsrechnung
            "voucherNumber": self.voucherNumber,
            "voucherDate": self.voucherDate.isoformat() if self.voucherDate else None,
            "dueDate": self.dueDate.isoformat() if self.dueDate else None,
            "totalGrossAmount": self.totalGrossAmount,
            "totalTaxAmount": self.totalTaxAmount,
            "taxType": "gross",
            "useCollectiveContact": self.contactId is None,
        }
        
        if self.contactId:
            data["contactId"] = self.contactId
        
        if self.lineItems:
            data["voucherItems"] = [item.to_api_dict() for item in self.lineItems]
        else:
            # Mindestens eine Position mit Gesamtbetrag
            net_amount = self.totalGrossAmount - self.totalTaxAmount
            data["voucherItems"] = [{
                "amount": net_amount,
                "taxAmount": self.totalTaxAmount,
                "taxRatePercent": self.taxRate,
                "categoryId": "8f8664a1-fd86-11e1-a21f-0800200c9a66"  # Sonstige Ausgaben
            }]
        
        if self.files:
            data["files"] = self.files
            
        return data


# =============================================================================
# API CLIENT
# =============================================================================

class LexofficeClient:
    """Lexoffice REST API Client"""
    
    def __init__(self, config: LexofficeConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                 files: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.config.base_url}/{endpoint}"
        
        try:
            if files:
                # File upload - different headers
                headers = {"Authorization": f"Bearer {self.config.api_key}"}
                response = requests.request(method, url, headers=headers, files=files)
            else:
                response = self.session.request(method, url, json=data)
            
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
            logger.error(f"Lexoffice API Error: {e} - {error_detail}")
            raise LexofficeAPIError(f"API Error: {e}", error_detail)
        except Exception as e:
            logger.error(f"Lexoffice Request Error: {e}")
            raise LexofficeAPIError(f"Request Error: {e}")
    
    # -------------------------------------------------------------------------
    # Contacts (Lieferanten)
    # -------------------------------------------------------------------------
    
    def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """Get contact by ID"""
        return self._request("GET", f"contacts/{contact_id}")
    
    def search_contacts(self, name: str = None, email: str = None, 
                       customer: bool = None, vendor: bool = True) -> List[Dict]:
        """Search contacts"""
        params = []
        if vendor:
            params.append("vendor=true")
        if customer:
            params.append("customer=true")
        if name:
            params.append(f"name={name}")
        if email:
            params.append(f"email={email}")
        
        query = "&".join(params)
        result = self._request("GET", f"contacts?{query}")
        return result.get("content", [])
    
    def create_contact(self, contact: LexofficeContact) -> Dict[str, Any]:
        """Create new contact"""
        return self._request("POST", "contacts", contact.to_api_dict())
    
    def update_contact(self, contact_id: str, contact: LexofficeContact) -> Dict[str, Any]:
        """Update existing contact"""
        return self._request("PUT", f"contacts/{contact_id}", contact.to_api_dict())
    
    def find_or_create_vendor(self, name: str, tax_id: str = None, 
                              vat_id: str = None) -> str:
        """Find vendor by name or create new one, return ID"""
        # Search existing
        results = self.search_contacts(name=name, vendor=True)
        
        for contact in results:
            company = contact.get("company", {})
            if company.get("name", "").lower() == name.lower():
                return contact["id"]
        
        # Create new
        new_contact = LexofficeContact(
            name=name,
            taxNumber=tax_id,
            vatRegistrationId=vat_id
        )
        result = self.create_contact(new_contact)
        return result["id"]
    
    # -------------------------------------------------------------------------
    # Vouchers (Belege / Eingangsrechnungen)
    # -------------------------------------------------------------------------
    
    def get_voucher(self, voucher_id: str) -> Dict[str, Any]:
        """Get voucher by ID"""
        return self._request("GET", f"vouchers/{voucher_id}")
    
    def create_voucher(self, voucher: LexofficeVoucher) -> Dict[str, Any]:
        """Create new voucher (Eingangsrechnung)"""
        return self._request("POST", "vouchers", voucher.to_api_dict())
    
    def list_vouchers(self, voucher_type: str = "purchaseinvoice", 
                      page: int = 0, size: int = 25) -> Dict[str, Any]:
        """List vouchers with pagination"""
        return self._request("GET", 
            f"voucherlist?voucherType={voucher_type}&page={page}&size={size}")
    
    # -------------------------------------------------------------------------
    # Files (Dokumente)
    # -------------------------------------------------------------------------
    
    def upload_file(self, file_path: str, voucher_id: str = None) -> Dict[str, Any]:
        """Upload a file (PDF)"""
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            
            if voucher_id:
                return self._request("POST", f"vouchers/{voucher_id}/files", files=files)
            else:
                return self._request("POST", "files", files=files)
    
    # -------------------------------------------------------------------------
    # Profile
    # -------------------------------------------------------------------------
    
    def get_profile(self) -> Dict[str, Any]:
        """Get organization profile"""
        return self._request("GET", "profile")
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            profile = self.get_profile()
            logger.info(f"Lexoffice connected: {profile.get('companyName', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Lexoffice connection test failed: {e}")
            return False


# =============================================================================
# INVOICE SYNC
# =============================================================================

class LexofficeInvoiceSync:
    """Sync invoices from SBS to Lexoffice"""
    
    def __init__(self, client: LexofficeClient):
        self.client = client
    
    def sync_invoice(self, invoice_data: Dict[str, Any], 
                     pdf_path: str = None) -> Dict[str, Any]:
        """
        Sync a single invoice to Lexoffice
        
        Args:
            invoice_data: Invoice dict from SBS database
            pdf_path: Optional path to PDF file
            
        Returns:
            Dict with sync result
        """
        try:
            # 1. Find or create vendor contact
            vendor_name = invoice_data.get('rechnungsaussteller', 'Unbekannt')
            vat_id = invoice_data.get('ust_idnr')
            
            contact_id = None
            if vendor_name and vendor_name != 'Unbekannt':
                try:
                    contact_id = self.client.find_or_create_vendor(
                        name=vendor_name,
                        vat_id=vat_id
                    )
                except Exception as e:
                    logger.warning(f"Could not create vendor contact: {e}")
            
            # 2. Parse dates
            voucher_date = None
            due_date = None
            
            if invoice_data.get('datum'):
                try:
                    voucher_date = datetime.strptime(
                        invoice_data['datum'], '%Y-%m-%d'
                    ).date()
                except:
                    voucher_date = date.today()
            
            if invoice_data.get('faelligkeitsdatum'):
                try:
                    due_date = datetime.strptime(
                        invoice_data['faelligkeitsdatum'], '%Y-%m-%d'
                    ).date()
                except:
                    pass
            
            # 3. Calculate amounts
            gross_amount = float(invoice_data.get('betrag_brutto', 0) or 0)
            tax_amount = float(invoice_data.get('mwst_betrag', 0) or 0)
            tax_rate = float(invoice_data.get('mwst_satz', 19) or 19)
            
            # 4. Create voucher
            voucher = LexofficeVoucher(
                voucherNumber=invoice_data.get('rechnungsnummer'),
                voucherDate=voucher_date or date.today(),
                dueDate=due_date,
                contactId=contact_id,
                contactName=vendor_name,
                totalGrossAmount=gross_amount,
                totalTaxAmount=tax_amount,
                taxRate=tax_rate
            )
            
            result = self.client.create_voucher(voucher)
            voucher_id = result.get('id')
            
            # 5. Upload PDF if available
            file_id = None
            if pdf_path and os.path.exists(pdf_path) and voucher_id:
                try:
                    file_result = self.client.upload_file(pdf_path, voucher_id)
                    file_id = file_result.get('id')
                except Exception as e:
                    logger.warning(f"Could not upload PDF: {e}")
            
            return {
                "success": True,
                "lexoffice_id": voucher_id,
                "contact_id": contact_id,
                "file_id": file_id,
                "message": f"Rechnung {invoice_data.get('rechnungsnummer')} erfolgreich zu Lexoffice übertragen"
            }
            
        except Exception as e:
            logger.error(f"Lexoffice sync error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Sync: {e}"
            }
    
    def sync_batch(self, invoices: List[Dict[str, Any]], 
                   pdf_dir: str = None) -> Dict[str, Any]:
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

class LexofficeAPIError(Exception):
    """Lexoffice API Error"""
    def __init__(self, message: str, detail: Any = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_lexoffice_client(api_key: str) -> LexofficeClient:
    """Create Lexoffice client with API key"""
    config = LexofficeConfig(api_key=api_key)
    return LexofficeClient(config)


def test_lexoffice_connection(api_key: str) -> Dict[str, Any]:
    """Test Lexoffice API connection"""
    try:
        client = create_lexoffice_client(api_key)
        profile = client.get_profile()
        return {
            "success": True,
            "company_name": profile.get("companyName"),
            "organization_id": profile.get("organizationId"),
            "created": profile.get("created")
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
    print("Lexoffice Integration Module")
    print("=" * 50)
    print("API Base:", LEXOFFICE_API_BASE)
    print()
    print("Klassen:")
    print("  - LexofficeConfig")
    print("  - LexofficeContact")
    print("  - LexofficeVoucher")
    print("  - LexofficeClient")
    print("  - LexofficeInvoiceSync")
    print()
    print("Verwendung:")
    print("  client = create_lexoffice_client('YOUR_API_KEY')")
    print("  client.test_connection()")
    print("  sync = LexofficeInvoiceSync(client)")
    print("  sync.sync_invoice(invoice_data)")
