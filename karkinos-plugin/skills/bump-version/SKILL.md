---
name: bump-version
description: Bump the version number in pyproject.toml, plugin.json, and marketplace.json, then commit and tag.
allowed-tools: Bash, Read, Edit, Grep
---

# Bump Version Skill

Bump the Karkinos version across all manifest files.

## Usage

```
/karkinos:bump-version <version>
```

## Examples

```
/karkinos:bump-version 0.3.0
/karkinos:bump-version 1.0.0
```

## Instructions

When the user invokes `/karkinos:bump-version`, follow these steps:

### 1. Validate Version Format

Ensure the version follows semantic versioning (X.Y.Z):

```bash
echo "$VERSION" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' || echo "INVALID"
```

### 2. Find and Update Version Files

Update version in these files:

1. **pyproject.toml** - CLI tool version
   ```
   version = "X.Y.Z"
   ```

2. **karkinos-plugin/.claude-plugin/plugin.json** - Plugin manifest
   ```json
   "version": "X.Y.Z"
   ```

3. **.claude-plugin/marketplace.json** - Marketplace metadata and plugin listing
   ```json
   "version": "X.Y.Z"  (both metadata and plugins[0])
   ```

### 3. Show Changes

Display the diff before committing:

```bash
git diff
```

### 4. Commit and Tag

```bash
git add pyproject.toml karkinos-plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump version to $VERSION"
git tag "v$VERSION"
```

### 5. Offer to Push

Ask the user if they want to push:

```bash
git push origin main --tags
```

## Notes

- Always use semantic versioning (MAJOR.MINOR.PATCH)
- The tag format is `v0.2.0` (with `v` prefix)
- All 3 files must be updated together to stay in sync
- Consider updating CHANGELOG.md if it exists
