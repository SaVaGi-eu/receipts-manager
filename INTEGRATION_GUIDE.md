# OCR Integration Guide

This guide shows you how to integrate the OCR feature into your existing `app.py`.

## Step 1: Install Dependencies

```bash
# Install EasyOCR (recommended)
pip install easyocr pillow numpy

# OR install Tesseract
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr
pip install pytesseract pillow
```

## Step 2: Test OCR Service

First, test that OCR works:

```bash
# Test with a receipt image
python ocr_service.py path/to/your/receipt.jpg
```

If this works, proceed to integration.

## Step 3: Add OCR Endpoint to app.py

You need to add an OCR endpoint to your existing `app.py`. Here's what to add:

### A. Add OCR imports at the top of app.py

Add these imports after the existing imports:

```python
# Add after existing imports
import base64
from io import BytesIO
try:
    from ocr_service import extract_receipt_data
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR not available. Install: pip install easyocr")
```

### B. Add OCR configuration

After the directory definitions, add:

```python
# OCR Configuration
OCR_ENGINE = "easyocr"  # or "tesseract"
OCR_LANGUAGES = ['en', 'nl']  # English and Dutch
```

### C. Add OCR endpoint to the Handler class

Add this method to the `Handler` class in the `do_POST` method:

```python
def do_POST(self):
    parsed = urlparse(self.path)
    path = parsed.path

    # Add this NEW endpoint before existing endpoints
    if path == "/api/ocr/process":
        if not OCR_AVAILABLE:
            self._set_headers(500)
            self.wfile.write(b'{"success":false,"error":"OCR not available"}')
            return

        try:
            # Get image data from request
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length == 0:
                self._set_headers(400)
                self.wfile.write(b'{"success":false,"error":"No image data"}')
                return

            # Read the uploaded file
            content = self.rfile.read(length)

            # Parse multipart form data to extract image
            boundary = self.headers.get('Content-Type', '').split('boundary=')[-1]
            if boundary:
                # Simple multipart parsing
                parts = content.split(f'--{boundary}'.encode())
                for part in parts:
                    if b'Content-Type: image' in part:
                        # Extract image data
                        image_data = part.split(b'\r\n\r\n', 1)[-1]
                        image_data = image_data.rsplit(b'\r\n', 1)[0]

                        # Save temporarily
                        temp_path = RECEIPTS_DIR / "temp_ocr_image.jpg"
                        with open(temp_path, 'wb') as f:
                            f.write(image_data)

                        # Process with OCR
                        result = extract_receipt_data(
                            str(temp_path),
                            engine=OCR_ENGINE,
                            languages=OCR_LANGUAGES
                        )

                        # Clean up temp file
                        temp_path.unlink(missing_ok=True)

                        # Return results
                        self._set_headers(200)
                        self.wfile.write(json.dumps({
                            "success": True,
                            "data": result
                        }).encode('utf-8'))
                        return

            # If we got here, couldn't parse image
            self._set_headers(400)
            self.wfile.write(b'{"success":false,"error":"Could not extract image"}')
            return

        except Exception as e:
            self._set_headers(500)
            error_msg = {"success": False, "error": str(e)}
            self.wfile.write(json.dumps(error_msg).encode('utf-8'))
            return

    # ... rest of existing do_POST code
    if path == "/api/integrity/check":
        # existing code...
```

## Step 4: Add Frontend Support

Create a new file `static/js/ocr.js` with OCR handling code.

See the `static/js/ocr.js` file in the repository for the complete implementation.

## Step 5: Update index.html

Add this to your `templates/index.html`:

### A. Add OCR script

In the `<head>` section or before `</body>`:

```html
<script src="/static/js/ocr.js"></script>
```

### B. Add image upload field

Add this to your receipt form (before or after existing fields):

```html
<div class="form-group">
    <label for="receipt-image" class="form-label">
        Receipt Image (Optional - for OCR)
    </label>
    <input
        type="file"
        id="receipt-image"
        accept="image/*"
        class="form-control"
    >
    <small class="text-muted">
        Upload a receipt image to auto-fill fields with OCR
    </small>
</div>

<!-- OCR Status Display -->
<div id="ocr-status" style="display: none;" class="alert">
    <span id="ocr-status-text"></span>
</div>
```

### C. Initialize OCR on form

Add this JavaScript at the bottom of your HTML or in your existing app.js:

```html
<script>
// Initialize OCR when page loads
document.addEventListener('DOMContentLoaded', function() {
    const imageInput = document.getElementById('receipt-image');

    if (imageInput && window.OCRHandler) {
        imageInput.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;

            // Show processing status
            const statusDiv = document.getElementById('ocr-status');
            const statusText = document.getElementById('ocr-status-text');
            statusDiv.style.display = 'block';
            statusDiv.className = 'alert alert-info';
            statusText.textContent = 'Processing receipt image...';

            try {
                // Process with OCR
                const data = await OCRHandler.processImage(file);

                // Fill form fields
                if (data.shop) {
                    document.getElementById('shop-input').value = data.shop;
                }
                if (data.purchase_date) {
                    document.getElementById('purchase-date-input').value = data.purchase_date;
                }
                if (data.total_amount) {
                    // You can use this for validation or display
                    console.log('Total amount:', data.total_amount);
                }

                // Show success
                statusDiv.className = 'alert alert-success';
                statusText.textContent = 'Receipt processed! Review and edit the extracted information.';

                // Hide after 5 seconds
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 5000);

            } catch (error) {
                statusDiv.className = 'alert alert-danger';
                statusText.textContent = 'OCR failed: ' + error.message;
            }
        });
    }
});
</script>
```

## Step 6: Test the Integration

1. **Start the server:**

   ```bash
   python app.py
   ```

2. **Open in browser:**

   ```
   http://127.0.0.1:5000
   ```

3. **Test OCR:**
   - Click "Choose File" on the receipt image field
   - Select a receipt image
   - Watch as the form fields auto-populate!
   - Edit any incorrect information
   - Save the receipt

## Troubleshooting

### OCR endpoint returns 500 error

- Check that OCR libraries are installed: `pip list | grep -i ocr`
- Check console for error messages: `python app.py`
- Test OCR directly: `python ocr_service.py test.jpg`

### Form fields don't populate

- Open browser console (F12) and check for JavaScript errors
- Verify `ocr.js` is loaded: check Network tab in browser DevTools
- Check that field IDs match (shop-input, purchase-date-input, etc.)

### OCR is slow

- First run downloads models (~500MB for EasyOCR)
- Subsequent runs are much faster
- Consider using Tesseract if EasyOCR is too slow

### Poor accuracy

- Check image quality (see OCR_SETUP.md for tips)
- Try the other OCR engine
- Configure correct languages in app.py

## Advanced: Full app.py Integration

For a complete, ready-to-use version, you can replace your `app.py` with the enhanced version.

The enhanced version includes:

- ✅ OCR endpoint (`/api/ocr/process`)
- ✅ Image upload handling
- ✅ Error handling and logging
- ✅ Fallback when OCR not available
- ✅ Multi-language support

See `app_with_ocr.py` (if provided) or manually integrate the code above.

## Configuration Options

### Customize OCR Engine

In `app.py`, change:

```python
OCR_ENGINE = "easyocr"  # More accurate, auto-downloads models
# OR
OCR_ENGINE = "tesseract"  # Lightweight, needs system install
```

### Customize Languages

In `app.py`, change:

```python
# For receipts in Netherlands (English and Dutch)
OCR_LANGUAGES = ['en', 'nl']

# For multilingual receipts (English, Dutch, Greek, Latvian)
OCR_LANGUAGES = ['en', 'nl', 'el', 'lv']

# For Tesseract, use 3-letter codes:
OCR_LANGUAGES = ['eng', 'nld', 'ell', 'lav']
```

## Security Considerations

- Upload size limits are recommended (add in app.py)
- Validate file types (only images)
- Clean up temporary files
- Consider adding rate limiting for OCR endpoint

## Next Steps

Once integrated:

1. **Test with various receipts** - different stores, formats, languages
2. **Fine-tune parsing** - edit `ocr_service.py` to improve extraction
3. **Add preprocessing** - enhance image quality before OCR
4. **Batch processing** - process multiple receipts at once
5. **Mobile support** - use phone camera to capture receipts directly

Enjoy your automated receipt manager! 🎉
