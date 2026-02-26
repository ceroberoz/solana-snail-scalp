#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync roadmap.md to GitHub Issues/Project Board

Reads user story status from roadmap.md and updates GitHub issues accordingly.

Usage:
    python scripts/sync_roadmap_to_github.py [--dry-run]

Status Mapping:
    Todo     -> Open issue, Status: Todo
    In Progress -> Open issue, Status: In Progress
    Done     -> Close issue, Status: Done
    Blocked  -> Open issue, add 'blocked' label
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class UserStory:
    id: str
    title: str
    status: str
    epic: str
    story_points: int
    priority: str
    sprint: str
    body: str


# Status emoji to GitHub status mapping
STATUS_MAP = {
    "📝": "Todo",
    "🚧": "In Progress", 
    "✅": "Done",
    "⏸️": "Blocked",
}

# GitHub issue state mapping
STATE_MAP = {
    "📝": "open",
    "🚧": "open",
    "✅": "closed",
    "⏸️": "open",
}


def run_gh_command(args: list[str]) -> tuple[int, str, str]:
    """Run a GitHub CLI command and return (returncode, stdout, stderr)."""
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def parse_roadmap(filepath: Path) -> list[UserStory]:
    """Parse roadmap.md and extract user stories with their status."""
    content = filepath.read_text(encoding="utf-8")
    stories = []
    
    # Find all user stories
    story_blocks = re.finditer(
        r'\*\*US-(\d+\.\d+):\s+([^\n]+?)\*\*\s*\n\*\*Status:\*\*\s*([📝🚧✅⏸️])',
        content
    )
    
    for match in story_blocks:
        story_id = f"US-{match.group(1)}"
        title = match.group(2).strip()
        status_emoji = match.group(3)
        
        # Determine epic from nearby context
        epic = _determine_epic(content, match.start())
        priority = _determine_priority(title, content, match.start())
        sprint = _determine_sprint(story_id, content)
        story_points = _extract_story_points(content, match.start(), match.end())
        
        # Build the user story body
        body = _extract_story_body(content, match.end())
        
        stories.append(UserStory(
            id=story_id,
            title=title,
            status=STATUS_MAP.get(status_emoji, "Todo"),
            epic=epic,
            story_points=story_points,
            priority=priority,
            sprint=sprint,
            body=body
        ))
    
    return stories


def _determine_epic(content: str, position: int) -> str:
    """Determine which epic a user story belongs to based on document position."""
    # Epic headers and their names
    epic_sections = [
        ("### Epic 1: Entry Strategy Optimization", "Entry Strategy"),
        ("### Epic 2: Exit Strategy Enhancement", "Exit Strategy"),
        ("### Epic 3: Risk Management 2.0", "Risk Management"),
        ("### Epic 4: Data & Intelligence", "Data Intelligence"),
        ("### Epic 5: Live Trading Infrastructure", "Live Trading"),
    ]
    
    # Find which epic section this story falls under
    current_epic = "Unknown"
    for header, epic_name in epic_sections:
        header_pos = content.find(header)
        if header_pos != -1 and header_pos < position:
            current_epic = epic_name
    
    return current_epic


def _determine_priority(title: str, content: str, position: int) -> str:
    """Extract priority from context."""
    # Look for priority indicators in nearby text
    nearby_text = content[max(0, position-500):position+200]
    
    # Check for epic-level priority
    epic_priority_match = re.search(r'\*\*Priority:\*\*\s*([🔴🟠🟡🟢🔵])', nearby_text[:500])
    if epic_priority_match:
        emoji = epic_priority_match.group(1)
        priority_map = {
            "🔴": "🔴 Critical",
            "🟠": "🟠 High", 
            "🟡": "🟡 Medium",
            "🟢": "🟢 Low",
            "🔵": "🔵 Nice to Have",
        }
        return priority_map.get(emoji, "🟡 Medium")
    
    return "🟡 Medium"  # Default


def _determine_sprint(story_id: str, content: str) -> str:
    """Determine sprint from sprint planning tables."""
    # Look for the story ID in sprint tables
    sprint_patterns = [
        (r'Sprint 1-2.*?\|\s*' + re.escape(story_id), "Sprint 1-2"),
        (r'Sprint 3-4.*?\|\s*' + re.escape(story_id), "Sprint 3-4"),
        (r'Sprint 5-6.*?\|\s*' + re.escape(story_id), "Sprint 5-6"),
        (r'Sprint 7-10.*?\|\s*' + re.escape(story_id), "Sprint 7-10"),
    ]
    
    for pattern, sprint_name in sprint_patterns:
        if re.search(pattern, content, re.DOTALL):
            return sprint_name
    
    return "Backlog"


def _extract_story_points(content: str, start: int, end: int) -> int:
    """Extract story points from the story block."""
    story_text = content[start:end+500]
    match = re.search(r'Story\s+Points:\s*(\d+)', story_text)
    return int(match.group(1)) if match else 0


def _extract_story_body(content: str, position: int) -> str:
    """Extract the full story body from the code block."""
    block_start = content.find('```', position)
    if block_start == -1:
        return ""
    
    block_end = content.find('```', block_start + 3)
    if block_end == -1:
        return ""
    
    return content[block_start+3:block_end].strip()


def get_github_issues(repo: str) -> dict[str, dict]:
    """Get all existing GitHub issues mapped by title."""
    returncode, stdout, stderr = run_gh_command([
        "issue", "list", "--repo", repo, 
        "--state", "all",
        "--limit", "100",
        "--json", "number,title,state,body"
    ])
    
    if returncode != 0:
        print(f"Error fetching issues: {stderr}")
        return {}
    
    issues = json.loads(stdout)
    # Map by story ID (US-X.X) extracted from title
    issue_map = {}
    for issue in issues:
        match = re.search(r'US-(\d+\.\d+)', issue['title'])
        if match:
            story_id = f"US-{match.group(1)}"
            issue_map[story_id] = issue
    
    return issue_map


def update_issue_status(repo: str, issue_number: int, status: str, current_state: str, dry_run: bool = False) -> bool:
    """Update an issue's status (state and project board)."""
    target_state = "closed" if status == "Done" else "open"
    
    if current_state == target_state:
        return True  # No change needed
    
    if dry_run:
        action = "close" if target_state == "closed" else "reopen"
        print(f"  [DRY-RUN] Would {action} issue #{issue_number} (status: {status})")
        return True
    
    # Use gh issue close or reopen command
    if target_state == "closed":
        cmd = ["issue", "close", str(issue_number), "--repo", repo]
    else:
        cmd = ["issue", "reopen", str(issue_number), "--repo", repo]
    
    returncode, stdout, stderr = run_gh_command(cmd)
    
    if returncode != 0:
        print(f"  [FAIL] Failed to update issue #{issue_number}: {stderr}")
        return False
    
    action = "closed" if target_state == "closed" else "reopened"
    print(f"  [OK] {action.capitalize()} issue #{issue_number} (status: {status})")
    return True


def sync_to_github(stories: list[UserStory], repo: str, dry_run: bool = False) -> bool:
    """Sync user stories to GitHub issues."""
    print(f"\nFetching existing issues from {repo}...")
    existing_issues = get_github_issues(repo)
    print(f"   Found {len(existing_issues)} existing issues")
    
    print(f"\nSyncing {len(stories)} user stories...")
    
    synced = 0
    created = 0
    skipped = 0
    
    for story in stories:
        print(f"\n{story.id}: {story.title}")
        print(f"   Status: {story.status} | Epic: {story.epic} | Sprint: {story.sprint}")
        
        if story.id in existing_issues:
            issue = existing_issues[story.id]
            current_state = issue['state']
            target_state = "closed" if story.status == "Done" else "open"
            
            if current_state != target_state:
                if update_issue_status(repo, issue['number'], story.status, current_state, dry_run):
                    synced += 1
            else:
                print(f"   [OK] Already up to date ({current_state})")
                skipped += 1
        else:
            if dry_run:
                print(f"   [DRY-RUN] Would create new issue")
            else:
                print(f"   [WARN] Issue not found - would need to create")
            skipped += 1
    
    print(f"\nSummary:")
    print(f"   Updated: {synced}")
    print(f"   Created: {created}")
    print(f"   Skipped: {skipped}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Sync roadmap.md to GitHub Issues"
    )
    parser.add_argument(
        "--roadmap", 
        type=Path, 
        default=Path("roadmap.md"),
        help="Path to roadmap.md (default: roadmap.md)"
    )
    parser.add_argument(
        "--repo",
        default="ceroberoz/solana-snail-scalp",
        help="GitHub repository (default: ceroberoz/solana-snail-scalp)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    
    args = parser.parse_args()
    
    if not args.roadmap.exists():
        print(f"[FAIL] Roadmap file not found: {args.roadmap}")
        sys.exit(1)
    
    print(f"Reading roadmap from: {args.roadmap}")
    stories = parse_roadmap(args.roadmap)
    print(f"   Found {len(stories)} user stories")
    
    if not stories:
        print("[FAIL] No user stories found in roadmap")
        sys.exit(1)
    
    # Show parsed stories
    print("\nParsed User Stories:")
    for story in stories:
        print(f"   {story.id}: {story.status:<15} | {story.title[:50]}...")
    
    success = sync_to_github(stories, args.repo, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
