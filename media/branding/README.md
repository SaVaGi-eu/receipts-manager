# Branding Assets

This directory contains the source branding assets used to build the macOS application.

## Files

| File | Purpose |
|------|---------|
| `icon.png` | Master app icon — 1024×1024 PNG, used as source for all icon sizes |
| `icon.icns` | Compiled macOS icon bundle — used directly by `electron-builder` |
| `background.png` | DMG installer background image — 540×380 px |

## How to regenerate `icon.icns` from `icon.png`

```bash
# From the repo root
mkdir -p /tmp/icon.iconset
sips -z 16 16     media/branding/icon.png --out /tmp/icon.iconset/icon_16x16.png
sips -z 32 32     media/branding/icon.png --out /tmp/icon.iconset/icon_16x16@2x.png
sips -z 32 32     media/branding/icon.png --out /tmp/icon.iconset/icon_32x32.png
sips -z 64 64     media/branding/icon.png --out /tmp/icon.iconset/icon_32x32@2x.png
sips -z 128 128   media/branding/icon.png --out /tmp/icon.iconset/icon_128x128.png
sips -z 256 256   media/branding/icon.png --out /tmp/icon.iconset/icon_128x128@2x.png
sips -z 256 256   media/branding/icon.png --out /tmp/icon.iconset/icon_256x256.png
sips -z 512 512   media/branding/icon.png --out /tmp/icon.iconset/icon_256x256@2x.png
sips -z 512 512   media/branding/icon.png --out /tmp/icon.iconset/icon_512x512.png
sips -z 1024 1024 media/branding/icon.png --out /tmp/icon.iconset/icon_512x512@2x.png
iconutil -c icns /tmp/icon.iconset -o media/branding/icon.icns
```

## Notes

- Binary files (`icon.png`, `icon.icns`, `background.png`) must be added locally with `git add` after copying.
- `release.sh` copies these files into `platforms/macos/build/` automatically before each build.
- Do **not** commit `platforms/macos/build/` — it remains git-ignored as a derived directory.
