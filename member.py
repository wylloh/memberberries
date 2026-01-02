#!/usr/bin/env python3
"""
🫐 Memberberries Member Command

Seamless integration with Claude Code.
Syncs relevant memories into CLAUDE.md and launches Claude Code.

Usage:
    member "implement user auth"    # Sync context + launch claude
    member                          # Sync based on project + launch claude
    member --sync-only              # Just sync CLAUDE.md, don't launch
    member --clean                  # Remove memberberries section from CLAUDE.md
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from berry_manager import BerryManager


# Delimiters for the memberberries section in CLAUDE.md
MB_START = "<!-- 🫐 MEMBERBERRIES CONTEXT - Auto-managed, do not edit below this line -->"
MB_END = "<!-- 🫐 END MEMBERBERRIES -->"


class ClaudeMDManager:
    """Manages the CLAUDE.md file with memberberries integration."""

    def __init__(self, project_path: Path, storage_mode: str = 'auto'):
        self.project_path = Path(project_path)
        self.claude_md_path = self.project_path / "CLAUDE.md"
        self.bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

    def ensure_claude_md_exists(self):
        """Create CLAUDE.md if it doesn't exist."""
        if not self.claude_md_path.exists():
            template = self._get_default_template()
            with open(self.claude_md_path, 'w') as f:
                f.write(template)
            print(f"🫐 Created {self.claude_md_path}")
            return True
        return False

    def _get_default_template(self) -> str:
        """Get default CLAUDE.md template."""
        project_name = self.project_path.name
        return f"""# {project_name}

## Project Overview

<!-- Add your project description here -->

## Architecture

<!-- Describe your project's architecture -->

## Conventions

<!-- List coding conventions and standards -->

## Important Notes

<!-- Any other important information for Claude Code -->

---

{MB_START}

*No memberberries context loaded yet. Run `member "your task"` to load relevant context.*

{MB_END}
"""

    def read_claude_md(self) -> tuple[str, str]:
        """Read CLAUDE.md and separate user content from memberberries section.

        Returns:
            tuple: (user_content, memberberries_content)
        """
        if not self.claude_md_path.exists():
            return "", ""

        with open(self.claude_md_path, 'r') as f:
            content = f.read()

        # Find memberberries section
        start_idx = content.find(MB_START)
        end_idx = content.find(MB_END)

        if start_idx == -1:
            # No memberberries section, all is user content
            return content.rstrip(), ""

        # Extract user content (everything before the delimiter)
        user_content = content[:start_idx].rstrip()

        # Extract memberberries content
        if end_idx != -1:
            mb_content = content[start_idx + len(MB_START):end_idx].strip()
        else:
            mb_content = content[start_idx + len(MB_START):].strip()

        return user_content, mb_content

    def generate_memberberries_section(self, task: str = None, max_tokens: int = 2000) -> str:
        """Generate the memberberries section for CLAUDE.md.

        Args:
            task: Optional task description to focus context
            max_tokens: Approximate max tokens for the section (rough estimate)

        Returns:
            Formatted memberberries section content
        """
        sections = []

        # Get task description for search, or use generic
        query = task or "general development context"

        # Header with timestamp
        sections.append(f"\n*Context loaded: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        if task:
            sections.append(f"*Task: {task}*\n")

        # Get preferences
        prefs = self.bm.get_preferences(query, top_k=3)
        if prefs:
            sections.append("\n## Your Preferences")
            for pref in prefs:
                sections.append(f"- **{pref['category']}**: {pref['content']}")

        # Get relevant solutions
        solutions = self.bm.search_solutions(query, top_k=2)
        if solutions:
            sections.append("\n## Relevant Solutions")
            for sol in solutions:
                sections.append(f"- **{sol['problem']}**: {sol['solution']}")

        # Get error patterns
        errors = self.bm.search_errors(query, top_k=2)
        if errors:
            sections.append("\n## Known Error Patterns")
            for err in errors:
                msg = err['error_message'][:100] + "..." if len(err['error_message']) > 100 else err['error_message']
                sections.append(f"- **{msg}**: {err['resolution']}")

        # Get antipatterns
        antipatterns = self.bm.search_antipatterns(query, top_k=2)
        if antipatterns:
            sections.append("\n## Antipatterns (Avoid These)")
            for ap in antipatterns:
                sections.append(f"- **Don't**: {ap['pattern']}")
                sections.append(f"  - *Why*: {ap['reason']}")
                sections.append(f"  - *Instead*: {ap['alternative']}")

        # Get git conventions
        git_convs = self.bm.search_git_conventions(query, top_k=2)
        if git_convs:
            sections.append("\n## Git Conventions")
            for conv in git_convs:
                sections.append(f"- **{conv['convention_type']}**: {conv['pattern']}")
                sections.append(f"  - *Example*: `{conv['example']}`")

        # Get testing patterns
        testing = self.bm.search_testing_patterns(query, top_k=2)
        if testing:
            sections.append("\n## Testing Patterns")
            for tp in testing:
                sections.append(f"- **{tp['strategy']} ({tp['framework']})**: {tp['pattern']}")

        # Get API notes
        api_notes = self.bm.search_api_notes(query, top_k=2)
        if api_notes:
            sections.append("\n## API Notes")
            for note in api_notes:
                sections.append(f"- **{note['service_name']}**: {note['notes']}")

        # Get project context if available
        project_ctx = self.bm.get_project_context(str(self.project_path))
        if project_ctx:
            sections.append("\n## Project Context (from Memberberries)")
            if project_ctx.get('description'):
                sections.append(f"- **Description**: {project_ctx['description']}")
            if project_ctx.get('tech_stack'):
                sections.append(f"- **Tech Stack**: {', '.join(project_ctx['tech_stack'])}")

        # If no content was generated, add a note
        if len(sections) <= 2:  # Only header lines
            sections.append("\n*No relevant memberberries found for this context.*")
            sections.append("*Use `memberberries.py concentrate-*` commands to build your memory.*")

        return "\n".join(sections)

    def sync_claude_md(self, task: str = None) -> bool:
        """Sync CLAUDE.md with fresh memberberries context.

        Args:
            task: Optional task description to focus context

        Returns:
            True if sync was successful
        """
        # Ensure file exists
        created = self.ensure_claude_md_exists()

        # Read existing content
        user_content, _ = self.read_claude_md()

        # Generate new memberberries section
        mb_section = self.generate_memberberries_section(task)

        # Combine and write
        # Only add separator if user content doesn't already end with one
        separator = "" if user_content.rstrip().endswith("---") else "\n\n---"
        new_content = f"""{user_content}{separator}

{MB_START}
{mb_section}
{MB_END}
"""

        with open(self.claude_md_path, 'w') as f:
            f.write(new_content)

        if not created:
            print(f"🫐 Synced memberberries to {self.claude_md_path}")

        return True

    def clean_memberberries_section(self) -> bool:
        """Remove the memberberries section from CLAUDE.md.

        Returns:
            True if cleaning was successful
        """
        if not self.claude_md_path.exists():
            print("No CLAUDE.md found")
            return False

        user_content, _ = self.read_claude_md()

        # Write back just user content
        with open(self.claude_md_path, 'w') as f:
            f.write(user_content.rstrip() + "\n")

        print(f"🫐 Cleaned memberberries section from {self.claude_md_path}")
        return True


def launch_claude():
    """Launch Claude Code, replacing the current process."""
    try:
        # Use os.execvp to replace current process with claude
        os.execvp("claude", ["claude"])
    except FileNotFoundError:
        print("❌ Error: 'claude' command not found")
        print("   Make sure Claude Code is installed and in your PATH")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='🫐 Memberberries - Seamless Claude Code Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  member "implement user auth"    # Sync context for task + launch claude
  member                          # Sync with general context + launch claude
  member --sync-only              # Just sync CLAUDE.md, don't launch
  member --clean                  # Remove memberberries section
  member --status                 # Show current memberberries status

The 'member' command:
1. Ensures CLAUDE.md exists in your project
2. Injects relevant memberberries context
3. Launches Claude Code

Your existing CLAUDE.md content is preserved - memberberries only manages
the section between the special delimiters.
        """
    )

    parser.add_argument('task', nargs='?', default=None,
                        help='Task description to focus context (optional)')
    parser.add_argument('--sync-only', action='store_true',
                        help='Only sync CLAUDE.md, do not launch Claude Code')
    parser.add_argument('--clean', action='store_true',
                        help='Remove memberberries section from CLAUDE.md')
    parser.add_argument('--status', action='store_true',
                        help='Show memberberries status for this project')
    parser.add_argument('--project', '-p', type=str, default=None,
                        help='Project path (default: current directory)')
    parser.add_argument('--global', dest='global_storage', action='store_true',
                        help='Use global memberberries storage')
    parser.add_argument('--local', dest='local_storage', action='store_true',
                        help='Use per-project memberberries storage')

    args = parser.parse_args()

    # Determine project path
    project_path = Path(args.project) if args.project else Path.cwd()

    # Determine storage mode
    storage_mode = 'auto'
    if args.global_storage:
        storage_mode = 'global'
    elif args.local_storage:
        storage_mode = 'local'

    # Initialize manager
    manager = ClaudeMDManager(project_path, storage_mode)

    # Handle different modes
    if args.clean:
        manager.clean_memberberries_section()
        return

    if args.status:
        print(f"\n🫐 Memberberries Status")
        print(f"   Project: {project_path}")
        print(f"   Storage: {manager.bm.base_path}")
        print(f"   CLAUDE.md: {'exists' if manager.claude_md_path.exists() else 'not found'}")
        stats = manager.bm.get_stats()
        print(f"\n   Memories:")
        for key, count in stats.items():
            if count > 0:
                print(f"     - {key}: {count}")
        print()
        return

    # Sync CLAUDE.md
    print(f"\n🫐 Syncing memberberries for: {project_path.name}")
    if args.task:
        print(f"   Task: {args.task}")

    manager.sync_claude_md(args.task)

    # Launch Claude Code unless sync-only
    if not args.sync_only:
        print(f"\n🚀 Launching Claude Code...\n")
        launch_claude()
    else:
        print(f"\n✓ CLAUDE.md synced. Run 'claude' to start your session.\n")


if __name__ == '__main__':
    main()
