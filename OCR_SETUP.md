# OCR Feature Setup Guide

Complete guide for setting up and using the OCR (Optical Character Recognition) feature to automatically extract information from receipt images.

## 📋 Table of Contents

- [What Does OCR Do?](#-what-does-ocr-do)
- [Installation Options](#-installation-options)
- [Quick Start](#-quick-start)
- [Testing OCR](#-testing-ocr)
- [Using OCR in Web Interface](#-using-ocr-in-the-web-interface)
- [Tips for Best Results](#-tips-for-best-ocr-results)
- [Troubleshooting](#-troubleshooting)
- [Language Support](#-language-support)
- [Advanced Usage](#-advanced-usage)

---

## 🎯 What Does OCR Do?

The OCR feature automatically reads text from receipt images and extracts:
- **Shop/Merchant name**
- **Purchase date**
- **Total amount**
- **Individual items** (names and prices)
- **Raw text** (complete OCR output)

You can then review and edit the extracted information before saving.

### Workflow

```
1. User uploads receipt image 📷
       ↓
2. OCR extracts text 🔍
       ↓
3. Parser identifies fields 🏷️
       ↓
4. Form pre-fills with data ✍️
       ↓
5. User reviews & edits 👀
       ↓
6. Receipt saved to database 💾
```

---

## 📦 Installation Options

You have two OCR engine choices:

### Option 1: EasyOCR (Recommended)

**Advantages:**
- More accurate text recognition
- Supports 80+ languages out of the box
- No additional system installations needed
- Works well with multilingual receipts (English, Dutch, Greek, etc.)

**Disadvantages:**
- Larger download (~500MB for models on first run)
- Slightly slower on first use

**Installation:**
```bash
pip install easyocr pillow numpy
```

### Option 2: Tesseract OCR

**Advantages:**
- Lightweight and fast
- Industry standard
- Lower memory usage

**Disadvantages:**
- Requires system installation
- May be less accurate on some receipts
- Needs language packs installed separately

**Installation:**

**macOS:**
```bash
brew install tesseract
pip install pytesseract pillow
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
pip install pytesseract pillow
```

**Windows:**
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install Tesseract
3. Add to PATH or note installation directory
4. Install Python package:
```bash
pip install pytesseract pillow
```

### Installing Language Packs (Tesseract only)

For multilingual support with Tesseract:

**macOS:**
```bash
brew install tesseract-lang
```

**Ubuntu/Debian:**
```bash
# Dutch
sudo apt-get install tesseract-ocr-nld
# Greek
sudo apt-get install tesseract-ocr-ell
# German
sudo apt-get install tesseract-ocr-deu
```

### Comparison: EasyOCR vs Tesseract

| Feature | EasyOCR | Tesseract |
|---------|---------|-----------|
| **Accuracy** | ⭐⭐⭐⭐⭐ Higher | ⭐⭐⭐⭐ Good |
| **Speed** | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐ Fast |
| **Setup** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐ Requires system install |
| **Languages** | 80+ built-in | Install per language |
| **Memory** | ~500MB | ~50MB |
| **GPU Support** | ✅ Yes | ❌ No |
| **Multi-lingual** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good |
| **Maintenance** | pip install | System updates |

**Recommendation:** Start with EasyOCR for best results, switch to Tesseract if you need lower memory usage.

---

## 🚀 Quick Start

### 1. Install Dependencies

**For EasyOCR (recommended):**
```bash
cd receipts-manager
pip install -r requirements.txt
```

**For Tesseract:**
```bash
# Install Tesseract system package first (see above)
pip install pytesseract pillow
```

### 2. Test OCR from Command Line

Test the OCR service with a receipt image:

```bash
# Using EasyOCR (default)
python ocr_service.py path/to/receipt.jpg

# Using Tesseract
python ocr_service.py path/to/receipt.jpg tesseract
```

Example output:
```
Processing receipt with easyocr...
------------------------------------------------------------

Shop: Albert Heijn B.V.
Date: 2024-Feb-15
Total: €45.67

Items found: 5
  - Melk Halfvol 1L: €1.29
  - Brood Volkoren: €2.15
  - Appels Elstar 1kg: €2.99
  - Koffie Filtermaling: €4.85
  - Kaas Jong Belegen: €3.49

------------------------------------------------------------
Raw extracted text:
Albert Heijn B.V.
Hoofdstraat 123
1234 AB Amsterdam

Date: 15-02-2024
Time: 14:23
...
```

### 3. Configure for Your Languages

Edit the OCR service initialization in `app.py` or `ocr_service.py`:

```python
# For English and Dutch receipts
ocr_service = OCRService(engine="easyocr", languages=['en', 'nl'])

# For English, Dutch, Greek, and Latvian receipts
ocr_service = OCRService(engine="easyocr", languages=['en', 'nl', 'el', 'lv'])

# For Tesseract (uses system language packs)
ocr_service = OCRService(engine="tesseract", languages=['eng', 'nld', 'ell'])
```

---

## 🧪 Testing OCR

### Quick Test Script

Create `test_ocr.py`:

```python
#!/usr/bin/env python3
"""Test OCR functionality"""

import sys
from ocr_service import extract_receipt_data

def test_ocr(image_path, engine='easyocr'):
    """Test OCR on a receipt image."""
    print(f"\n{'='*60}")
    print(f"Testing OCR with {engine}")
    print(f"Image: {image_path}")
    print(f"{'='*60}\n")
    
    try:
        # Extract data
        data = extract_receipt_data(
            image_path,
            engine=engine,
            languages=['en', 'nl', 'el', 'lv']  # Your languages
        )
        
        # Display results
        print("✅ OCR Successful!\n")
        
        print(f"Shop:          {data.get('shop', 'N/A')}")
        print(f"Date:          {data.get('purchase_date', 'N/A')}")
        
        if data.get('total_amount'):
            print(f"Total:         €{data['total_amount']:.2f}")
        else:
            print(f"Total:         N/A")
        
        print(f"\nItems found:   {len(data.get('items', []))}")
        for i, item in enumerate(data.get('items', [])[:5], 1):
            print(f"  {i}. {item['name']:<30} €{item['price']}")
        
        if len(data.get('items', [])) > 5:
            print(f"  ... and {len(data['items']) - 5} more items")
        
        print(f"\n{'-'*60}")
        print("Raw text (first 500 chars):")
        print(f"{'-'*60}")
        raw = data.get('raw_text', '')
        print(raw[:500])
        if len(raw) > 500:
            print("...\n[truncated]")
        
        print(f"\n{'='*60}")
        print("✅ Test PASSED")
        print(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ocr.py <image_path> [engine]")
        print("  engine: easyocr (default) or tesseract")
        sys.exit(1)
    
    image = sys.argv[1]
    engine = sys.argv[2] if len(sys.argv) > 2 else "easyocr"
    
    success = test_ocr(image, engine)
    sys.exit(0 if success else 1)
```

Run the test:
```bash
python test_ocr.py receipt.jpg
```

### Test Cases

#### Test Case 1: Perfect Receipt
- **Input:** Clear, well-lit photo of printed receipt
- **Expected:** All fields extracted correctly

#### Test Case 2: Poor Quality
- **Input:** Blurry or dark photo
- **Expected:** Some fields may be "N/A", manual editing required

#### Test Case 3: Faded Thermal Receipt
- **Input:** Old thermal receipt with faded text
- **Expected:** May fail to extract text

#### Test Case 4: Multilingual Receipt
- **Input:** Receipt with mixed languages (Dutch + English)
- **Expected:** Both languages recognized with proper configuration

#### Test Case 5: Handwritten Receipt
- **Input:** Handwritten receipt or notes
- **Expected:** Lower accuracy, likely needs manual correction

### Automated Batch Testing

Create `test_all_receipts.sh`:

```bash
#!/bin/bash
# Test all receipts in a folder

echo "Testing OCR on all receipt images..."
echo "===================================="

pass=0
fail=0

for img in test_receipts/*.jpg test_receipts/*.png; do
    if [ -f "$img" ]; then
        echo "\nTesting: $img"
        if python ocr_service.py "$img" > /dev/null 2>&1; then
            echo "✅ PASS: $img"
            ((pass++))
        else
            echo "❌ FAIL: $img"
            ((fail++))
        fi
    fi
done

echo "\n===================================="
echo "Results: $pass passed, $fail failed"
echo "===================================="
```

Make executable and run:
```bash
chmod +x test_all_receipts.sh
./test_all_receipts.sh
```

### Benchmark Testing

Compare EasyOCR vs Tesseract performance:

```python
#!/usr/bin/env python3
import time
from ocr_service import extract_receipt_data

def benchmark(image_path):
    engines = ['easyocr', 'tesseract']
    
    print(f"\nBenchmarking: {image_path}")
    print("=" * 60)
    
    for engine in engines:
        try:
            start = time.time()
            data = extract_receipt_data(image_path, engine=engine)
            elapsed = time.time() - start
            
            print(f"\n{engine.upper()}:")
            print(f"  Time:  {elapsed:.2f}s")
            print(f"  Shop:  {data.get('shop', 'N/A')[:30]}")
            print(f"  Date:  {data.get('purchase_date', 'N/A')}")
            print(f"  Items: {len(data.get('items', []))}")
            
        except Exception as e:
            print(f"\n{engine.upper()}: FAILED - {e}")
    
    print("\n" + "=" * 60)

# Usage
benchmark('receipt.jpg')
```

---

## 🎨 Using OCR in the Web Interface

### Method 1: Drag and Drop
1. Open the Receipt Manager web interface
2. Drag a receipt image into the upload area
3. The OCR will automatically process the image
4. Review the extracted information
5. Edit any incorrect fields
6. Click "Save Receipt"

### Method 2: File Upload
1. Click the "Choose File" button
2. Select your receipt image
3. OCR processes automatically
4. Review and edit the extracted data
5. Save the receipt

---

## 📋 Supported Image Formats

- **JPEG/JPG** (.jpg, .jpeg)
- **PNG** (.png)
- **BMP** (.bmp)
- **TIFF** (.tiff, .tif)
- **WebP** (.webp)

---

## 💡 Tips for Best OCR Results

### Image Quality

✅ **Good practices:**
- **Good lighting** - Natural daylight or bright indoor lighting
- **Straight angle** - Hold camera directly above receipt
- **In focus** - Ensure text is sharp and readable
- **Flat surface** - Lay receipt flat, avoid folds or wrinkles
- **High resolution** - Use at least 1200x1600 pixels
- **Avoid shadows** - Ensure even lighting across the receipt

### Receipt Condition

✅ **What works best:**
- **Clean receipts** - Avoid stains or tears
- **Printed receipts** - Better than handwritten notes
- **Dark text on light background** - Most reliable
- **Fresh thermal receipts** - Scan before they fade

### Common Receipt Types

| Receipt Type | OCR Accuracy |
|--------------|--------------|
| **Supermarket** (Albert Heijn, Jumbo) | ⭐⭐⭐⭐⭐ Excellent |
| **Restaurant bills** (printed) | ⭐⭐⭐⭐ Good |
| **Retail receipts** (clothing, electronics) | ⭐⭐⭐⭐⭐ Excellent |
| **Gas station receipts** | ⭐⭐⭐⭐ Good |
| **Pharmacy receipts** | ⭐⭐⭐⭐ Good |
| **Handwritten receipts** | ⭐⭐ Poor (manual review needed) |
| **Faded thermal receipts** | ⭐ Very Poor |

### Image Preprocessing (Optional)

For challenging receipts, you can improve OCR accuracy with preprocessing:

```python
import cv2
import numpy as np
from PIL import Image

def preprocess_receipt(image_path, output_path):
    """Enhance receipt image for better OCR."""
    # Read image
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Reduce noise
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # Binarize (black and white)
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Save processed image
    cv2.imwrite(output_path, binary)
    return output_path

# Use it
processed = preprocess_receipt('receipt.jpg', 'receipt_processed.jpg')
data = extract_receipt_data(processed)
```

---

## 🔧 Troubleshooting

### EasyOCR Issues

**"Module not found: easyocr"**
```bash
pip install easyocr pillow numpy
```

**"Downloading model files..." (first run)**
- This is normal on first use
- Models are cached for future use (~500MB download)
- Subsequent runs will be much faster

**"CUDA not available" warning**
- This is normal if you don't have a GPU
- OCR will use CPU (still works fine, just slower)
- For GPU support: `pip install torch torchvision`

**Very slow first run**
- EasyOCR downloads language models on first use
- This only happens once
- Cached models make future runs fast

### Tesseract Issues

**"TesseractNotFoundError"**
- Tesseract is not installed or not in PATH
- Install using instructions above
- On Windows, you may need to set the path:
  ```python
  import pytesseract
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

**"Failed to load language"**
- Language pack not installed
- Install using instructions above for your OS

### Poor OCR Accuracy

**If extracted text is gibberish:**
1. Check image quality (see tips above)
2. Try the other OCR engine (EasyOCR vs Tesseract)
3. Ensure correct language codes are configured
4. Preprocess the image (see preprocessing section)

**If shop name is wrong:**
- OCR picks the first substantial text line
- Manually edit the field after extraction
- Shop name will be remembered for future receipts

**If date is wrong:**
- Multiple date formats are supported
- If OCR fails, it defaults to today's date
- Manually correct and save

**If items are missing:**
- OCR looks for price patterns (numbers with 2 decimals)
- Some receipts have unusual formatting
- Add items manually if needed

**If total amount is wrong:**
- OCR looks for the largest amount or "total" keyword
- Verify the amount manually
- Some receipts list subtotals that may confuse the parser

---

## 🌍 Language Support

### EasyOCR Language Codes

Common languages for European receipts:
- `'en'` - English
- `'nl'` - Dutch (Nederlands)
- `'el'` - Greek (Ελληνικά)
- `'lv'` - Latvian (Latviešu)
- `'de'` - German (Deutsch)
- `'fr'` - French (Français)
- `'it'` - Italian (Italiano)
- `'es'` - Spanish (Español)
- `'pt'` - Portuguese (Português)

**Multilingual family setup (English, Dutch, Greek, Latvian):**
```python
ocr_service = OCRService(engine="easyocr", languages=['en', 'nl', 'el', 'lv'])
```

Full list: https://www.jaided.ai/easyocr/

### Tesseract Language Codes

Use 3-letter ISO codes:
- `'eng'` - English
- `'nld'` - Dutch
- `'ell'` - Greek
- `'lav'` - Latvian
- `'deu'` - German
- `'fra'` - French
- `'ita'` - Italian
- `'spa'` - Spanish
- `'por'` - Portuguese

---

## 🔒 Privacy & Security

- ✅ **Local processing** - All OCR happens on your computer
- ✅ **No cloud** - Receipt images are never sent to external services
- ✅ **Your data** - Stays in your `_Receipts` folder
- ✅ **Open source** - You can inspect the code
- ✅ **No internet** - After initial model download, works offline

---

## 📚 Advanced Usage

### Batch Processing from Command Line

Process multiple receipts:

```bash
#!/bin/bash
# Process all receipts in a folder

for img in receipts/*.jpg receipts/*.png; do
    if [ -f "$img" ]; then
        echo "Processing $img..."
        python ocr_service.py "$img" easyocr
        echo "---"
    fi
done
```

### Custom Parsing Rules

You can customize the parsing logic in `ocr_service.py`:

```python
def _extract_shop(self, text: str) -> str:
    """Customize shop extraction logic."""
    # Add your custom logic here
    # For example, prioritize certain stores:
    if 'albert heijn' in text.lower():
        return 'Albert Heijn'
    if 'jumbo' in text.lower():
        return 'Jumbo'
    # ... rest of logic
    return self._get_first_line(text)
```

### Python API Usage

Use OCR as a Python module:

```python
from ocr_service import extract_receipt_data

# Extract data
data = extract_receipt_data(
    'receipt.jpg', 
    engine='easyocr',
    languages=['en', 'nl', 'el', 'lv']
)

# Access extracted data
print(f"Shop: {data['shop']}")
print(f"Date: {data['purchase_date']}")
print(f"Total: €{data['total_amount']}")

# Process items
for item in data['items']:
    print(f"  - {item['name']}: €{item['price']}")

# Full raw text
print(f"\nRaw OCR text:\n{data['raw_text']}")
```

### Integration with Other Tools

Export OCR data to Excel:

```python
import pandas as pd
from ocr_service import extract_receipt_data

# Process receipt
data = extract_receipt_data('receipt.jpg')

# Create DataFrame
df = pd.DataFrame({
    'Item': [item['name'] for item in data['items']],
    'Price': [item['price'] for item in data['items']],
    'Shop': data['shop'],
    'Date': data['purchase_date']
})

# Export to Excel
df.to_excel('receipt_data.xlsx', index=False)
print("Exported to receipt_data.xlsx")
```

---

## 🆘 Getting Help

If you encounter issues:

1. ✅ Check this documentation
2. ✅ Test with the command-line tool first (`python ocr_service.py receipt.jpg`)
3. ✅ Verify your image quality (see tips above)
4. ✅ Try the other OCR engine
5. ✅ Check the GitHub issues: https://github.com/SaVaGi-eu/receipts-manager/issues
6. ✅ Create a new issue with:
   - Your OS (macOS, Linux, Windows)
   - OCR engine used (EasyOCR or Tesseract)
   - Example receipt image (remove personal info)
   - Complete error message
   - Output of `python --version`

---

## ✅ Success Criteria

OCR is working correctly when:

- ✅ OCR service installs without errors
- ✅ Can process receipt images from command line
- ✅ Extracts shop name (may need manual correction)
- ✅ Extracts date (or defaults to today)
- ✅ Extracts total amount (if visible on receipt)
- ✅ Extracts 3+ items with prices
- ✅ Raw text is readable
- ✅ Processing completes in <10 seconds (after first run)
- ✅ Web interface shows extracted data in form fields

---

## 📝 Next Steps

Once OCR is working:

1. ✅ Test from command line with various receipts
2. ✅ Configure your languages
3. ✅ Use the web interface to upload receipts
4. ✅ Build your receipt database with minimal typing
5. ✅ Export data for expense reports

---

**Happy receipt scanning! 📸✨**
