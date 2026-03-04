# QUICK START GUIDE

## Installation (First Time Only)

### Mac Users

1. Extract the `receipt_manager` folder to your desired location
2. Navigate to the folder in Finder
3. **Double-click** `run.command`
4. If you see "unidentified developer" warning:
   - Right-click `run.command` → Open
   - Click "Open" in the dialog
5. Wait for setup to complete (1-2 minutes first time)
6. Browser will open automatically, or visit: <http://127.0.0.1:5000>

### Linux Users

1. Extract the `receipt_manager` folder
2. Open Terminal and navigate to the folder:

   ```bash
   cd /path/to/receipt_manager
   ```

3. Make script executable (if needed):

   ```bash
   chmod +x run.sh
   ```

4. Run the application:

   ```bash
   ./run.sh
   ```

5. Open browser to: <http://127.0.0.1:5000>

## Basic Usage

### Add Your First Item

1. **Drag & drop** a receipt file (PDF, JPG, or PNG) onto the green drop zone

2. **Fill receipt information**:
   - Shop: `Coolblue` (or wherever you bought it)
   - Purchase Date: `2026-Feb-15` (format: YYYY-MMM-DD)
   - Documentation: `Invoice` (or Warranty Card, Receipt, etc.)
   - Quantity: `1` (how many items on this receipt)

3. **Fill item information**:
   - Brand: `Apple`
   - Model: `iPhone 15 Pro Max`
   - Location: `Home` (where you store it)
   - Users: Type names and press Enter (e.g., `John`, `Jane`)
   - Project: Leave as `N/A` or enter project name
   - Guarantee Duration: `24` months (or 0 for no warranty)

4. Click **Add Item**

Done! Your item is now tracked with warranty expiration date automatically calculated.

## Finding Items

**Search**: Type in the search box to find by brand, model, shop, etc.

**Filter by Project**: Select from the Projects dropdown

**Filter by Status**:

- Active: Warranties still valid
- Expiring Soon: Within 90 days
- Expired: Past warranty date
- No Guarantee: Items without warranty

**Sort**: Click any column header (ID, Brand, Model, etc.)

## Editing Items

1. Click the **✏️ Edit** button on any row
2. Modify fields
3. Click **Save Changes**

Files are automatically renamed/moved if needed!

## Tips

- **Multi-item receipts**: Set Quantity > 1 to add multiple items from one receipt
- **Project organization**: Use projects to group related items (e.g., "Home Office", "Kitchen Renovation")
- **User tags**: Tag items by who uses them (family members, departments, etc.)
- **Column visibility**: Click ⚙️ Columns to hide fields you don't need
- **Backup regularly**: Use Export JSON to create manual backups

## Stopping the App

Press `Ctrl+C` in the terminal window, or just close the terminal.

## Next Steps

- Read the full README.md for advanced features
- Check data/backups/ folder for automatic backups
- Customize colors in static/css/style.css
- Import/export data to migrate between computers

---

**Questions?** See README.md for detailed documentation and troubleshooting.
