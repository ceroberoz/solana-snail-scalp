# Roadmap to GitHub Sync

Scripts for syncing `roadmap.md` with GitHub Issues and Project Board.

## Files

| File | Description |
|------|-------------|
| `sync_roadmap_to_github.py` | Syncs roadmap.md status to GitHub issues |

## Usage

### 1. Update Status in roadmap.md

Edit `roadmap.md` and change the status emoji for any user story:

```markdown
**US-1.1: Widen RSI Entry Range**
**Status:** 🚧 In Progress   <- Change this!
```

**Status Options:**
| Emoji | Status | GitHub Action |
|-------|--------|---------------|
| 📝 | Todo | Issue stays open |
| 🚧 | In Progress | Issue stays open |
| ✅ | Done | Issue gets closed |
| ⏸️ | Blocked | Issue stays open, adds label |

### 2. Run Sync Script

**Dry run (preview changes):**
```bash
python scripts/sync_roadmap_to_github.py --dry-run
```

**Apply changes:**
```bash
python scripts/sync_roadmap_to_github.py
```

**Options:**
```bash
python scripts/sync_roadmap_to_github.py --help

# Sync different file
python scripts/sync_roadmap_to_github.py --roadmap path/to/roadmap.md

# Sync to different repo
python scripts/sync_roadmap_to_github.py --repo owner/repo-name
```

## Workflow Example

1. Start working on US-1.1:
   - Edit `roadmap.md`: Change `**Status:** 📝 Todo` to `**Status:** 🚧 In Progress`
   - Run sync: `python scripts/sync_roadmap_to_github.py`

2. Complete US-1.1:
   - Edit `roadmap.md`: Change `**Status:** 🚧 In Progress` to `**Status:** ✅ Done`
   - Run sync: `python scripts/sync_roadmap_to_github.py`
   - GitHub issue #1 will be closed automatically

3. Blocked on US-2.3:
   - Edit `roadmap.md`: Change `**Status:** 📝 Todo` to `**Status:** ⏸️ Blocked`
   - Run sync: `python scripts/sync_roadmap_to_github.py`
   - GitHub issue gets "blocked" label

## Integration with GitHub Project Board

The sync script only updates issue **state** (open/closed). To update Project Board fields (Epic, Priority, Sprint, Story Points):

1. Go to your GitHub Project: https://github.com/users/ceroberoz/projects/3
2. Enable the fields on board cards (View options → Fields)
3. Or edit issues directly on the board

## Future Improvements

- [ ] Auto-sync on roadmap.md commit (GitHub Action)
- [ ] Two-way sync (GitHub → roadmap.md)
- [ ] Update Project Board custom fields via API
- [ ] Batch update multiple stories
