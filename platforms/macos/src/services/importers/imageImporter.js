const fs = require('fs');
const path = require('path');
const BaseImporter = require('./BaseImporter');

const SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];

class ImageImporter extends BaseImporter {
  canHandle(filename, mimeType) {
    return (
      SUPPORTED_EXTENSIONS.includes(path.extname(filename).toLowerCase()) ||
      (typeof mimeType === 'string' && mimeType.startsWith('image/'))
    );
  }

  getDisplayName() {
    return 'Image Receipt';
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

module.exports = new ImageImporter();
