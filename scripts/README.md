# Scripts

Utility scripts for the Solana Snail Scalp Bot project.

## Files

| File | Description |
|------|-------------|
| `sync_roadmap_to_github.py` | Syncs roadmap.md status to GitHub issues (open/close) |

## Roadmap Sync

Syncs `roadmap.md` status emojis with GitHub issue states.

### Usage

**Dry run (preview changes):**
```bash
python scripts/sync_roadmap_to_github.py --dry-run
```

**Apply changes:**
```bash
python scripts/sync_roadmap_to_github.py
```

### Status Mapping

| Emoji | Status | GitHub Action |
|-------|--------|---------------|
| 📝 | Todo | Issue stays open |
| 🚧 | In Progress | Issue stays open |
| ✅ | Done | Issue gets closed |
| ⏸️ | Blocked | Issue stays open, adds label |

## GitHub Project Automation

Project fields (Epic, Priority, Story Points, Sprint) are automatically synced via GitHub Actions:

- **Auto-sync**: `.github/workflows/sync-issue-to-project.yml` - triggers on issue edits
- **Manual sync**: `.github/workflows/sync-all-issues.yml` - bulk update all issues

### Running Manual Sync

Go to **Actions** → **Sync All Issues to Project (Manual)** → **Run workflow**

Or via CLI:
```bash
gh workflow run sync-all-issues.yml
```

### How It Works

The workflows parse issue descriptions for these fields:

```markdown
**Epic:** Entry Strategy
**Priority:** 🔴 Critical
**Story Points:** 5
**Sprint:** Sprint 1-2
```

And automatically update the GitHub Project fields using GraphQL API.
