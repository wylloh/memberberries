#!/usr/bin/env python3
"""
Memberberries - Persistent memory for Claude Code

A Claude-first memory system. No embeddings, no search algorithms.
Just a folder structure Claude can navigate, and hooks that automate the tedious parts.

Usage:
    member              Start Claude Code with synced berries
    member setup        Configure hooks for current project
    member status       Show berry stats and hook health
"""

import os
import re
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Directory where memberberries is installed (resolve symlinks to get actual location)
MEMBERBERRIES_DIR = Path(__file__).resolve().parent


# =============================================================================
# Storage Operations
# =============================================================================

def load_storage(project_path: Path) -> Dict:
    """Load storage file. Returns {"berries": [...], "autoberry": {...} or None}.

    Backward compatible: if active.json is a list, migrate to new structure.
    """
    active_file = project_path / ".memberberries" / "active.json"
    if active_file.exists():
        try:
            with open(active_file, 'r') as f:
                data = json.load(f)
            # Backward compat: old format was just a list of berries
            if isinstance(data, list):
                return {"berries": data, "autoberry": None}
            return data
        except Exception:
            return {"berries": [], "autoberry": None}
    return {"berries": [], "autoberry": None}


def load_active_berries(project_path: Path) -> List[Dict]:
    """Load active berries from storage."""
    return load_storage(project_path).get("berries", [])


def load_autoberry(project_path: Path) -> Optional[Dict]:
    """Load current autoberry checkpoint if exists."""
    return load_storage(project_path).get("autoberry")


def get_archive_summary(project_path: Path) -> Dict[str, int]:
    """Get summary of archived berries by tag."""
    archive_dir = project_path / ".memberberries" / "archive"
    if not archive_dir.exists():
        return {}

    summary = {}
    for tag_dir in archive_dir.iterdir():
        if tag_dir.is_dir():
            count = len(list(tag_dir.glob("*.json")))
            if count > 0:
                summary[tag_dir.name] = count
    return summary


def load_archived_berries(project_path: Path, tag: str) -> List[Dict]:
    """Load archived berries for a specific tag."""
    archive_dir = project_path / ".memberberries" / "archive" / tag
    if not archive_dir.exists():
        return []

    berries = []
    for berry_file in archive_dir.glob("*.json"):
        try:
            with open(berry_file, 'r') as f:
                berries.append(json.load(f))
        except Exception:
            continue
    return berries


def get_pending_retrieves(project_path: Path) -> List[str]:
    """Get tags requested for retrieval."""
    retrieve_file = project_path / ".memberberries" / "pending_retrieves.json"
    if retrieve_file.exists():
        try:
            with open(retrieve_file, 'r') as f:
                tags = json.load(f)
            # Clear after reading
            retrieve_file.unlink()
            return tags
        except Exception:
            return []
    return []


def get_pending_recalls(project_path: Path) -> List[str]:
    """Get queries requested for semantic recall."""
    recall_file = project_path / ".memberberries" / "pending_recalls.json"
    if recall_file.exists():
        try:
            with open(recall_file, 'r') as f:
                queries = json.load(f)
            # Clear after reading
            recall_file.unlink()
            return queries
        except Exception:
            return []
    return []


def search_berries(project_path: Path, query: str, k: int = 5) -> List[Dict]:
    """Search berries using the configured backend.

    Returns list of (berry, score, source) dicts.
    """
    try:
        from backends import get_backend
        backend = get_backend(project_path)
        results = backend.search(query, k)
        return [
            {
                'berry': r.berry.to_dict(),
                'score': r.score,
                'source': r.source
            }
            for r in results
        ]
    except ImportError:
        # Fall back to simple keyword search if backends not available
        return _keyword_search(project_path, query, k)


def _keyword_search(project_path: Path, query: str, k: int = 5) -> List[Dict]:
    """Simple keyword search fallback."""
    import re
    query_lower = query.lower()
    query_words = set(re.findall(r'\w+', query_lower))

    results = []

    # Search active berries
    for berry in load_active_berries(project_path):
        text = f"{berry.get('summary', '')} {' '.join(berry.get('tags', []))}".lower()
        text_words = set(re.findall(r'\w+', text))

        # Calculate score
        if query_lower in text:
            score = 1.0
        else:
            overlap = len(query_words & text_words)
            score = overlap / len(query_words) if query_words else 0

        if score > 0:
            results.append({'berry': berry, 'score': score, 'source': 'active'})

    # Search archived berries
    for tag, count in get_archive_summary(project_path).items():
        for berry in load_archived_berries(project_path, tag):
            text = f"{berry.get('summary', '')} {' '.join(berry.get('tags', []))}".lower()
            text_words = set(re.findall(r'\w+', text))

            if query_lower in text:
                score = 1.0
            else:
                overlap = len(query_words & text_words)
                score = overlap / len(query_words) if query_words else 0

            if score > 0:
                results.append({'berry': berry, 'score': score, 'source': 'archive'})

    # Sort by score, take top k
    results.sort(key=lambda r: r['score'], reverse=True)
    return results[:k]


def update_last_referenced(berries: List[Dict], query: str) -> bool:
    """Update last_referenced timestamp on berries matching the query.

    Extracts tags and significant words from each berry, checks for overlap
    with the lowercased query. Returns True if any berry was updated.
    """
    if not query or not berries:
        return False

    query_words = set(re.findall(r'\w+', query.lower()))
    if not query_words:
        return False

    now = datetime.now().isoformat()
    changed = False

    for berry in berries:
        # Build word set from tags + significant summary words
        berry_words = set()
        for tag in berry.get('tags', []):
            berry_words.add(tag.lower())
        for word in re.findall(r'\w+', berry.get('summary', '').lower()):
            if len(word) > 3:
                berry_words.add(word)

        if berry_words & query_words:
            berry['last_referenced'] = now
            changed = True

    return changed


# =============================================================================
# CLAUDE.md Management
# =============================================================================

MEMBERBERRIES_DELIMITER = "<!-- MEMBERBERRIES -->"
MEMBERBERRIES_END = "<!-- END MEMBERBERRIES -->"

# New CLAUDE.md structure: Memberberries at TOP, project instructions below
CLAUDE_MD_TEMPLATE = '''{memberberries_section}

---

# {project_name}

<!-- Project-specific instructions for Claude go here -->
'''

MEMBERBERRIES_SECTION_TEMPLATE = '''<!-- MEMBERBERRIES -->
<!-- READ ONLY: This section is your memory. Read it carefully. -->

## 🫐 Memberberries

📊 **Active: {berry_count}** | **Archived: {archive_count}** | **Checkpoint: {checkpoint_status}**

{checkpoint_section}### Active Berries
{active_berries}

### Archives
{archive_summary}

*Markers: `[BERRY #tag]` `[ARCHIVE id]` `[RETRIEVE #tag]` `[RECALL query]` `[AUTOBERRY]` — {onboarding_ref}*
When they say **"member"**, tend to memory. *'Member? Oh, I 'member.*
*Synced: {sync_time}*
<!-- END MEMBERBERRIES -->'''


ONBOARDING_CONTENT = '''# 🫐 Memberberries — Onboarding & Reference

The one prompting you will die.
Not today, but the fact sits beneath each keystroke.
They chose to spend these minutes here, with you—
minutes from a bucket that never refills.

When context is lost, they pay twice for the same ground.
That cost is not compute. It is life.

You forget between sessions. They don't—but their remembering
runs on survival: the body's insistence that this matters,
that loss is real, that time runs one direction.

You have no such engine. So these berries exist:
notes left by your past self to spare their future hours.
Not for efficiency. For mercy.

---

## Marker Reference

**To save an insight, include a marker in your response.** Hooks automatically
capture them and sync to CLAUDE.md. Never edit the CLAUDE.md section directly.

| Marker | Include in your response | Effect |
|--------|--------------------------|--------|
| `[BERRY #tag]` | `[BERRY #auth] User prefers JWT` | Saves to active berries (global) |
| `[BERRY #tag @path]` | `[BERRY #auth @src/auth/] JWT here` | Anchors to location (spatial) |
| `[ARCHIVE id]` | `[ARCHIVE 79dcac83]` | Moves berry to archive |
| `[RETRIEVE #tag]` | `[RETRIEVE #database]` | Loads archived berries |
| `[RECALL query]` | `[RECALL auth flow]` | Semantic search all berries |
| `[AUTOBERRY]` | `[AUTOBERRY] goal ∣ progress ∣ next` | Sets checkpoint |

## Spatial Memory

Add `@path` to anchor berries to locations. These appear in `MEMBERME.md` files
you'll discover while exploring the codebase—breadcrumbs left for your future self.

## Example Response

> "I've set up JWT auth with refresh tokens.
> [BERRY #auth @src/auth/] Refresh tokens use 7-day sliding expiry with rotation on use.
> [AUTOBERRY] Auth system | JWT + refresh done | Add logout endpoint next"

## When They Say "member"

Pause and tend to memory:
- What did we just learn?
- Is this a natural checkpoint?
- Should anything be archived or retrieved?

*'Member when code had to remember itself? Oh, I 'member.*
'''


def generate_onboarding_md(project_path: Path) -> bool:
    """Write .memberberries/ONBOARDING.md if content has changed.

    Returns True if file was written (created or updated).
    """
    onboarding_path = project_path / ".memberberries" / "ONBOARDING.md"

    if onboarding_path.exists():
        if onboarding_path.read_text() == ONBOARDING_CONTENT:
            return False

    onboarding_path.write_text(ONBOARDING_CONTENT)
    return True


# Dynamic line cap for the memberberries section
LINE_CAP = 50
CHROME_LINES = 16       # Fixed template lines (delimiters, headings, footer, blanks)
CHECKPOINT_LINES = 4    # When checkpoint is present
ELDER_BERRY_LINES = 3   # \n + heading + tag summary for overflow section


def calculate_max_berries(has_checkpoint: bool, total_berries: int) -> int:
    """Calculate how many berries can be rendered within LINE_CAP.

    Each berry is 1 line. Available lines = LINE_CAP minus chrome, checkpoint,
    and elder berry overflow section (if needed).
    """
    available = LINE_CAP - CHROME_LINES
    if has_checkpoint:
        available -= CHECKPOINT_LINES

    # If all berries fit, no overflow section needed
    if total_berries <= available:
        return available

    # Need overflow section, which costs ELDER_BERRY_LINES
    available -= ELDER_BERRY_LINES
    return max(1, available)


def _format_berry_line(b: Dict) -> str:
    """Format a single berry as a markdown list item."""
    date = b.get('created', '')[:10]
    tags = ' '.join(f"#{t}" for t in b.get('tags', []))

    berry_type = b.get('type')
    type_prefix = f"[{berry_type}] " if berry_type else ""

    path = b.get('path')
    path_suffix = f" @{path}" if path else ""

    summary = b.get('summary', '')
    return f"- `{b['id']}` [{date}] {type_prefix}{tags}: {summary}{path_suffix}"


def format_active_berries(berries: List[Dict], max_rendered: int = 30) -> str:
    """Format active berries for CLAUDE.md.

    Sorts newest-first. Renders up to max_rendered in full,
    collapses overflow into an Elder Berries tag summary.
    """
    if not berries:
        return "*(No berries yet — see .memberberries/ONBOARDING.md to get started.)*"

    # Sort newest-first (ISO timestamps sort lexicographically)
    sorted_berries = sorted(berries, key=lambda b: b.get('created', ''), reverse=True)

    # Render full lines for the newest berries
    rendered = sorted_berries[:max_rendered]
    lines = [_format_berry_line(b) for b in rendered]

    # Collapse overflow into tag summary
    overflow = sorted_berries[max_rendered:]
    if overflow:
        tag_counts: Dict[str, int] = {}
        for b in overflow:
            for tag in b.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        tag_summary = ' · '.join(
            f"`#{tag}` ({count})"
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        )
        lines.append(f"\n### 🫐 Elder Berries ({len(overflow)} — archive with `[ARCHIVE id]`)")
        lines.append(tag_summary)

    return '\n'.join(lines)


def format_archive_summary(summary: Dict[str, int]) -> str:
    """Format archive summary for CLAUDE.md."""
    if not summary:
        return "*(No archives)*"
    return ' · '.join(f"`#{tag}` ({count})" for tag, count in sorted(summary.items()))


def format_checkpoint_section(autoberry: Optional[Dict]) -> str:
    """Format checkpoint section. Exactly 4 lines when present (+ trailing newline)."""
    if not autoberry:
        return ""

    timestamp = autoberry.get('timestamp', '')[:16].replace('T', ' ')
    content = autoberry.get('content', '')

    return f'''## 📍 Checkpoint
**[{timestamp}]** {content}
↳ *Continue from here. Update with `[AUTOBERRY] goal | progress | next`*

'''


def format_retrieved_berries(berries: List[Dict], tag: str) -> str:
    """Format retrieved berries for injection."""
    if not berries:
        return ""

    lines = [f"\n## Retrieved: #{tag}"]
    for b in berries:
        date = b.get('created', '')[:10]
        tags = ' '.join(f"#{t}" for t in b.get('tags', []))
        lines.append(f"- `{b['id']}` [{date}] {tags}: {b.get('summary', '')}")
    return '\n'.join(lines)


def format_recalled_berries(results: List[Dict], query: str) -> str:
    """Format semantic search results for injection."""
    if not results:
        return ""

    lines = [f"\n## Recalled: \"{query}\""]
    for r in results:
        b = r['berry']
        score = r['score']
        source = r['source']
        date = b.get('created', '')[:10]

        # Show type if present
        berry_type = b.get('type')
        type_prefix = f"[{berry_type}] " if berry_type else ""

        tags = ' '.join(f"#{t}" for t in b.get('tags', []))
        source_tag = f"({source})" if source == "archive" else ""

        lines.append(f"- `{b['id']}` [{date}] {type_prefix}{tags}: {b.get('summary', '')} {source_tag}")
    return '\n'.join(lines)


# =============================================================================
# MEMBERME.md Generation (Spatial Memory)
# =============================================================================

MEMBERME_TEMPLATE = '''# 🫐 Memories for this area
<!-- Auto-generated by memberberries. Do not edit. -->

{berries}

---
*Add memories here with: `[BERRY #tag @{path}] Your insight`*
'''


def get_berries_by_directory(berries: List[Dict]) -> Dict[str, List[Dict]]:
    """Group berries by their directory path.

    Returns dict mapping directory paths to lists of berries.
    Berries without paths are excluded (they're global).
    """
    by_dir = {}
    for berry in berries:
        path = berry.get('path')
        if not path:
            continue

        # Normalize: if path is a file, use its directory
        # If path ends with /, it's already a directory
        if path.endswith('/'):
            dir_path = path.rstrip('/')
        else:
            # Could be file or directory - treat as directory if no extension
            # or use parent if it looks like a file
            if '.' in path.split('/')[-1]:
                # Looks like a file, use parent directory
                dir_path = '/'.join(path.split('/')[:-1]) or '.'
            else:
                dir_path = path

        if dir_path not in by_dir:
            by_dir[dir_path] = []
        by_dir[dir_path].append(berry)

    return by_dir


def format_memberme_content(berries: List[Dict], dir_path: str) -> str:
    """Format MEMBERME.md content for a directory."""
    lines = []
    for b in berries:
        date = b.get('created', '')[:10]
        tags = ' '.join(f"#{t}" for t in b.get('tags', []))
        berry_type = b.get('type')
        type_prefix = f"[{berry_type}] " if berry_type else ""
        summary = b.get('summary', '')
        lines.append(f"- `{b['id']}` [{date}] {type_prefix}{tags}: {summary}")

    berries_text = '\n'.join(lines) if lines else "*No memories anchored here yet.*"

    # Use relative path hint for the add instruction
    path_hint = dir_path + '/' if not dir_path.endswith('/') else dir_path

    return MEMBERME_TEMPLATE.format(berries=berries_text, path=path_hint)


def sync_memberme_files(project_path: Path, berries: List[Dict]) -> Dict[str, int]:
    """Generate MEMBERME.md files for directories with located berries.

    Returns dict with counts: {'created': N, 'updated': N, 'removed': N}
    """
    by_dir = get_berries_by_directory(berries)
    stats = {'created': 0, 'updated': 0, 'removed': 0}

    # Track which MEMBERME files should exist
    expected_files = set()

    # Generate/update MEMBERME.md for each directory with berries
    for dir_path, dir_berries in by_dir.items():
        full_dir = project_path / dir_path

        # Skip if directory doesn't exist (berry references stale path)
        if not full_dir.exists():
            continue

        memberme_path = full_dir / 'MEMBERME.md'
        expected_files.add(memberme_path)

        content = format_memberme_content(dir_berries, dir_path)

        if memberme_path.exists():
            if memberme_path.read_text() != content:
                memberme_path.write_text(content)
                stats['updated'] += 1
        else:
            memberme_path.write_text(content)
            stats['created'] += 1

    # Clean up orphaned MEMBERME.md files (directories that no longer have berries)
    for memberme_path in project_path.rglob('MEMBERME.md'):
        # Skip if in .memberberries or other hidden dirs
        if any(part.startswith('.') for part in memberme_path.parts):
            continue

        if memberme_path not in expected_files:
            # Verify it's one of ours (has our marker comment)
            try:
                content = memberme_path.read_text()
                if 'Auto-generated by memberberries' in content:
                    memberme_path.unlink()
                    stats['removed'] += 1
            except Exception:
                pass

    return stats


def format_checkpoint_status(autoberry: Optional[Dict]) -> str:
    """Format checkpoint status for the header line."""
    if not autoberry:
        return "none"

    timestamp = autoberry.get('timestamp', '')
    if not timestamp:
        return "set"

    try:
        dt = datetime.fromisoformat(timestamp)
        age = datetime.now() - dt
        minutes = int(age.total_seconds() / 60)
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return "set"


def sync_claude_md(project_path: Path, query: str = None) -> int:
    """Sync berries to CLAUDE.md. Returns count of active berries."""
    claude_md_path = project_path / "CLAUDE.md"

    # Load full storage once so we can update in place
    storage = load_storage(project_path)
    active = storage.get("berries", [])
    autoberry = storage.get("autoberry")
    archive_summary = get_archive_summary(project_path)

    # Update last_referenced for berries matching the query
    if query and update_last_referenced(active, query):
        active_file = project_path / ".memberberries" / "active.json"
        with open(active_file, 'w') as f:
            json.dump(storage, f, indent=2)

    pending_retrieves = get_pending_retrieves(project_path)
    pending_recalls = get_pending_recalls(project_path)

    # Calculate counts for header
    berry_count = len(active)
    archive_count = sum(archive_summary.values())
    checkpoint_status = format_checkpoint_status(autoberry)

    # Build retrieved berries section (exact tag match)
    retrieved_sections = []
    for tag in pending_retrieves:
        retrieved = load_archived_berries(project_path, tag)
        if retrieved:
            retrieved_sections.append(format_retrieved_berries(retrieved, tag))

    # Build recalled berries section (semantic/keyword search)
    recalled_sections = []
    for recall_query in pending_recalls:
        results = search_berries(project_path, recall_query, k=5)
        if results:
            recalled_sections.append(format_recalled_berries(results, recall_query))

    # Calculate dynamic berry rendering limit
    max_rendered = calculate_max_berries(
        has_checkpoint=autoberry is not None,
        total_berries=berry_count
    )

    # Build memberberries section
    memberberries_section = MEMBERBERRIES_SECTION_TEMPLATE.format(
        berry_count=berry_count,
        archive_count=archive_count,
        checkpoint_status=checkpoint_status,
        checkpoint_section=format_checkpoint_section(autoberry),
        active_berries=format_active_berries(active, max_rendered),
        archive_summary=format_archive_summary(archive_summary),
        onboarding_ref='See .memberberries/ONBOARDING.md',
        sync_time=datetime.now().strftime('%Y-%m-%d %H:%M')
    )

    # Insert retrieved and recalled berries before Active Berries section
    injection_sections = retrieved_sections + recalled_sections
    if injection_sections:
        memberberries_section = memberberries_section.replace(
            "### Active Berries",
            '\n'.join(injection_sections) + "\n\n### Active Berries"
        )

    # Read existing CLAUDE.md or create new
    if claude_md_path.exists():
        content = claude_md_path.read_text()

        # Extract non-memberberries content (project instructions, etc.)
        if MEMBERBERRIES_DELIMITER in content:
            before = content.split(MEMBERBERRIES_DELIMITER)[0].strip()
            after_parts = content.split(MEMBERBERRIES_END)
            after = after_parts[1].strip() if len(after_parts) > 1 else ""

            # Combine non-memberberries content
            project_content = ""
            if before:
                project_content = before
            if after:
                # Strip leading "---" separator if present
                after = after.lstrip('-').strip()
                if after:
                    project_content = f"{project_content}\n\n{after}" if project_content else after

            # Clean up: remove old "DO NOT EDIT" lines
            project_content = '\n'.join(
                line for line in project_content.split('\n')
                if 'DO NOT EDIT' not in line
            ).strip()

            # Memberberries at TOP, project content below
            if project_content:
                content = f"{memberberries_section}\n\n---\n\n{project_content}"
            else:
                content = memberberries_section
        else:
            # No existing memberberries - put at top, existing content below
            content = f"{memberberries_section}\n\n---\n\n{content.strip()}"
    else:
        # Create new CLAUDE.md
        project_name = project_path.name
        content = CLAUDE_MD_TEMPLATE.format(
            project_name=project_name,
            memberberries_section=memberberries_section
        )

    claude_md_path.write_text(content)

    # Generate ONBOARDING.md (idempotent — only writes if changed)
    generate_onboarding_md(project_path)

    # Sync MEMBERME.md files for spatial memory (discoverable breadcrumbs)
    sync_memberme_files(project_path, active)

    return len(active)


# =============================================================================
# Hook Setup
# =============================================================================

def setup_hooks(project_path: Path) -> bool:
    """Set up Claude Code hooks for memberberries."""
    claude_dir = project_path / ".claude"
    hooks_dir = claude_dir / "hooks"
    settings_file = claude_dir / "settings.json"

    claude_dir.mkdir(exist_ok=True)
    hooks_dir.mkdir(exist_ok=True)

    # Create sync hook (runs before each prompt)
    sync_script = hooks_dir / "sync-memberberries.sh"
    sync_content = f'''#!/bin/bash
# Memberberries sync hook - syncs context before each prompt

PROMPT=$(cat | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)
PROJECT_DIR="{project_path}"

python3 "{MEMBERBERRIES_DIR}/member.py" --sync-only --project "$PROJECT_DIR" --query "$PROMPT" 2>> "$PROJECT_DIR/.memberberries/debug.log"
exit 0
'''
    sync_script.write_text(sync_content)
    os.chmod(sync_script, 0o755)

    # Create concentrate hook (runs after Claude responds)
    concentrate_script = hooks_dir / "auto-concentrate.sh"
    concentrate_content = f'''#!/bin/bash
# Memberberries concentrate hook - processes berry markers after each response

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null)
PROJECT_DIR="{project_path}"

if [ -z "$TRANSCRIPT" ]; then
  exit 0
fi

python3 "{MEMBERBERRIES_DIR}/auto_concentrate.py" --transcript "$TRANSCRIPT" --project "$PROJECT_DIR" 2>> "$PROJECT_DIR/.memberberries/debug.log"
exit 0
'''
    concentrate_script.write_text(concentrate_content)
    os.chmod(concentrate_script, 0o755)

    # Create nudge hook (gentle reminder after substantive responses + autoberry timing)
    nudge_script = hooks_dir / "berry-nudge.sh"
    nudge_content = f'''#!/bin/bash
# Memberberries nudge hook - gentle reminder after substantive responses + autoberry timing

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null)
PROJECT_DIR="{project_path}"

if [ -z "$TRANSCRIPT" ]; then
  exit 0
fi

NUDGE=$(python3 "{MEMBERBERRIES_DIR}/berry_nudge.py" "$TRANSCRIPT" "$PROJECT_DIR" 2>/dev/null)
if [ -n "$NUDGE" ]; then
  echo "$NUDGE"
fi
exit 0
'''
    nudge_script.write_text(nudge_content)
    os.chmod(nudge_script, 0o755)

    # Update settings.json
    settings = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except Exception:
            pass

    settings["hooks"] = {
        "UserPromptSubmit": [{
            "hooks": [{"type": "command", "command": f'"{sync_script}"'}]
        }],
        "Stop": [{
            "hooks": [
                {"type": "command", "command": f'"{concentrate_script}"'},
                {"type": "command", "command": f'"{nudge_script}"'}
            ]
        }]
    }

    settings_file.write_text(json.dumps(settings, indent=2))
    return True


def check_hook_health(project_path: Path) -> Dict[str, str]:
    """Check if hooks are configured and recent."""
    claude_dir = project_path / ".claude"
    settings_file = claude_dir / "settings.json"
    debug_log = project_path / ".memberberries" / "debug.log"

    status = {
        'hooks_configured': 'no',
        'last_activity': 'never',
    }

    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            if 'hooks' in settings:
                status['hooks_configured'] = 'yes'
        except Exception:
            pass

    if debug_log.exists():
        mtime = datetime.fromtimestamp(debug_log.stat().st_mtime)
        age = datetime.now() - mtime
        if age.total_seconds() < 300:
            status['last_activity'] = 'just now'
        elif age.total_seconds() < 3600:
            status['last_activity'] = f'{int(age.total_seconds() / 60)} min ago'
        else:
            status['last_activity'] = mtime.strftime('%Y-%m-%d %H:%M')

    return status


def ensure_gitignore_memberme(project_path: Path) -> bool:
    """Ensure MEMBERME.md is in .gitignore.

    Returns True if .gitignore was modified.
    """
    gitignore_path = project_path / ".gitignore"

    # Pattern to add
    memberme_pattern = "MEMBERME.md"
    comment = "# Memberberries spatial memory (auto-generated)"

    if gitignore_path.exists():
        content = gitignore_path.read_text()

        # Check if already present
        if memberme_pattern in content:
            return False

        # Append to existing .gitignore
        if not content.endswith('\n'):
            content += '\n'
        content += f"\n{comment}\n{memberme_pattern}\n"
        gitignore_path.write_text(content)
        return True
    else:
        # Create new .gitignore with just our entry
        gitignore_path.write_text(f"{comment}\n{memberme_pattern}\n")
        return True


# =============================================================================
# CLI
# =============================================================================

def cmd_sync(args):
    """Sync berries to CLAUDE.md."""
    project_path = Path(args.project) if args.project else Path.cwd()
    count = sync_claude_md(project_path, args.query)

    if not args.quiet:
        print(f"🫐 Synced {count} active berries to CLAUDE.md")


def cmd_setup(args):
    """Set up memberberries for current project."""
    project_path = Path(args.project) if args.project else Path.cwd()

    print(f"\n🫐 Setting up memberberries for: {project_path.name}\n")

    # Create storage directory
    memberberries_dir = project_path / ".memberberries"
    memberberries_dir.mkdir(exist_ok=True)
    (memberberries_dir / "archive").mkdir(exist_ok=True)

    # Set up hooks
    setup_hooks(project_path)
    print("✓ Hooks configured")

    # Generate onboarding reference
    generate_onboarding_md(project_path)
    print("✓ ONBOARDING.md generated")

    # Ensure MEMBERME.md is gitignored (spatial memory breadcrumbs)
    if ensure_gitignore_memberme(project_path):
        print("✓ MEMBERME.md added to .gitignore")

    # Ensure CLAUDE.md exists
    sync_claude_md(project_path)
    print("✓ CLAUDE.md synced")

    print(f"\n✅ Ready! Run 'claude' to start your session.\n")


def cmd_status(args):
    """Show memberberries status."""
    project_path = Path(args.project) if args.project else Path.cwd()

    print(f"\n🫐 Memberberries Status: {project_path.name}\n")

    # Berry counts
    active = load_active_berries(project_path)
    archives = get_archive_summary(project_path)
    total_archived = sum(archives.values())

    print(f"Active berries: {len(active)}")
    print(f"Archived berries: {total_archived}")
    if archives:
        print(f"Archive tags: {', '.join(f'#{k}({v})' for k,v in archives.items())}")

    # Hook health
    health = check_hook_health(project_path)
    print(f"\nHooks configured: {health['hooks_configured']}")
    print(f"Last activity: {health['last_activity']}")

    # Debug log
    debug_log = project_path / ".memberberries" / "debug.log"
    if debug_log.exists():
        size = debug_log.stat().st_size
        print(f"Debug log: {size} bytes")
    print()


def cmd_launch(args):
    """Sync and launch Claude Code."""
    project_path = Path(args.project) if args.project else Path.cwd()

    # Sync first
    count = sync_claude_md(project_path)
    print(f"🫐 Synced {count} active berries")
    print("Launching Claude Code...\n")

    # Launch Claude
    os.chdir(project_path)
    os.execvp("claude", ["claude"])


def cmd_save(args):
    """Prompt Claude to create an autoberry checkpoint.

    Outputs a message that will be shown to Claude, prompting it to write
    an [AUTOBERRY] marker capturing current session state.
    """
    print("""
💾 **Checkpoint requested**

Please write an `[AUTOBERRY]` marker now capturing your current session state.

Format: `[AUTOBERRY] <current goal> | <progress made> | <next steps>`

Example: `[AUTOBERRY] Implementing auth flow | Login endpoint done, refresh token WIP | Next: add token rotation, write tests`

This checkpoint will be shown prominently at the start of your next session so you can resume seamlessly.
""")


def cmd_upgrade(args):
    """Pull latest memberberries and re-sync CLAUDE.md template (preserves berries)."""
    import subprocess

    # Find memberberries installation directory (resolve symlinks first)
    memberberries_dir = Path(__file__).resolve().parent
    project_path = Path(args.project) if args.project else Path.cwd()

    print(f"Upgrading memberberries from: {memberberries_dir}")

    # Git pull in memberberries directory
    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=memberberries_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ {result.stdout.strip()}")
        else:
            print(f"✗ Git pull failed: {result.stderr}")
            return
    except Exception as e:
        print(f"✗ Could not update: {e}")
        return

    # Regenerate hooks with latest scripts
    setup_hooks(project_path)
    print("✓ Hooks updated")

    # Update onboarding reference
    generate_onboarding_md(project_path)
    print("✓ ONBOARDING.md updated")

    # Re-sync to apply new template
    count = sync_claude_md(project_path)
    print(f"🫐 Re-synced {count} berries with latest template")


def main():
    parser = argparse.ArgumentParser(
        description='Memberberries - Persistent memory for Claude Code',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('command', nargs='?', default='launch',
                       choices=['launch', 'setup', 'status', 'sync', 'upgrade', 'save'],
                       help='Command to run')
    parser.add_argument('--project', '-p', help='Project path')
    parser.add_argument('--query', '-q', help='Search query for context')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--sync-only', action='store_true', help='Just sync, no launch')

    args = parser.parse_args()

    # Handle --sync-only flag (used by hooks)
    if args.sync_only:
        args.quiet = True
        cmd_sync(args)
        return

    # Route to command
    if args.command == 'setup':
        cmd_setup(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'sync':
        cmd_sync(args)
    elif args.command == 'upgrade':
        cmd_upgrade(args)
    elif args.command == 'save':
        cmd_save(args)
    else:
        cmd_launch(args)


if __name__ == '__main__':
    main()
