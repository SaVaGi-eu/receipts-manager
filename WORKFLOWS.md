# WORKFLOW DIAGRAMS

## User Workflows

### 1. Adding a New Receipt (Single Item)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: Drags receipt.pdf onto drop zone                          │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Validates file (type, size)                             │
│         Shows "Receipt Information" dialog                       │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Fills in:                                                  │
│       • Shop: "Coolblue"                                         │
│       • Purchase Date: "2026-Feb-15"                             │
│       • Documentation: "Invoice"                                 │
│       • Quantity: "1"                                            │
│       Clicks "Next: Item Details"                                │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Shows "Item 1 of 1" dialog                              │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Fills in:                                                  │
│       • Brand: "Apple"                                           │
│       • Model: "iPhone 15 Pro Max"                               │
│       • Location: "Home"                                         │
│       • Users: "John" (press Enter), "Jane" (press Enter)       │
│       • Project: "N/A"                                           │
│       • Guarantee: "24 months"                                   │
│       Clicks "Add Item"                                          │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Processing...                                            │
│         1. Generates receipt_group_id: "RG-0001"                 │
│         2. Determines: Single item (quantity = 1)                │
│         3. Gets directory: Apple/ (project = N/A)                │
│         4. Builds filename:                                      │
│            Apple-iPhone15ProMax-2026Feb15-Coolblue-Home-        │
│            John-Jane-Invoice.pdf                                 │
│         5. Creates Apple/ directory                              │
│         6. Saves file to Apple/[filename]                        │
│         7. Calculates guarantee_end_date: "2028-Feb-28"          │
│         8. Creates receipt entry in data.json                    │
│         9. Creates item entry in data.json                       │
│        10. Creates backup in data/backups/                       │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Sees success message                                       │
│       Table refreshes with new item                              │
│       Row shows: ID 1, RG-0001, Apple, iPhone 15 Pro Max, etc. │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. Adding a New Receipt (Multi-Item)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: Uploads receipt.pdf                                        │
│       Sets Quantity: "3"                                         │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Shows "Item 1 of 3" dialog                              │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Fills item 1 details, clicks "Add Item"                   │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Shows "Item 2 of 3" dialog                              │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Fills item 2 details, clicks "Add Item"                   │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Shows "Item 3 of 3" dialog                              │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Fills item 3 details, clicks "Add Item"                   │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Processing all 3 items...                               │
│         1. Generates receipt_group_id: "RG-0002"                 │
│         2. Determines: Multi-item (quantity > 1)                 │
│         3. Builds filename:                                      │
│            IKEA-2026Feb15-Invoice-RG-0002.pdf                    │
│         4. Saves file to _Receipts/[filename]                    │
│         5. Creates 1 receipt entry                               │
│         6. Creates 3 item entries (all reference RG-0002)        │
│         7. Calculates guarantee dates for each                   │
│         8. Creates backup                                        │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Sees success: "Created 3 items with RG-0002"              │
│       Table shows 3 new rows, all sharing same receipt file     │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3. Editing an Item (Single-Item Receipt)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: Clicks ✏️ Edit button on row (Item ID: 5)                 │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Shows "Edit Item #5" dialog with current values         │
│         Brand: "Samsung"                                         │
│         Project: "N/A"                                           │
│         Current file: Samsung/Samsung-TV-...pdf                  │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Changes:                                                   │
│       • Brand: "Samsung" → "LG"                                  │
│       • Project: "N/A" → "LivingRoom"                            │
│       Clicks "Save Changes"                                      │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Detects changes require file move                       │
│         Old: Samsung/Samsung-TV-...pdf                           │
│         New: LivingRoom/LG-TV-...pdf                             │
│                                                                  │
│         1. Creates LivingRoom/ directory                         │
│         2. Builds new filename: LG-TV-...pdf                     │
│         3. Checks if target exists → No conflict                 │
│         4. Moves file: Samsung/... → LivingRoom/...              │
│         5. Updates data.json with new paths                      │
│         6. Removes Samsung/ if empty                             │
│         7. Creates backup                                        │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Sees "Item updated successfully"                           │
│       Row refreshes with new brand and project                   │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4. Editing an Item (Multi-Item Receipt)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: Edits item from RG-0002 (1 of 3 items)                    │
│       Changes guarantee from 12 to 24 months                     │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Multi-item receipt detected                             │
│         Receipt file stays in _Receipts/ (not moved)            │
│         Only updates item metadata in data.json                  │
│         Recalculates guarantee_end_date                          │
│         Creates backup                                           │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Row updated with new guarantee end date                    │
│       Other 2 items in RG-0002 unchanged                         │
└─────────────────────────────────────────────────────────────────┘
```

---

### 5. Deleting an Item (Last Item in Receipt Group)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: Clicks 🗑️ Delete on Item ID: 7                            │
│       (Only item with receipt_group_id RG-0003)                  │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Shows confirmation dialog                               │
│         "This will also delete the associated file"              │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Clicks "OK"                                                │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Checks items in RG-0003                                 │
│         Finds: 1 item (this is the last one)                     │
│         1. Deletes physical file from disk                       │
│         2. Removes receipt entry (RG-0003) from data.json        │
│         3. Removes item entry from data.json                     │
│         4. Removes empty directory if applicable                 │
│         5. Creates backup                                        │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Row disappears from table                                  │
│       File deleted from filesystem                               │
└─────────────────────────────────────────────────────────────────┘
```

---

### 6. Deleting an Item (Multi-Item Receipt)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: Deletes Item ID: 10 (part of RG-0004 with 3 items)        │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Checks items in RG-0004                                 │
│         Finds: 3 items (not the last one)                        │
│         1. Removes item entry from data.json                     │
│         2. Keeps receipt file (other items still reference it)   │
│         3. Keeps receipt entry (RG-0004 still has 2 items)       │
│         4. Creates backup                                        │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Row disappears                                             │
│       Other 2 items in RG-0004 remain                            │
│       Receipt file still exists in _Receipts/                    │
└─────────────────────────────────────────────────────────────────┘
```

---

### 7. File Integrity Check (Missing File Detected)

```
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Background worker runs (every 30 seconds)               │
│         Checks all receipt_relative_path entries                 │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Finds missing file for Item ID: 15                      │
│         Path: Apple/Apple-Watch-...pdf                           │
│         File doesn't exist                                       │
│                                                                  │
│         1. Adds to integrity_issues array                        │
│         2. Saves to data.json                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND: Polls /api/data                                        │
│           Receives integrity_issues                              │
│                                                                  │
│           1. Shows red banner at top                             │
│           2. Adds 🔴 indicator to row 15                         │
│           3. Applies strike-through to row                       │
│           4. Disables ✏️ Edit button for row 15                  │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Sees banner: "Missing files detected!"                    │
│       Clicks "🔄 Re-check Files Now"                             │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Manual integrity check triggered                        │
│         Re-verifies all files                                    │
│         Updates integrity_issues                                 │
│                                                                  │
│         If file restored: Removes from issues                    │
│         If still missing: Keeps in issues                        │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Banner disappears if no issues                             │
│       Or shows updated list of missing files                     │
└─────────────────────────────────────────────────────────────────┘
```

---

### 8. Search and Filter

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: Types "apple" in search box                                │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Filters items (case-insensitive)                        │
│         Searches in: brand, model, location, project,            │
│                     shop, documentation, users                   │
│         Finds: 5 items containing "apple"                        │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Selects "Expiring Soon" in status filter                  │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Further filters to items:                               │
│         • Containing "apple" AND                                 │
│         • Guarantee ends within 90 days                          │
│         Finds: 2 items                                           │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Clicks "Purchase Date" column header                       │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM: Sorts filtered results by purchase_date ascending       │
│         Shows: 2 items, oldest first, yellow highlighted        │
└─────────────────────┬───────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ USER: Sees narrowed-down results                                 │
│       Status shows: "2 items"                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technical Flows

### Backend: Filename Generation Logic

```
Input: Item + Receipt + Extension

                    ↓

Is this a multi-item receipt? (quantity > 1)

    ├─── YES → Multi-item filename:
    │          Parts: [Shop, PurchaseDate, Documentation, ReceiptGroupID]
    │          Example: IKEA-2026Feb15-Invoice-RG-0001.pdf
    │          Directory: _Receipts/
    │
    └─── NO → Single-item filename:
               Parts: [Brand, Model, PurchaseDate, Shop, Location,
                      Users (first 3), Documentation]
               Example: Apple-iPhone15-2026Feb15-Coolblue-Home-John-Jane-Invoice.pdf

               Project exists and != "N/A"?
                   ├─── YES → Directory: ProjectName/
                   └─── NO → Directory: BrandName/

                    ↓

Sanitize each part:
    • Remove invalid chars: < > : " / \ | ? *
    • Replace spaces with hyphens
    • Limit individual part length
    • Remove consecutive hyphens

                    ↓

Join parts with hyphens
Add extension

                    ↓

Check total length > 200 chars?
    ├─── YES → Truncate proportionally
    │          Set truncation warning flag
    └─── NO → Keep as is

                    ↓

Output: Filename + Directory + Warning Flag
```

---

### Backend: Guarantee End Date Calculation

```
Input: Purchase Date, Duration, Unit

                    ↓

Duration == 0?
    ├─── YES → Return "N/A"
    └─── NO → Continue

                    ↓

Parse purchase date: "2026-Feb-15" → Date object

                    ↓

Unit type?

    ├─── DAYS:
    │    Add duration days to purchase date
    │    Return result
    │
    ├─── MONTHS:
    │    Add duration months (handle year rollover)
    │    Keep same day if valid in target month
    │    Else use last day of target month
    │    Return last day of that month
    │
    └─── YEARS:
         Add duration years
         Keep same month and day if valid (handle Feb 29)
         Return last day of that month

                    ↓

Format as: "YYYY-MMM-DD"

                    ↓

Output: "2028-Feb-28"

Examples:
    2026-Jan-15 + 24 months = 2028-Jan-31 (last day of Jan 2028)
    2024-Feb-29 + 2 years = 2026-Feb-28 (leap year handled)
    2026-Mar-31 + 1 month = 2026-Apr-30 (31st doesn't exist in Apr)
```

---

**End of Workflow Diagrams**
