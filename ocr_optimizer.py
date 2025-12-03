#!/usr/bin/env python3
"""
SBS Deutschland – OCR Optimizer
Verbesserte Texterkennung für gescannte PDFs.
"""

import logging
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# Tesseract-Konfigurationen für verschiedene Dokumenttypen
OCR_CONFIGS = {
    'default': '--oem 3 --psm 6 -l deu+eng',
    'invoice': '--oem 3 --psm 4 -l deu+eng',  # Spalten-Layout
    'dense': '--oem 3 --psm 3 -l deu+eng',    # Vollautomatisch
    'sparse': '--oem 3 --psm 11 -l deu+eng',  # Sparse Text
}


def preprocess_image(image: Image.Image, method: str = 'standard') -> Image.Image:
    """
    Bildvorverarbeitung für bessere OCR-Ergebnisse.
    
    Args:
        image: PIL Image
        method: Vorverarbeitungsmethode
        
    Returns:
        Verarbeitetes Image
    """
    # Zu Graustufen konvertieren
    if image.mode != 'L':
        image = image.convert('L')
    
    if method == 'standard':
        # Kontrast erhöhen
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Schärfen
        image = image.filter(ImageFilter.SHARPEN)
        
    elif method == 'high_contrast':
        # Sehr hoher Kontrast für verblasste Dokumente
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.2)
        
        image = image.filter(ImageFilter.SHARPEN)
        
    elif method == 'binarize':
        # Binarisierung für sehr schlechte Scans
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.5)
        
        # Schwellenwert
        threshold = 140
        image = image.point(lambda x: 255 if x > threshold else 0, '1')
        image = image.convert('L')
        
    elif method == 'denoise':
        # Rauschunterdrückung
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)
    
    return image


def extract_text_with_confidence(image: Image.Image, config: str = 'default') -> Tuple[str, float]:
    """
    Extrahiert Text mit Konfidenz-Score.
    
    Returns:
        Tuple (text, confidence)
    """
    ocr_config = OCR_CONFIGS.get(config, OCR_CONFIGS['default'])
    
    try:
        # OCR mit detaillierten Daten
        data = pytesseract.image_to_data(image, config=ocr_config, output_type=pytesseract.Output.DICT)
        
        # Text zusammenbauen
        words = []
        confidences = []
        
        for i, word in enumerate(data['text']):
            if word.strip():
                words.append(word)
                conf = int(data['conf'][i])
                if conf > 0:  # -1 = keine Konfidenz
                    confidences.append(conf)
        
        text = ' '.join(words)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return text, avg_confidence / 100  # Normalisiert auf 0-1
        
    except Exception as e:
        logger.error(f"OCR-Fehler: {e}")
        return "", 0.0


def ocr_with_fallback(image: Image.Image) -> Dict:
    """
    Führt OCR mit mehreren Methoden durch und wählt das beste Ergebnis.
    
    Returns:
        Dict mit text, confidence, method
    """
    results = []
    
    # Verschiedene Vorverarbeitungen durchprobieren
    preprocessing_methods = ['standard', 'high_contrast', 'denoise']
    ocr_configs = ['default', 'invoice', 'dense']
    
    for preprocess in preprocessing_methods:
        processed = preprocess_image(image.copy(), preprocess)
        
        for config in ocr_configs:
            text, confidence = extract_text_with_confidence(processed, config)
            
            if text and len(text) > 50:  # Mindestlänge
                results.append({
                    'text': text,
                    'confidence': confidence,
                    'preprocess': preprocess,
                    'config': config,
                    'char_count': len(text)
                })
    
    if not results:
        # Letzter Versuch: Binarisierung
        processed = preprocess_image(image.copy(), 'binarize')
        text, confidence = extract_text_with_confidence(processed, 'default')
        return {
            'text': text,
            'confidence': confidence,
            'method': 'binarize_fallback'
        }
    
    # Bestes Ergebnis auswählen (Kombination aus Konfidenz und Textlänge)
    def score(r):
        # Gewichtung: 70% Konfidenz, 30% normalisierte Textlänge
        max_len = max(r['char_count'] for r in results)
        len_score = r['char_count'] / max_len if max_len > 0 else 0
        return r['confidence'] * 0.7 + len_score * 0.3
    
    best = max(results, key=score)
    
    return {
        'text': best['text'],
        'confidence': best['confidence'],
        'method': f"{best['preprocess']}_{best['config']}"
    }


def extract_from_pdf_optimized(pdf_path: str, dpi: int = 200) -> Dict:
    """
    Optimierte OCR-Extraktion aus PDF.
    
    Args:
        pdf_path: Pfad zur PDF
        dpi: Auflösung für Bildkonvertierung
        
    Returns:
        Dict mit text, confidence, pages, method
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.error("pdf2image nicht installiert")
        return {'text': '', 'confidence': 0, 'error': 'pdf2image missing'}
    
    try:
        # PDF zu Bildern konvertieren
        images = convert_from_path(pdf_path, dpi=dpi, fmt='png')
        
        all_text = []
        total_confidence = 0
        methods_used = set()
        
        for i, image in enumerate(images):
            logger.info(f"OCR Seite {i+1}/{len(images)}")
            
            result = ocr_with_fallback(image)
            
            if result['text']:
                all_text.append(f"--- Seite {i+1} ---\n{result['text']}")
                total_confidence += result['confidence']
                methods_used.add(result['method'])
        
        combined_text = '\n\n'.join(all_text)
        avg_confidence = total_confidence / len(images) if images else 0
        
        return {
            'text': combined_text,
            'confidence': round(avg_confidence, 3),
            'pages': len(images),
            'methods': list(methods_used),
            'char_count': len(combined_text)
        }
        
    except Exception as e:
        logger.error(f"PDF OCR-Fehler: {e}")
        return {'text': '', 'confidence': 0, 'error': str(e)}


def detect_scan_quality(image: Image.Image) -> Dict:
    """
    Analysiert die Qualität eines gescannten Bildes.
    
    Returns:
        Dict mit quality_score, issues
    """
    issues = []
    score = 100
    
    # Zu Graustufen
    if image.mode != 'L':
        gray = image.convert('L')
    else:
        gray = image
    
    # Histogramm analysieren
    histogram = gray.histogram()
    total_pixels = sum(histogram)
    
    # Zu dunkel?
    dark_pixels = sum(histogram[:50]) / total_pixels
    if dark_pixels > 0.3:
        issues.append("Bild zu dunkel")
        score -= 20
    
    # Zu hell / ausgewaschen?
    light_pixels = sum(histogram[200:]) / total_pixels
    if light_pixels > 0.5:
        issues.append("Bild zu hell/ausgewaschen")
        score -= 20
    
    # Niedriger Kontrast?
    mid_pixels = sum(histogram[100:150]) / total_pixels
    if mid_pixels > 0.6:
        issues.append("Niedriger Kontrast")
        score -= 15
    
    # Auflösung prüfen
    width, height = image.size
    if width < 1000 or height < 1000:
        issues.append("Niedrige Auflösung")
        score -= 25
    
    return {
        'quality_score': max(0, score),
        'issues': issues,
        'resolution': f"{width}x{height}",
        'recommendation': 'high_contrast' if score < 70 else 'standard'
    }


def enhance_for_ocr(image_path: str, output_path: str = None) -> str:
    """
    Verbessert ein Bild für OCR und speichert es.
    
    Returns:
        Pfad zum verbesserten Bild
    """
    image = Image.open(image_path)
    
    # Qualität analysieren
    quality = detect_scan_quality(image)
    
    # Passende Vorverarbeitung wählen
    method = quality['recommendation']
    processed = preprocess_image(image, method)
    
    # Speichern
    if not output_path:
        p = Path(image_path)
        output_path = str(p.parent / f"{p.stem}_enhanced{p.suffix}")
    
    processed.save(output_path)
    logger.info(f"Bild verbessert: {output_path} (Methode: {method})")
    
    return output_path


# Für direkten Aufruf
if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        result = extract_from_pdf_optimized(pdf_path)
        print(f"Konfidenz: {result['confidence']*100:.1f}%")
        print(f"Methoden: {result.get('methods', [])}")
        print(f"Text ({result.get('char_count', 0)} Zeichen):")
        print(result['text'][:1000] + "..." if len(result['text']) > 1000 else result['text'])
