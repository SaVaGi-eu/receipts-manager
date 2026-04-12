---
name: release
description: Orchestrate the full release workflow — bump version, update CHANGELOG from Jira, commit, tag, push, and create a GitHub draft release
---

You are orchestrating a full release of the receipts-manager project. Follow these steps in order, pausing to confirm with the user before any destructive or irreversible action (push, tag, GitHub release).

## Steps

### 1. Confirm version number
Ask the user for the new version number if not already provided (e.g. `2.5.0`). Strip any leading `v` for use in file edits; keep `v` prefix for the git tag.

### 2. Bump version in source files
- `platforms/macos/package.json` — update `"version"` field
- `platforms/macos/package-lock.json` — update the top-level `"version"` field
- `templates/index.html` — update `<span id="appVersion">…</span>`

### 3. Query Jira for resolved tickets
Use the Atlassian MCP to query all RM tickets that have been resolved since the previous release. Use JQL:
```
project = RM AND status = Done ORDER BY issuetype ASC, key ASC
```
Group results by type: Bug, Feature/Story, Task. Format as a markdown changelog section:
```
## [2.5.0] - YYYY-MM-DD
### Features
- RM-NNN: summary
### Bug Fixes
- RM-NNN: summary
### Tasks
- RM-NNN: summary
```

### 4. Update CHANGELOG.md
Prepend the new section to `CHANGELOG.md` (after the header, before the previous version entry).

### 5. Commit version bumps
```
git add platforms/macos/package.json platforms/macos/package-lock.json templates/index.html CHANGELOG.md
git commit -m "chore: release v{VERSION}"
```

### 6. Tag and push
**Confirm with user before running:**
```
git tag v{VERSION}
git push origin main
git push origin v{VERSION}
```

### 7. Create GitHub draft release
Use `gh release create v{VERSION} --draft --title "Release v{VERSION}" --notes "{CHANGELOG_SECTION}"` so the user can review and publish manually.

Confirm the release URL with the user when done.
