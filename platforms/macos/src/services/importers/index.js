/**
 * Importer registry — all registered importers are tried in order.
 *
 * To add a new format:
 *   1. Create MyFormatImporter.js extending BaseImporter
 *   2. Add `require('./myFormatImporter')` to the array below
 */
const importers = [
  require('./pdfImporter'),
  require('./imageImporter'),
  require('./emailImporter'),
];

/**
 * Return the first importer that can handle the given file, or null.
 *
 * @param {string} filename
 * @param {string} [mimeType]
 * @returns {import('./BaseImporter')|null}
 */
function findImporter(filename, mimeType = '') {
  return importers.find(i => i.canHandle(filename, mimeType)) || null;
}

/**
 * Return the flat list of all supported file extensions across every importer.
 *
 * @returns {string[]}
 */
function getSupportedExtensions() {
  return importers.flatMap(i => i.getSupportedExtensions());
}

module.exports = { importers, findImporter, getSupportedExtensions };
