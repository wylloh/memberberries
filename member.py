#!/usr/bin/env python3
"""
Memberberries Member Command

Seamless integration with Claude Code.
Syncs relevant memories into CLAUDE.md and launches Claude Code.

Usage:
    member "implement user auth"    # Sync context + launch claude
    member                          # Sync based on project + launch claude
    member --sync-only              # Just sync CLAUDE.md, don't launch
    member --sync-only --query "prompt"  # Sync with specific query (for hooks)
    member init                     # Interactive project setup wizard
    member setup                    # Full installation wizard
    member --clean                  # Remove memberberries section from CLAUDE.md
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from berry_manager import BerryManager


# Delimiters for the memberberries section in CLAUDE.md
MB_START = "<!-- MEMBERBERRIES CONTEXT - Auto-managed, do not edit below this line -->"
MB_END = "<!-- END MEMBERBERRIES -->"

# Path to memberberries installation
MEMBERBERRIES_DIR = Path(__file__).parent.resolve()


class ProjectDetector:
    """Auto-detect project information from files and structure."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)

    def detect_tech_stack(self) -> list:
        """Detect technologies used in the project."""
        stack = []

        # Python
        if (self.project_path / "requirements.txt").exists() or \
           (self.project_path / "setup.py").exists() or \
           (self.project_path / "pyproject.toml").exists():
            stack.append("Python")
            # Check for frameworks
            for f in ["requirements.txt", "pyproject.toml"]:
                fpath = self.project_path / f
                if fpath.exists():
                    content = fpath.read_text().lower()
                    if "fastapi" in content:
                        stack.append("FastAPI")
                    if "django" in content:
                        stack.append("Django")
                    if "flask" in content:
                        stack.append("Flask")
                    if "pytest" in content:
                        stack.append("pytest")

        # JavaScript/TypeScript
        if (self.project_path / "package.json").exists():
            stack.append("JavaScript/Node.js")
            try:
                pkg = json.loads((self.project_path / "package.json").read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "typescript" in deps:
                    stack.append("TypeScript")
                if "react" in deps:
                    stack.append("React")
                if "vue" in deps:
                    stack.append("Vue.js")
                if "next" in deps:
                    stack.append("Next.js")
                if "express" in deps:
                    stack.append("Express")
                if "jest" in deps:
                    stack.append("Jest")
            except:
                pass

        # Go
        if (self.project_path / "go.mod").exists():
            stack.append("Go")

        # Rust
        if (self.project_path / "Cargo.toml").exists():
            stack.append("Rust")

        # Docker
        if (self.project_path / "Dockerfile").exists() or \
           (self.project_path / "docker-compose.yml").exists() or \
           (self.project_path / "docker-compose.yaml").exists():
            stack.append("Docker")

        # Database indicators
        for f in self.project_path.glob("**/*.sql"):
            stack.append("SQL")
            break

        return list(set(stack))  # Remove duplicates

    def detect_architecture(self) -> str:
        """Suggest architecture based on directory structure."""
        dirs = [d.name for d in self.project_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

        # Microservices indicators
        if any(d in dirs for d in ["services", "microservices"]) or \
           (self.project_path / "docker-compose.yml").exists():
            return "Microservices"

        # Monorepo indicators
        if "packages" in dirs or "apps" in dirs:
            return "Monorepo"

        # Clean architecture indicators
        if all(d in dirs for d in ["domain", "application", "infrastructure"]):
            return "Clean Architecture"

        # MVC indicators
        if all(d in dirs for d in ["models", "views", "controllers"]):
            return "MVC"

        # Standard web app
        if "src" in dirs:
            return "Standard (src-based)"

        return "Unknown"

    def suggest_description(self) -> str:
        """Generate a suggested project description."""
        stack = self.detect_tech_stack()
        arch = self.detect_architecture()
        name = self.project_path.name

        if stack:
            return f"A {arch.lower()} project using {', '.join(stack[:3])}"
        return f"A software project called {name}"


class InteractiveSetup:
    """Interactive setup wizard for CLAUDE.md."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.detector = ProjectDetector(project_path)

    def prompt_user(self, question: str, default: str = None, options: list = None) -> str:
        """Prompt user for input with optional default and options."""
        if options:
            print(f"\n{question}")
            for i, opt in enumerate(options, 1):
                print(f"  [{i}] {opt}")
            print(f"  [s] Skip")
            print(f"  [?] Suggest based on codebase")

            while True:
                choice = input("\nYour choice: ").strip().lower()
                if choice == 's' or choice == '':
                    return None
                if choice == '?':
                    return "__suggest__"
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(options):
                        return options[idx]
                except ValueError:
                    pass
                print("Invalid choice, try again.")
        else:
            prompt = f"\n{question}"
            if default:
                prompt += f" [{default}]"
            prompt += "\n  (Enter to skip, ? for suggestions): "

            response = input(prompt).strip()
            if response == '?':
                return "__suggest__"
            if response == '':
                return default
            return response

    def run_wizard(self) -> dict:
        """Run the interactive setup wizard."""
        print("\n" + "="*60)
        print("  MEMBERBERRIES PROJECT SETUP WIZARD")
        print("="*60)
        print(f"\nSetting up: {self.project_path.name}")
        print("Answer the questions below to create your CLAUDE.md")
        print("Press Enter to skip any question, or ? for suggestions.\n")

        config = {
            "name": self.project_path.name,
            "description": None,
            "architecture": None,
            "tech_stack": [],
            "conventions": [],
            "notes": []
        }

        # Project description
        response = self.prompt_user(
            "Describe your project in 1-2 sentences:",
            default=None
        )
        if response == "__suggest__":
            suggested = self.detector.suggest_description()
            print(f"  Suggested: {suggested}")
            confirm = input("  Use this? [Y/n]: ").strip().lower()
            if confirm != 'n':
                config["description"] = suggested
        elif response:
            config["description"] = response

        # Architecture
        response = self.prompt_user(
            "What's your project architecture?",
            options=["Monolith", "Microservices", "Serverless", "Monorepo", "MVC", "Clean Architecture"]
        )
        if response == "__suggest__":
            suggested = self.detector.detect_architecture()
            print(f"  Detected: {suggested}")
            confirm = input("  Use this? [Y/n]: ").strip().lower()
            if confirm != 'n':
                config["architecture"] = suggested
        elif response:
            config["architecture"] = response

        # Tech stack
        detected_stack = self.detector.detect_tech_stack()
        if detected_stack:
            print(f"\nDetected tech stack: {', '.join(detected_stack)}")
            confirm = input("Add or modify? [Enter to confirm, or type additions]: ").strip()
            if confirm:
                config["tech_stack"] = detected_stack + [s.strip() for s in confirm.split(",")]
            else:
                config["tech_stack"] = detected_stack
        else:
            response = input("\nTech stack (comma-separated, e.g., Python, FastAPI, PostgreSQL): ").strip()
            if response:
                config["tech_stack"] = [s.strip() for s in response.split(",")]

        # Coding conventions
        print("\nCoding conventions (one per line, empty line to finish):")
        print("  Examples: 'Use type hints', 'Prefer composition over inheritance'")
        while True:
            conv = input("  > ").strip()
            if not conv:
                break
            config["conventions"].append(conv)

        # Important notes
        print("\nImportant notes for Claude (one per line, empty line to finish):")
        print("  Examples: 'Main entry point is src/main.py', 'Tests require Docker'")
        while True:
            note = input("  > ").strip()
            if not note:
                break
            config["notes"].append(note)

        return config

    def generate_claude_md(self, config: dict) -> str:
        """Generate CLAUDE.md content from config."""
        sections = [f"# {config['name']}\n"]

        # Project Overview
        sections.append("## Project Overview\n")
        if config.get("description"):
            sections.append(config["description"] + "\n")
        else:
            sections.append("<!-- Add your project description here -->\n")

        # Architecture
        sections.append("## Architecture\n")
        if config.get("architecture"):
            sections.append(f"**Pattern**: {config['architecture']}\n")
        else:
            sections.append("<!-- Describe your project's architecture -->\n")

        # Tech Stack
        if config.get("tech_stack"):
            sections.append("## Tech Stack\n")
            for tech in config["tech_stack"]:
                sections.append(f"- {tech}")
            sections.append("")

        # Conventions
        sections.append("## Conventions\n")
        if config.get("conventions"):
            for conv in config["conventions"]:
                sections.append(f"- {conv}")
            sections.append("")
        else:
            sections.append("<!-- List coding conventions and standards -->\n")

        # Important Notes
        sections.append("## Important Notes\n")
        if config.get("notes"):
            for note in config["notes"]:
                sections.append(f"- {note}")
            sections.append("")
        else:
            sections.append("<!-- Any other important information for Claude Code -->\n")

        sections.append("---\n")

        return "\n".join(sections)


class ClaudeMDManager:
    """Manages the CLAUDE.md file with memberberries integration."""

    def __init__(self, project_path: Path, storage_mode: str = 'auto'):
        self.project_path = Path(project_path)
        self.claude_md_path = self.project_path / "CLAUDE.md"
        self.bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

    def ensure_claude_md_exists(self, interactive: bool = False) -> bool:
        """Create CLAUDE.md if it doesn't exist.

        Args:
            interactive: If True, run the setup wizard for new files
        """
        if not self.claude_md_path.exists():
            if interactive:
                wizard = InteractiveSetup(self.project_path)
                config = wizard.run_wizard()
                content = wizard.generate_claude_md(config)
                content += f"\n{MB_START}\n\n*Memberberries context will appear here.*\n\n{MB_END}\n"
            else:
                content = self._get_default_template()

            with open(self.claude_md_path, 'w') as f:
                f.write(content)
            print(f"Created {self.claude_md_path}")
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

    def read_claude_md(self) -> tuple:
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

    def generate_memberberries_section(self, query: str = None, max_tokens: int = 2000) -> str:
        """Generate the memberberries section for CLAUDE.md.

        Args:
            query: Query to focus context (task description or prompt)
            max_tokens: Approximate max tokens for the section (rough estimate)

        Returns:
            Formatted memberberries section content
        """
        sections = []

        # Get query for search, or use generic
        search_query = query or "general development context"

        # Header with timestamp
        sections.append(f"\n*Context synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        if query:
            # Truncate long queries for display
            display_query = query[:100] + "..." if len(query) > 100 else query
            sections.append(f"*Query: {display_query}*\n")

        # Get preferences
        prefs = self.bm.get_preferences(search_query, top_k=3)
        if prefs:
            sections.append("\n## Your Preferences")
            for pref in prefs:
                sections.append(f"- **{pref['category']}**: {pref['content']}")

        # Get relevant solutions
        solutions = self.bm.search_solutions(search_query, top_k=2)
        if solutions:
            sections.append("\n## Relevant Solutions")
            for sol in solutions:
                sections.append(f"- **{sol['problem']}**: {sol['solution']}")

        # Get error patterns
        errors = self.bm.search_errors(search_query, top_k=2)
        if errors:
            sections.append("\n## Known Error Patterns")
            for err in errors:
                msg = err['error_message'][:100] + "..." if len(err['error_message']) > 100 else err['error_message']
                sections.append(f"- **{msg}**: {err['resolution']}")

        # Get antipatterns
        antipatterns = self.bm.search_antipatterns(search_query, top_k=2)
        if antipatterns:
            sections.append("\n## Antipatterns (Avoid These)")
            for ap in antipatterns:
                sections.append(f"- **Don't**: {ap['pattern']}")
                sections.append(f"  - *Why*: {ap['reason']}")
                sections.append(f"  - *Instead*: {ap['alternative']}")

        # Get git conventions
        git_convs = self.bm.search_git_conventions(search_query, top_k=2)
        if git_convs:
            sections.append("\n## Git Conventions")
            for conv in git_convs:
                sections.append(f"- **{conv['convention_type']}**: {conv['pattern']}")
                sections.append(f"  - *Example*: `{conv['example']}`")

        # Get testing patterns
        testing = self.bm.search_testing_patterns(search_query, top_k=2)
        if testing:
            sections.append("\n## Testing Patterns")
            for tp in testing:
                sections.append(f"- **{tp['strategy']} ({tp['framework']})**: {tp['pattern']}")

        # Get API notes
        api_notes = self.bm.search_api_notes(search_query, top_k=2)
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

        # If no content was generated, show a friendly message
        if len(sections) <= 2:  # Only header lines
            sections.append("\n*Building your memory...*")
            sections.append("*Insights will be captured automatically as you work.*")

        return "\n".join(sections)

    def sync_claude_md(self, query: str = None, quiet: bool = False) -> bool:
        """Sync CLAUDE.md with fresh memberberries context.

        Args:
            query: Query to focus context (task or prompt)
            quiet: If True, suppress output (for hook mode)

        Returns:
            True if sync was successful
        """
        # Ensure file exists
        created = self.ensure_claude_md_exists()

        # Read existing content
        user_content, _ = self.read_claude_md()

        # Generate new memberberries section
        mb_section = self.generate_memberberries_section(query)

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

        if not quiet and not created:
            print(f"Synced memberberries to {self.claude_md_path}")

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

        print(f"Cleaned memberberries section from {self.claude_md_path}")
        return True


class ClaudeCodeInstaller:
    """Handles Claude Code detection and installation guidance."""

    @staticmethod
    def is_installed() -> bool:
        """Check if Claude Code CLI is installed."""
        return shutil.which("claude") is not None

    @staticmethod
    def get_install_instructions() -> str:
        """Get Claude Code installation instructions."""
        return """
Claude Code Installation Guide
==============================

Claude Code is not installed. Here's how to get it:

Option 1: VS Code Extension (Recommended for VS Code users)
-----------------------------------------------------------
1. Open VS Code
2. Go to Extensions (Cmd+Shift+X / Ctrl+Shift+X)
3. Search for "Claude Code"
4. Click Install
5. The 'claude' CLI command will be available after installation

Option 2: Standalone CLI
------------------------
Visit: https://claude.ai/claude-code

After installation, run 'member setup' again to complete memberberries setup.
"""

    @staticmethod
    def setup_hooks(project_path: Path) -> bool:
        """Set up Claude Code hooks for memberberries integration."""
        claude_dir = project_path / ".claude"
        hooks_dir = claude_dir / "hooks"
        settings_file = claude_dir / "settings.json"

        # Create directories
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # Create sync hook (runs before each prompt)
        sync_script = hooks_dir / "sync-memberberries.sh"
        sync_content = f'''#!/bin/bash
# Memberberries sync hook - runs on every prompt
# Syncs relevant memories based on the user's prompt

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('prompt', ''))" 2>/dev/null)

if [ -z "$PROMPT" ]; then
  exit 0
fi

python3 "{MEMBERBERRIES_DIR}/member.py" --sync-only --query "$PROMPT" --quiet 2>/dev/null
exit 0
'''

        with open(sync_script, 'w') as f:
            f.write(sync_content)
        os.chmod(sync_script, 0o755)

        # Create auto-concentrate hook (runs after Claude responds)
        concentrate_script = hooks_dir / "auto-concentrate.sh"
        concentrate_content = f'''#!/bin/bash
# Memberberries auto-concentrate hook - runs after Claude responds
# Automatically extracts and stores memories from the conversation

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('transcript_path', ''))" 2>/dev/null)

if [ -z "$TRANSCRIPT" ]; then
  exit 0
fi

python3 "{MEMBERBERRIES_DIR}/auto_concentrate.py" --transcript "$TRANSCRIPT" 2>/dev/null
exit 0
'''

        with open(concentrate_script, 'w') as f:
            f.write(concentrate_content)
        os.chmod(concentrate_script, 0o755)

        # Create or update settings.json
        settings = {}
        if settings_file.exists():
            try:
                settings = json.loads(settings_file.read_text())
            except:
                pass

        # Add hook configurations
        settings["hooks"] = settings.get("hooks", {})

        # UserPromptSubmit - sync context before each prompt
        settings["hooks"]["UserPromptSubmit"] = [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": str(sync_script)
                    }
                ]
            }
        ]

        # Stop - auto-concentrate after Claude responds
        settings["hooks"]["Stop"] = [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": str(concentrate_script)
                    }
                ]
            }
        ]

        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        return True


def run_setup_wizard():
    """Run the full setup wizard."""
    print("\n" + "="*60)
    print("     MEMBERBERRIES SETUP WIZARD")
    print("="*60)
    print("\nWelcome! Let's get you set up with memberberries.\n")

    # Step 1: Check Claude Code
    print("Step 1: Checking for Claude Code...")
    if ClaudeCodeInstaller.is_installed():
        print("  Claude Code is installed!")
    else:
        print(ClaudeCodeInstaller.get_install_instructions())
        response = input("\nPress Enter after installing Claude Code, or 'skip' to continue anyway: ").strip()
        if response.lower() != 'skip' and not ClaudeCodeInstaller.is_installed():
            print("\nClaude Code still not detected. Please install it and run 'member setup' again.")
            return

    # Step 2: Project setup
    project_path = Path.cwd()
    print(f"\nStep 2: Setting up project: {project_path.name}")

    # Step 3: Interactive CLAUDE.md setup
    claude_md = project_path / "CLAUDE.md"
    if claude_md.exists():
        response = input("\nCLAUDE.md already exists. Recreate with wizard? [y/N]: ").strip().lower()
        if response == 'y':
            manager = ClaudeMDManager(project_path)
            manager.ensure_claude_md_exists(interactive=True)
    else:
        manager = ClaudeMDManager(project_path)
        manager.ensure_claude_md_exists(interactive=True)

    # Step 4: Set up hooks
    print("\nStep 3: Setting up Claude Code hooks...")
    if ClaudeCodeInstaller.is_installed():
        ClaudeCodeInstaller.setup_hooks(project_path)
        print("  Hooks configured! Memberberries will sync on every prompt.")
    else:
        print("  Skipped (Claude Code not installed)")

    # Step 5: Install member command
    print("\nStep 4: Installing 'member' command...")
    member_py = MEMBERBERRIES_DIR / "member.py"

    # Check for writable bin directories
    bin_paths = [Path("/usr/local/bin"), Path.home() / ".local/bin"]
    installed = False

    for bin_path in bin_paths:
        if bin_path.exists() and os.access(bin_path, os.W_OK):
            link_path = bin_path / "member"
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink()
            link_path.symlink_to(member_py)
            print(f"  Created symlink: {link_path}")
            installed = True
            break

    if not installed:
        print(f"\n  Add this alias to your shell config (~/.zshrc or ~/.bashrc):")
        print(f"    alias member='python3 {member_py}'")

    # Done!
    print("\n" + "="*60)
    print("  SETUP COMPLETE!")
    print("="*60)
    print("""
You're all set! Here's how to use memberberries:

  member "your task"     # Start session with context
  member                 # Start session (syncs general context)
  member init            # Re-run project setup wizard
  member --status        # Check memberberries status

The hooks will automatically sync relevant memories before each prompt.
Your context stays fresh throughout your coding session!

Happy coding!
""")


def launch_claude():
    """Launch Claude Code, replacing the current process."""
    try:
        # Use os.execvp to replace current process with claude
        os.execvp("claude", ["claude"])
    except FileNotFoundError:
        print("Error: 'claude' command not found")
        print("Run 'member setup' to install Claude Code")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Memberberries - Seamless Claude Code Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  member                          Start session with memberberries context
  member "task description"       Start session focused on specific task
  member init                     Interactive project setup wizard
  member setup                    Full installation wizard

Options:
  member --sync-only              Just sync CLAUDE.md, don't launch
  member --sync-only --query "x"  Sync with specific query (for hooks)
  member --clean                  Remove memberberries section
  member --status                 Show memberberries status

The 'member' command:
1. Syncs relevant memories into CLAUDE.md
2. Launches Claude Code with pre-loaded context
3. Hooks keep context fresh on every prompt
        """
    )

    parser.add_argument('task', nargs='?', default=None,
                        help='Task description or subcommand (init, setup)')
    parser.add_argument('--sync-only', action='store_true',
                        help='Only sync CLAUDE.md, do not launch Claude Code')
    parser.add_argument('--query', '-q', type=str, default=None,
                        help='Query for context search (used by hooks)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output (for hook mode)')
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

    # Handle subcommands
    if args.task == 'setup':
        run_setup_wizard()
        return

    if args.task == 'init':
        project_path = Path(args.project) if args.project else Path.cwd()
        manager = ClaudeMDManager(project_path)
        # Force interactive mode by removing existing file temporarily
        if manager.claude_md_path.exists():
            response = input(f"CLAUDE.md exists. Recreate with wizard? [y/N]: ").strip().lower()
            if response != 'y':
                print("Cancelled.")
                return
            manager.claude_md_path.unlink()
        manager.ensure_claude_md_exists(interactive=True)
        print(f"\nCLAUDE.md created! Run 'member' to start your session.")
        return

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
        print(f"\nMemberberries Status")
        print(f"   Project: {project_path}")
        print(f"   Storage: {manager.bm.base_path}")
        print(f"   CLAUDE.md: {'exists' if manager.claude_md_path.exists() else 'not found'}")
        print(f"   Claude Code: {'installed' if ClaudeCodeInstaller.is_installed() else 'not found'}")

        # Check hooks
        hooks_file = project_path / ".claude" / "settings.json"
        hooks_configured = False
        if hooks_file.exists():
            try:
                settings = json.loads(hooks_file.read_text())
                hooks_configured = "UserPromptSubmit" in settings.get("hooks", {})
            except:
                pass
        print(f"   Hooks: {'configured' if hooks_configured else 'not configured'}")

        stats = manager.bm.get_stats()
        print(f"\n   Memories:")
        for key, count in stats.items():
            if count > 0:
                print(f"     - {key}: {count}")
        print()
        return

    # Determine query - prefer --query flag, fall back to task
    query = args.query or args.task

    # Sync CLAUDE.md
    if not args.quiet:
        print(f"\nSyncing memberberries for: {project_path.name}")
        if query:
            display = query[:60] + "..." if len(query) > 60 else query
            print(f"   Query: {display}")

    manager.sync_claude_md(query, quiet=args.quiet)

    # Launch Claude Code unless sync-only
    if not args.sync_only:
        if not args.quiet:
            print(f"\nLaunching Claude Code...\n")
        launch_claude()
    elif not args.quiet:
        print(f"\nCLAUDE.md synced. Run 'claude' to start your session.\n")


if __name__ == '__main__':
    main()
