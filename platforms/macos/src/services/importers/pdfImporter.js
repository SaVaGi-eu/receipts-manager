const fs = require('fs');
const path = require('path');
const BaseImporter = require('./BaseImporter');

class PdfImporter extends BaseImporter {
  canHandle(filename, mimeType) {
    return (
      path.extname(filename).toLowerCase() === '.pdf' ||
      mimeType === 'application/pdf'
    );
  }

  getDisplayName() {
    return 'PDF Receipt';
  }

  getSupportedExtensions() {
    return ['.pdf'];
  }

  async import(filePath) {
    const filename = path.basename(filePath);
    const fileBuffer = fs.readFileSync(filePath);
    return { filename, fileBuffer, metadata: {} };
  }
}

module.exports = new PdfImporter();
