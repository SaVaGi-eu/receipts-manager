#!/usr/bin/env python3
"""
OCR Service for Receipt Text Extraction
Supports both EasyOCR (more accurate) and Tesseract (lightweight)
Supports both images (JPG, PNG) and PDF files
"""

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import pytesseract

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sanitize_for_logging(text: str, max_length: int = 200) -> str:
    """
    SECURITY: Sanitize user input before logging to prevent log injection.
    Removes newlines, carriage returns, and other control characters that could
    be used to forge log entries or inject malicious content into logs.

    Args:
        text: User-controlled text to sanitize
        max_length: Maximum length to truncate to

    Returns:
        Sanitized text safe for logging
    """
    if not text:
        return ""
    # Remove control characters including CR, LF, and other escape sequences
    sanitized = re.sub(r"[\r\n\x00-\x1f\x7f]", "", str(text))
    # Truncate to prevent log flooding
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


def get_tesseract_config():
    """
    Detect if running from .app bundle and configure Tesseract paths accordingly.
    Returns tuple: (tesseract_cmd, tessdata_dir)
    """
    import sys

    if getattr(sys, "frozen", False):
        # Running in .app bundle (py2app)
        if hasattr(sys, "_MEIPASS"):
            # PyInstaller
            bundle_dir = sys._MEIPASS
        else:
            # py2app
            bundle_dir = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))

        tesseract_cmd = os.path.join(bundle_dir, "Resources", "tesseract", "bin", "tesseract")
        tessdata_dir = os.path.join(bundle_dir, "Resources", "tesseract", "tessdata")

        if os.path.exists(tesseract_cmd):
            logger.info("Using bundled Tesseract: %s", tesseract_cmd)
            return tesseract_cmd, tessdata_dir
        else:
            logger.warning("Bundled Tesseract not found at %s, falling back to system", tesseract_cmd)

    # Running from source or bundled Tesseract not found - use system
    logger.info("Using system Tesseract")
    return "tesseract", None  # Use system default


# Configure Tesseract on module import
tesseract_cmd, tessdata_dir = get_tesseract_config()
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

if tessdata_dir:
    # Set TESSDATA_PREFIX environment variable for bundled tessdata
    os.environ["TESSDATA_PREFIX"] = tessdata_dir

# Check for PDF support
try:
    from pdf2image import convert_from_path

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("PDF support not available. Install with: pip3 install pdf2image")


class OCRService:
    """
    OCR service for extracting text from receipt images and PDFs.
    Supports both EasyOCR and Tesseract OCR engines.
    """

    def __init__(self, engine: str = "easyocr", languages: List[str] = None):
        """
        Initialize OCR service.

        Args:
            engine: OCR engine to use ("easyocr" or "tesseract")
            languages: List of language codes (e.g., ['en', 'nl', 'el'])
        """
        self.engine = engine.lower()
        self.languages = languages or ["en"]
        self.reader = None

        if self.engine == "easyocr":
            self._init_easyocr()
        elif self.engine == "tesseract":
            self._init_tesseract()
        else:
            raise ValueError(f"Unsupported OCR engine: {engine}")

    def _init_easyocr(self):
        """Initialize EasyOCR reader."""
        try:
            import easyocr

            logger.info(f"Initializing EasyOCR with languages: {self.languages}")
            self.reader = easyocr.Reader(self.languages, gpu=False)
            logger.info("EasyOCR initialized successfully")
        except ImportError:
            raise ImportError("EasyOCR not installed. Install with: pip3 install easyocr")
        except Exception as e:
            # SECURITY: Sanitize exception message before logging
            safe_msg = sanitize_for_logging(str(e))
            logger.error(f"Failed to initialize EasyOCR: {safe_msg}")
            raise

    def _init_tesseract(self):
        """Initialize Tesseract OCR."""
        try:
            from PIL import Image  # noqa: F401

            # Test if Tesseract is installed
            pytesseract.get_tesseract_version()
            self.reader = pytesseract
            logger.info("Tesseract initialized successfully")
        except ImportError:
            raise ImportError("pytesseract not installed. Install with: pip3 install pytesseract pillow")
        except pytesseract.TesseractNotFoundError:
            raise RuntimeError(
                "Tesseract OCR not found. Install Tesseract:\n"
                "  macOS: brew install tesseract\n"
                "  Ubuntu: sudo apt-get install tesseract-ocr\n"
                "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki"
            )

    def _is_pdf(self, file_path: str) -> bool:
        """Check if file is a PDF."""
        return file_path.lower().endswith(".pdf")

    def _pdf_to_images(self, pdf_path: str) -> List:
        """
        Convert PDF pages to images.
        Returns list of PIL Image objects.
        """
        if not PDF_SUPPORT:
            raise ImportError(
                "PDF support not available. Install with: pip3 install pdf2image\n"
                "Also install poppler:\n"
                "  macOS: brew install poppler\n"
                "  Ubuntu: sudo apt-get install poppler-utils\n"
                "  Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/"
            )

        try:
            # SECURITY: Strip CR/LF inline at the logger call to prevent log injection.
            # Use str.replace so CodeQL can track the sanitizer without an intermediate variable.
            logger.info("Converting PDF to images: %s", str(pdf_path).replace("\r", "").replace("\n", ""))

            # Convert PDF to images (one per page)
            images = convert_from_path(pdf_path, dpi=300)
            logger.info(f"Converted {len(images)} page(s) from PDF")
            return images
        except Exception as e:
            # SECURITY: Sanitize exception message before logging
            safe_msg = sanitize_for_logging(str(e))
            logger.error(f"Failed to convert PDF: {safe_msg}")
            raise

    def _extract_text_from_pil_image(self, pil_image) -> str:
        """Extract text from PIL Image using EasyOCR."""
        import numpy as np

        # Convert PIL image to numpy array for EasyOCR
        image_np = np.array(pil_image)
        result = self.reader.readtext(image_np, detail=0, paragraph=False)
        return "\n".join(result)

    def _extract_text_tesseract_pil(self, pil_image) -> str:
        """Extract text from PIL Image using Tesseract."""
        config = "--psm 6"
        text = self.reader.image_to_string(pil_image, config=config)
        return text

    def extract_text(self, image_path: str) -> str:
        """
        Extract raw text from image or PDF.

        Args:
            image_path: Path to the receipt image or PDF

        Returns:
            Extracted text as string
        """
        # Handle PDF files
        if self._is_pdf(image_path):
            # SECURITY: Strip CR/LF inline at the logger call to prevent log injection.
            # Use str.replace so CodeQL can track the sanitizer without an intermediate variable.
            logger.info("Processing PDF file: %s", str(image_path).replace("\r", "").replace("\n", ""))
            images = self._pdf_to_images(image_path)

            # Extract text from all pages
            all_text = []
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)}")
                if self.engine == "easyocr":
                    text = self._extract_text_from_pil_image(image)
                elif self.engine == "tesseract":
                    text = self._extract_text_tesseract_pil(image)
                all_text.append(text)

            return "\n\n--- PAGE BREAK ---\n\n".join(all_text)

        # Handle regular images
        if self.engine == "easyocr":
            return self._extract_text_easyocr(image_path)
        elif self.engine == "tesseract":
            return self._extract_text_tesseract(image_path)
        return ""

    def _extract_text_easyocr(self, image_path: str) -> str:
        """Extract text using EasyOCR."""
        result = self.reader.readtext(image_path, detail=0, paragraph=False)
        return "\n".join(result)

    def _extract_text_tesseract(self, image_path: str) -> str:
        """Extract text using Tesseract."""
        from PIL import Image

        image = Image.open(image_path)
        # Use PSM 6 for uniform text blocks (receipts)
        config = "--psm 6"
        text = self.reader.image_to_string(image, config=config)
        return text

    def parse_receipt(self, image_path: str) -> Dict[str, any]:
        """
        Extract and parse receipt information from image or PDF.

        Args:
            image_path: Path to the receipt image or PDF

        Returns:
            Dictionary with parsed receipt data
        """
        # Extract raw text
        text = self.extract_text(image_path)

        # SECURITY: Don't log full raw text as it may contain sensitive data
        # Only log length for debugging
        logger.info(f"Extracted {len(text)} characters from receipt")

        # Parse the text
        parsed_data = self._parse_receipt_text(text)

        return parsed_data

    def _parse_receipt_text(self, text: str) -> Dict[str, any]:
        """
        Parse extracted text to extract structured data.

        Args:
            text: Raw OCR text

        Returns:
            Dictionary with parsed fields
        """
        data = {
            "shop": self._extract_shop(text),
            "purchase_date": self._extract_date(text),
            "total_amount": self._extract_total(text),
            "items": self._extract_items(text),
            "raw_text": text,
        }

        return data

    def _extract_shop(self, text: str) -> str:
        """
        Extract shop/merchant name from receipt text.
        Usually the first few lines.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Common shop/merchant indicators
        shop_keywords = [
            "store",
            "shop",
            "market",
            "mart",
            "supermarket",
            "restaurant",
            "cafe",
            "ltd",
            "inc",
            "bv",
            "b.v.",
        ]

        # Check first 5 lines for shop name
        for i, line in enumerate(lines[:5]):
            # Skip very short lines or lines with only numbers
            if len(line) < 3 or line.replace(" ", "").isdigit():
                continue

            # Check if line contains shop keywords
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in shop_keywords):
                return line

            # If first substantial line, likely shop name
            if i == 0 and len(line) > 3:
                return line

        return lines[0] if lines else "Unknown"

    def _extract_date(self, text: str) -> str:
        """
        Extract purchase date from receipt text.
        Returns date in YYYY-MMM-DD format.
        """
        # Common date patterns
        patterns = [
            # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
            r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b",
            # YYYY/MM/DD or YYYY-MM-DD
            r"\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b",
            # DD MMM YYYY or DD MMMM YYYY
            r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()

                    if len(groups) == 3:
                        if len(groups[0]) == 4:  # YYYY-MM-DD
                            year, month, day = groups
                        elif groups[1].isalpha():  # DD MMM YYYY
                            day, month_str, year = groups
                            month = datetime.strptime(month_str[:3], "%b").month
                        else:  # DD/MM/YYYY
                            day, month, year = groups

                        # Create date object
                        date_obj = datetime(int(year), int(month), int(day))
                        return date_obj.strftime("%Y-%b-%d")
                except (ValueError, AttributeError):
                    continue

        # Default to today if no date found
        return datetime.now().strftime("%Y-%b-%d")

    def _extract_total(self, text: str) -> Optional[float]:
        """
        Extract total amount from receipt text.
        """
        # Common total indicators
        total_keywords = ["total", "totaal", "σύνολο", "sum", "amount", "te betalen", "to pay", "balance"]

        lines = text.split("\n")

        # Look for total amount
        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Check if line contains total keyword
            if any(keyword in line_lower for keyword in total_keywords):
                # Extract number from this line or next line
                for check_line in [line, lines[i + 1] if i + 1 < len(lines) else ""]:
                    # Find currency amounts (e.g., 12.34, €12.34, $12.34)
                    amounts = re.findall(r"[€$]?\s*(\d+[.,]\d{2})", check_line)
                    if amounts:
                        # Return the largest amount (likely the total)
                        amount_str = max(amounts, key=lambda x: float(x.replace(",", ".")))
                        return float(amount_str.replace(",", "."))

        return None

    def _extract_items(self, text: str) -> List[Dict[str, str]]:
        """
        Extract item names and prices from receipt text.
        This is a basic implementation - can be enhanced.
        """
        items = []
        lines = text.split("\n")

        # Look for lines with item name and price
        for line in lines:
            # Skip very short lines
            if len(line.strip()) < 3:
                continue

            # Find price patterns (number with 2 decimals)
            price_matches = re.findall(r"(\d+[.,]\d{2})", line)

            if price_matches:
                # Extract item name (everything before the price)
                for price in price_matches:
                    parts = line.split(price)
                    if parts[0].strip():
                        item_name = parts[0].strip()
                        # Clean up item name
                        item_name = re.sub(r"^\d+\s*x?\s*", "", item_name)  # Remove quantity

                        if len(item_name) > 2:  # Valid item name
                            items.append({"name": item_name, "price": price.replace(",", ".")})
                            break  # Only take first price per line

        return items[:10]  # Limit to first 10 items


# Convenience functions
def create_ocr_service(engine: str = "easyocr", languages: List[str] = None) -> OCRService:
    """
    Create and initialize an OCR service.

    Args:
        engine: "easyocr" (more accurate) or "tesseract" (lightweight)
        languages: List of language codes, e.g., ['en', 'nl', 'el']

    Returns:
        Initialized OCRService instance
    """
    return OCRService(engine=engine, languages=languages)


def extract_receipt_data(image_path: str, engine: str = "easyocr", languages: List[str] = None) -> Dict[str, any]:
    """
    Convenience function to extract receipt data from image or PDF.

    Args:
        image_path: Path to receipt image or PDF
        engine: OCR engine to use
        languages: List of language codes

    Returns:
        Dictionary with extracted receipt data
    """
    service = create_ocr_service(engine=engine, languages=languages)
    return service.parse_receipt(image_path)


if __name__ == "__main__":
    # Test the OCR service
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr_service.py <image_path> [engine]")
        print("  engine: easyocr (default) or tesseract")
        sys.exit(1)

    image_path = sys.argv[1]
    engine = sys.argv[2] if len(sys.argv) > 2 else "easyocr"

    print(f"Processing receipt with {engine}...")
    print("-" * 60)

    try:
        data = extract_receipt_data(image_path, engine=engine, languages=["en", "nl"])

        print(f"\nShop: {data['shop']}")
        print(f"Date: {data['purchase_date']}")
        print(f"Total: €{data['total_amount']}" if data["total_amount"] else "Total: Not found")
        print(f"\nItems found: {len(data['items'])}")
        for item in data["items"]:
            print(f"  - {item['name']}: €{item['price']}")

        print("\n" + "-" * 60)
        print("Raw extracted text:")
        print(data["raw_text"])

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
