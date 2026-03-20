const fs = require('fs');
const path = require('path');
const BaseImporter = require('./BaseImporter');

const SUPPORTED_EXTENSIONS = ['.eml', '.msg'];

class EmailImporter extends BaseImporter {
  canHandle(filename, mimeType) {
    return (
      SUPPORTED_EXTENSIONS.includes(path.extname(filename).toLowerCase()) ||
      mimeType === 'message/rfc822'
    );
  }

  getDisplayName() {
    return 'Email Receipt';
  }

  getSupportedExtensions() {
    return SUPPORTED_EXTENSIONS;
  }

  async import(filePath) {
    const filename = path.basename(filePath);
    const fileBuffer = fs.readFileSync(filePath);
    return { filename, fileBuffer, metadata: {} };
  }
}

module.exports = new EmailImporter();
