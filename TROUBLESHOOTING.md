# TROUBLESHOOTING GUIDE

## Common Issues and Solutions

### Installation Issues

#### "Python 3 is not installed"

**Mac:**

1. Download Python from <https://www.python.org/downloads/>
2. Install the .pkg file
3. Verify: Open Terminal and run `python3 --version`
4. Should show Python 3.8 or higher

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

**Linux (Fedora):**

```bash
sudo dnf install python3 python3-pip
```

**Linux (Arch):**

```bash
sudo pacman -S python python-pip
```

#### "Permission denied" when running scripts

**Mac/Linux:**

```bash
cd receipt_manager
chmod +x run.command run.sh
```

Then try running again.

#### "Address already in use" error

Port 5000 is being used by another application.

**Solution 1 - Stop the other app:**
Find what's using port 5000:

```bash
# Mac/Linux
lsof -i :5000
# Then kill that process
kill -9 <PID>
```

**Solution 2 - Change port:**
Edit `app.py`, find line 685:

```python
app.run(host='127.0.0.1', port=5000, debug=False)
```

Change to:

```python
app.run(host='127.0.0.1', port=5001, debug=False)
```

Then visit <http://127.0.0.1:5001>

#### Virtual environment creation fails

Delete existing venv and retry:

```bash
cd receipt_manager
rm -rf venv
./run.sh  # or double-click run.command
```

#### Dependencies won't install

Upgrade pip first:

```bash
cd receipt_manager
source venv/bin/activate  # Mac/Linux
pip install --upgrade pip
pip install -r requirements.txt
```

---

### File Upload Issues

#### "Invalid file type"

Only these formats are supported:

- PDF (.pdf)
- JPEG (.jpg, .jpeg)
- PNG (.png)

**Solution:** Convert your file to one of these formats first.

#### "File too large"

Maximum file size is 50MB.

**Solution:** Compress the file or split into multiple pages.

**To change limit:** Edit `app.py` line 19:

```python
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
```

#### Upload succeeds but no file appears

Check:

1. File actually saved? Look in `_Receipts/` or brand/project folders
2. Check terminal for errors
3. Verify disk space available

#### "File already exists" error

You're trying to upload a duplicate.

**Solutions:**

- Use different purchase date
- Change shop/documentation name
- Delete the existing item first
- Rename the file before uploading

---

### Data Issues

#### Items disappeared after restart

Check if `data/data.json` exists and is not empty.

**Recovery:**

1. Look in `data/backups/` for recent backup
2. Copy the most recent backup:

   ```bash
   cp data/backups/data_backup_YYYYMMDD_HHMMSS.json data/data.json
   ```

3. Restart the app

#### JSON import fails

**Error: "Invalid JSON structure"**

The JSON file must have this structure:

```json
{
  "receipts": [...],
  "items": [...],
  "next_id": 1
}
```

**Solution:**

- Check the JSON is valid (use jsonlint.com)
- Ensure it has receipts and items arrays
- Don't manually edit unless you know the structure

#### Data corrupted after crash

Restore from backup:

```bash
cd receipt_manager/data
ls -lt backups/  # List backups, newest first
cp backups/data_backup_YYYYMMDD_HHMMSS.json data.json
```

---

### File Integrity Issues

#### Red banner showing missing files

Files were moved, renamed, or deleted outside the app.

**Solutions:**

**Option 1 - Restore files:**
Find and move files back to their original paths listed in the banner.

**Option 2 - Delete affected items:**

1. Note the IDs with 🔴 indicators
2. Delete those items (this removes the references)
3. Re-upload the receipts if you have them

**Option 3 - Manual JSON edit (advanced):**
Edit `data/data.json` and remove the affected items from the "items" array.

#### Files exist but still marked as missing

**Possible causes:**

- Wrong path in data.json
- File permissions issue
- Case-sensitive filesystem (Mac/Linux)

**Debug:**

1. Open `data/data.json`
2. Find the item with issues
3. Check `receipt_relative_path` value
4. Verify that exact path exists
5. Check file permissions: `ls -l _Receipts/`

---

### Edit/Delete Issues

#### Edit button is disabled (grayed out)

The file is missing. Red 🔴 indicator should be visible.

**Solution:** Fix the missing file issue first (see above).

#### Edit saves but file not renamed

**For multi-item receipts:** Files stay in `_Receipts/` and are not renamed.

**For single-item receipts:** Check terminal for errors. Possible causes:

- Target file already exists
- Permission issue
- Disk full

#### Delete removes item but file remains

This shouldn't happen. Check:

1. Terminal for errors
2. File permissions
3. Disk errors

**Manual cleanup:**

```bash
# Find orphaned files (files not referenced in data.json)
cd receipt_manager
# You'll need to manually compare files with data.json entries
```

---

### Display Issues

#### Dark mode not activating

Check your system settings:

- **Mac:** System Preferences → General → Appearance
- **Linux:** Depends on desktop environment (GNOME, KDE, etc.)

**Force dark mode:** Edit `style.css`, add at top:

```css
:root {
    color-scheme: dark;
}
```

#### Columns not showing

Click **⚙️ Columns** button and enable the hidden columns.

#### Table not displaying correctly

Browser compatibility issue. Update your browser:

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Clear browser cache: Ctrl+Shift+Delete (Cmd+Shift+Delete on Mac)

#### Truncated filenames

This is intentional to prevent filesystem errors. The warning notifies you.

**To see full names:** Hover over filenames (if tooltip added), or check in filesystem.

---

### Search/Filter Issues

#### Search not finding items

Search is case-insensitive but looks for partial matches.

**Check:**

- No typos
- Search looks in: brand, model, location, project, shop, documentation, users
- Doesn't search in: ID, receipt group ID, dates

#### Filters showing "0 items"

Either:

- No items match the criteria
- Filters are too restrictive

**Reset all filters:**

1. Clear search box
2. Set all dropdowns to "All..."
3. Click refresh

---

### Performance Issues

#### App is slow with many items

Expected with 50,000+ items. Performance degrades with very large datasets.

**Solutions:**

- Archive old items (export → delete → import when needed)
- Split into multiple databases by year/project
- Use filters to reduce visible items

#### Startup takes long time

First run installs dependencies (1-2 minutes normal).

Subsequent runs should be fast (<2 seconds).

**If always slow:**

- Check disk speed (HDD vs SSD)
- Check available RAM
- Close other applications

---

### Browser Issues

#### "Cannot connect" or "Unable to load"

Check:

1. App is running (terminal shows "Running on <http://127.0.0.1:5000>")
2. Correct URL: <http://127.0.0.1:5000> (not localhost, not https)
3. No firewall blocking
4. Port 5000 not blocked

#### Dialogs not appearing

JavaScript error. Check browser console:

1. Press F12
2. Click "Console" tab
3. Look for red errors
4. Report issue with error message

#### Buttons not working

Clear browser cache:

- Chrome: Ctrl+Shift+Delete → Clear cached images and files
- Firefox: Ctrl+Shift+Delete → Cached Web Content
- Safari: Cmd+Option+E

---

### Network/Security Issues

#### Firewall blocking Flask

**Mac:**
System Preferences → Security & Privacy → Firewall → Firewall Options
→ Allow Python to accept incoming connections

**Linux:**

```bash
# UFW
sudo ufw allow 5000/tcp

# Firewalld
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```

#### Can't access from other devices

By design! This app is localhost-only for security.

**To enable network access (not recommended):**
Edit `app.py` line 685:

```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

⚠️ **Warning:** This exposes the app to your entire network without authentication.

---

### Data Recovery

#### Lost all data, no backup available

Unfortunately, if both `data.json` and backups are gone, data cannot be recovered.

**Prevention:**

- Regular exports (JSON) to external drive
- Use Time Machine (Mac) or backup tools
- Keep receipts in a separate backup location

#### Backup files are corrupted

Try older backups. They're timestamped:

```bash
ls -lt data/backups/
```

Try each from newest to oldest until you find a working one.

---

## Advanced Debugging

### Enable Flask Debug Mode

**Warning:** Only for development, shows detailed errors.

Edit `app.py` line 685:

```python
app.run(host='127.0.0.1', port=5000, debug=True)
```

### Check Python Errors

Look at terminal output when issue occurs. Errors show:

- File paths involved
- Error type (FileNotFoundError, PermissionError, etc.)
- Line numbers in code

### Verify JSON Integrity

```bash
python3 -m json.tool data/data.json > /dev/null
```

If no output = valid JSON. If error = corrupted.

### Reset to Fresh Install

```bash
cd receipt_manager
rm -rf venv
rm data/data.json
rm -rf data/backups/*
# Then restart
./run.sh  # or run.command
```

⚠️ **Warning:** This deletes all data!

---

## Getting Help

If you've tried everything above and still have issues:

1. **Check terminal output** for error messages
2. **Try on different browser**
3. **Check Python version**: `python3 --version` (need 3.8+)
4. **Verify file permissions**: `ls -la receipt_manager/`
5. **Check disk space**: `df -h`
6. **Review README.md** for missed steps

### Reporting Issues

Include:

- Operating system and version
- Python version: `python3 --version`
- Flask version: `pip show Flask`
- Browser and version
- Exact error message from terminal
- Steps to reproduce the issue

---

## Prevention Tips

✅ **Do:**

- Use Export JSON regularly for backups
- Keep receipts in separate backup location
- Update browser regularly
- Monitor disk space
- Use the app's edit/delete functions

❌ **Don't:**

- Manually move/rename files in filesystem
- Edit `data.json` directly (unless you know what you're doing)
- Delete the backups folder
- Run multiple instances simultaneously
- Use on untrusted networks without authentication

---

**Last Updated:** February 2026
