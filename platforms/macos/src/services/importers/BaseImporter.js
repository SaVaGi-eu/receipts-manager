/**
 * BaseImporter — the contract every importer must fulfil.
 *
 * To add a new format, extend this class, implement all methods, and register
 * the instance in index.js.
 */
class BaseImporter {
  /** Return true if this importer can handle the given file. */
  canHandle(filename, mimeType) {   // eslint-disable-line no-unused-vars
    throw new Error(`${this.constructor.name} must implement canHandle()`);
  }

  /** Human-readable label shown in the UI (e.g. "PDF Receipt"). */
  getDisplayName() {
    throw new Error(`${this.constructor.name} must implement getDisplayName()`);
  }

  /** List of file extensions this importer accepts (e.g. ['.pdf']). */
  getSupportedExtensions() {
    return [];
  }

  /**
   * Read the file at filePath and return an import payload.
   *
   * @param {string} filePath  Absolute path to the file on disk.
   * @returns {Promise<{ filename: string, fileBuffer: Buffer, metadata: object }>}
   */
  async import(filePath) {   // eslint-disable-line no-unused-vars
    throw new Error(`${this.constructor.name} must implement import()`);
  }
}

module.exports = BaseImporter;
