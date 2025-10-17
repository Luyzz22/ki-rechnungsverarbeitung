#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - Validation Module v3.0
Data validation for extracted invoice data
"""

import re
from typing import Dict, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class InvoiceValidator:
    """Validates extracted invoice data"""
    
    def __init__(self, strict: bool = False, required_fields: List[str] = None):
        self.strict = strict
        self.required_fields = required_fields or [
            'rechnungsnummer',
            'datum',
            'lieferant',
            'betrag_brutto'
        ]
    
    def validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate invoice data
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if not data.get(field):
                errors.append(f"Pflichtfeld fehlt: {field}")
        
        # Validate specific fields
        errors.extend(self._validate_amounts(data))
        errors.extend(self._validate_dates(data))
        errors.extend(self._validate_iban(data))
        errors.extend(self._validate_ust_idnr(data))
        errors.extend(self._validate_tax_calculation(data))
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Validation failed for {data.get('dateiname', 'unknown')}: {errors}")
        
        return is_valid, errors
    
    def _validate_amounts(self, data: Dict) -> List[str]:
        """Validate amount fields"""
        errors = []
        
        brutto = data.get('betrag_brutto')
        netto = data.get('betrag_netto')
        mwst = data.get('mwst_betrag')
        
        # Check if amounts are numbers
        if brutto is not None and not isinstance(brutto, (int, float)):
            errors.append(f"betrag_brutto ist keine Zahl: {brutto}")
        
        if netto is not None and not isinstance(netto, (int, float)):
            errors.append(f"betrag_netto ist keine Zahl: {netto}")
        
        if mwst is not None and not isinstance(mwst, (int, float)):
            errors.append(f"mwst_betrag ist keine Zahl: {mwst}")
        
        # Check if amounts are positive
        if brutto is not None and brutto < 0:
            errors.append(f"betrag_brutto ist negativ: {brutto}")
        
        if netto is not None and netto < 0:
            errors.append(f"betrag_netto ist negativ: {netto}")
        
        # Check plausibility range (0.01 - 1M EUR)
        if brutto is not None:
            if brutto < 0.01:
                errors.append(f"betrag_brutto zu klein: {brutto}")
            if brutto > 1000000:
                errors.append(f"betrag_brutto unrealistisch hoch: {brutto}")
        
        return errors
    
    def _validate_tax_calculation(self, data: Dict) -> List[str]:
        """Validate tax calculation (netto + mwst = brutto)"""
        errors = []
        
        brutto = data.get('betrag_brutto')
        netto = data.get('betrag_netto')
        mwst = data.get('mwst_betrag')
        
        # Only validate if all three are present
        if brutto is not None and netto is not None and mwst is not None:
            calculated_brutto = netto + mwst
            
            # Allow 0.02 EUR tolerance for rounding
            if abs(calculated_brutto - brutto) > 0.02:
                errors.append(
                    f"Steuerberechnung inkonsistent: "
                    f"{netto} + {mwst} = {calculated_brutto} ≠ {brutto}"
                )
        
        return errors
    
    def _validate_dates(self, data: Dict) -> List[str]:
        """Validate date fields"""
        errors = []
        
        datum = data.get('datum')
        faellig = data.get('faelligkeitsdatum')
        
        # Check date format
        if datum:
            if not self._is_valid_date(datum):
                errors.append(f"Ungültiges Datumsformat: {datum}")
            else:
                # Check if date is reasonable (not in far future/past)
                try:
                    date_obj = datetime.strptime(datum, '%Y-%m-%d')
                    today = datetime.now()
                    
                    # Allow dates from 10 years ago to 1 year in future
                    if (today - date_obj).days > 3650:
                        errors.append(f"Datum zu weit in der Vergangenheit: {datum}")
                    if (date_obj - today).days > 365:
                        errors.append(f"Datum zu weit in der Zukunft: {datum}")
                except:
                    pass
        
        if faellig:
            if not self._is_valid_date(faellig):
                errors.append(f"Ungültiges Fälligkeitsdatum: {faellig}")
        
        # Check if Fälligkeitsdatum >= Rechnungsdatum
        if datum and faellig:
            try:
                datum_obj = datetime.strptime(datum, '%Y-%m-%d')
                faellig_obj = datetime.strptime(faellig, '%Y-%m-%d')
                
                if faellig_obj < datum_obj:
                    errors.append(
                        f"Fälligkeitsdatum ({faellig}) vor Rechnungsdatum ({datum})"
                    )
            except:
                pass
        
        return errors
    
    def _validate_iban(self, data: Dict) -> List[str]:
        """Validate IBAN format"""
        errors = []
        
        iban = data.get('iban')
        if iban:
            # Remove spaces
            iban_clean = iban.replace(' ', '').upper()
            
            # Basic IBAN validation (DE: 22 chars, starts with DE)
            if not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]+$', iban_clean):
                errors.append(f"Ungültiges IBAN-Format: {iban}")
            
            # German IBAN specific
            if iban_clean.startswith('DE') and len(iban_clean) != 22:
                errors.append(f"Deutsche IBAN muss 22 Zeichen haben: {iban}")
        
        return errors
    
    def _validate_ust_idnr(self, data: Dict) -> List[str]:
        """Validate USt-IdNr format"""
        errors = []
        
        ust_idnr = data.get('ust_idnr')
        if ust_idnr:
            # Remove spaces
            ust_clean = ust_idnr.replace(' ', '').upper()
            
            # German USt-IdNr: DE + 9 digits
            if ust_clean.startswith('DE'):
                if not re.match(r'^DE[0-9]{9}$', ust_clean):
                    errors.append(f"Ungültige USt-IdNr (DE Format): {ust_idnr}")
            
            # General EU format: 2 letters + digits
            elif not re.match(r'^[A-Z]{2}[0-9A-Z]+$', ust_clean):
                errors.append(f"Ungültiges USt-IdNr Format: {ust_idnr}")
        
        return errors
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date string is valid YYYY-MM-DD format"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except:
            return False


class DataCleaner:
    """Cleans and normalizes extracted data"""
    
    @staticmethod
    def clean(data: Dict) -> Dict:
        """Clean and normalize data"""
        cleaned = data.copy()
        
        # Clean IBAN (remove spaces)
        if cleaned.get('iban'):
            cleaned['iban'] = cleaned['iban'].replace(' ', '').upper()
        
        # Clean USt-IdNr (remove spaces)
        if cleaned.get('ust_idnr'):
            cleaned['ust_idnr'] = cleaned['ust_idnr'].replace(' ', '').upper()
        
        # Clean BIC (remove spaces)
        if cleaned.get('bic'):
            cleaned['bic'] = cleaned['bic'].replace(' ', '').upper()
        
        # Normalize Währung
        if cleaned.get('waehrung'):
            cleaned['waehrung'] = cleaned['waehrung'].upper()
        elif cleaned.get('betrag_brutto'):
            # Default to EUR if amount exists but currency is missing
            cleaned['waehrung'] = 'EUR'
        
        # Round amounts to 2 decimals
        for field in ['betrag_brutto', 'betrag_netto', 'mwst_betrag']:
            if cleaned.get(field) is not None:
                try:
                    cleaned[field] = round(float(cleaned[field]), 2)
                except:
                    pass
        
        # Clean Lieferant (strip whitespace)
        if cleaned.get('lieferant'):
            cleaned['lieferant'] = cleaned['lieferant'].strip()
        
        return cleaned


def validate_and_clean(data: Dict, strict: bool = False) -> Tuple[Dict, bool, List[str]]:
    """
    Validate and clean data in one step
    Returns: (cleaned_data, is_valid, errors)
    """
    # Clean first
    cleaner = DataCleaner()
    cleaned_data = cleaner.clean(data)
    
    # Then validate
    validator = InvoiceValidator(strict=strict)
    is_valid, errors = validator.validate(cleaned_data)
    
    return cleaned_data, is_valid, errors
