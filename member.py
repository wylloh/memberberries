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


# =============================================================================
# CLAUDE.md Management
# =============================================================================

MEMBERBERRIES_DELIMITER = "<!-- MEMBERBERRIES -->"
MEMBERBERRIES_END = "<!-- END MEMBERBERRIES -->"

CLAUDE_MD_TEMPLATE = '''# {project_name}

<!-- Project-specific instructions for Claude go here -->

---

**DO NOT EDIT BELOW THIS LINE** — This section is automatically managed by Memberberries.

{memberberries_section}
'''

MEMBERBERRIES_SECTION_TEMPLATE = '''<!-- MEMBERBERRIES -->

## Memberberries

Persistent memory across sessions. Write markers in responses—hooks persist them automatically.

### Markers
| Marker | Effect |
|--------|--------|
| `[BERRY #tag] insight` | Adds to Active Berries (knowledge) |
| `[ARCHIVE id]` | Moves berry to archive by primary tag |
| `[RETRIEVE #tag]` | Loads archived berries next session |
| `[AUTOBERRY] state` | Saves checkpoint below (overwrites previous) |

### When to Write
**Berries** (knowledge) — capture when the next Claude would ask the same question:
- Critical files, non-obvious dependencies, user preferences, why something was built a certain way

**Autoberries** (task state) — capture current work to resume later:
- When you see `⏰` prompt or user runs `member save`
- Before complex multi-step work
- Format: `[AUTOBERRY] <goal> | <progress> | <next steps>`

### On Session Start
1. **Checkpoint exists?** → Acknowledge and continue from that state
2. **No checkpoint?** → Starting fresh; read Active Berries for context
3. **No berries?** → First session; capture architecture and conventions now

---

{checkpoint_section}
## Active Berries
{active_berries}

## Archives
{archive_summary}

*Synced: {sync_time}*
<!-- END MEMBERBERRIES -->'''


def format_active_berries(berries: List[Dict]) -> str:
    """Format active berries for CLAUDE.md."""
    if not berries:
        return "*(No active berries)*"

    lines = []
    for b in berries:
        date = b.get('created', '')[:10]
        tags = ' '.join(f"#{t}" for t in b.get('tags', []))
        summary = b.get('summary', '')[:100]
        lines.append(f"- `{b['id']}` [{date}] {tags}: {summary}")
    return '\n'.join(lines)


def format_archive_summary(summary: Dict[str, int]) -> str:
    """Format archive summary for CLAUDE.md."""
    if not summary:
        return "*(No archives)*"
    return ' · '.join(f"`#{tag}` ({count})" for tag, count in sorted(summary.items()))


def format_checkpoint_section(autoberry: Optional[Dict]) -> str:
    """Format checkpoint section. Prominent, appears before Active Berries."""
    if not autoberry:
        return ""

    timestamp = autoberry.get('timestamp', '')[:16].replace('T', ' ')
    content = autoberry.get('content', '')

    return f'''## 📍 Checkpoint
**[{timestamp}]** {content}

↳ *Continue from here. Write `[AUTOBERRY]` to update.*

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


def sync_claude_md(project_path: Path, query: str = None) -> int:
    """Sync berries to CLAUDE.md. Returns count of active berries."""
    claude_md_path = project_path / "CLAUDE.md"

    # Load data
    active = load_active_berries(project_path)
    autoberry = load_autoberry(project_path)
    archive_summary = get_archive_summary(project_path)
    pending_retrieves = get_pending_retrieves(project_path)

    # Build retrieved berries section
    retrieved_sections = []
    for tag in pending_retrieves:
        retrieved = load_archived_berries(project_path, tag)
        if retrieved:
            retrieved_sections.append(format_retrieved_berries(retrieved, tag))

    # Build memberberries section
    memberberries_section = MEMBERBERRIES_SECTION_TEMPLATE.format(
        checkpoint_section=format_checkpoint_section(autoberry),
        active_berries=format_active_berries(active),
        archive_summary=format_archive_summary(archive_summary),
        sync_time=datetime.now().strftime('%Y-%m-%d %H:%M')
    )

    # Add retrieved berries if any
    if retrieved_sections:
        memberberries_section = memberberries_section.replace(
            "## Session Context",
            '\n'.join(retrieved_sections) + "\n\n## Session Context"
        )

    # Read existing CLAUDE.md or create new
    if claude_md_path.exists():
        content = claude_md_path.read_text()

        # Replace existing memberberries section
        if MEMBERBERRIES_DELIMITER in content:
            before = content.split(MEMBERBERRIES_DELIMITER)[0].rstrip()
            after_parts = content.split(MEMBERBERRIES_END)
            after = after_parts[1].lstrip() if len(after_parts) > 1 else ""
            content = f"{before}\n\n{memberberries_section}"
            if after:
                content += f"\n\n{after}"
        else:
            # Append to existing file
            content = f"{content.rstrip()}\n\n---\n\n{memberberries_section}"
    else:
        # Create new CLAUDE.md
        project_name = project_path.name
        content = CLAUDE_MD_TEMPLATE.format(
            project_name=project_name,
            memberberries_section=memberberries_section
        )

    claude_md_path.write_text(content)
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
            "hooks": [{"type": "command", "command": str(sync_script)}]
        }],
        "Stop": [{
            "hooks": [
                {"type": "command", "command": str(concentrate_script)},
                {"type": "command", "command": str(nudge_script)}
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
