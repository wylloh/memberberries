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
import re
import json
import random
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from berry_manager import BerryManager

# Optional Anthropic SDK for deep scan
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# Delimiters for the memberberries section in CLAUDE.md
MB_START = "<!-- MEMBERBERRIES CONTEXT - Auto-synced by memberberries. Human: do not edit. Claude: you manage this section. -->"
MB_END = "<!-- END MEMBERBERRIES -->"

# Path to memberberries installation
MEMBERBERRIES_DIR = Path(__file__).resolve().parent  # resolve() first to follow symlinks


class ConfigManager:
    """Manage Memberberries configuration including API keys."""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or MEMBERBERRIES_DIR / ".memberberries"
        self.config_file = self.storage_path / "config.json"
        self._config = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self._config is not None:
            return self._config

        if self.config_file.exists():
            try:
                self._config = json.loads(self.config_file.read_text())
            except json.JSONDecodeError:
                self._config = {}
        else:
            self._config = {}
        return self._config

    def _save_config(self) -> None:
        """Save configuration to file."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(self._config, indent=2))

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._load_config().get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._load_config()
        self._config[key] = value
        self._save_config()

    def get_api_key(self) -> Optional[str]:
        """Get Anthropic API key from config or environment."""
        # Check config first, then environment
        key = self.get("anthropic_api_key")
        if not key:
            key = os.environ.get("ANTHROPIC_API_KEY")
        return key

    def set_api_key(self, key: str) -> None:
        """Set Anthropic API key in config."""
        self.set("anthropic_api_key", key)


class DeepScan:
    """AI-powered deep memory scan using Claude Haiku."""

    SYSTEM_PROMPT = """You are a memory relevance analyzer for a coding assistant.
Your job is to select the most relevant memories for a given task.

You will receive:
1. A task description
2. A list of memory summaries with IDs

Return ONLY a JSON array of memory IDs that are relevant to the task.
Select 5-15 memories maximum. Prioritize:
- Direct matches to the task topic
- Related architectural patterns
- Previous errors/solutions in the same domain
- User preferences that apply

Example output: ["mem_abc123", "mem_def456", "mem_ghi789"]"""

    def __init__(self, api_key: str, berry_manager: BerryManager):
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("Anthropic SDK not installed. Run: pip install anthropic")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.bm = berry_manager

    def _get_all_memory_summaries(self) -> List[Dict[str, str]]:
        """Get summaries of all memories for AI analysis."""
        summaries = []

        # Solutions
        for m in self.bm.index.get("solutions", []):
            summaries.append({
                "id": m.get("id", ""),
                "type": "solution",
                "summary": f"Problem: {m.get('problem', '')[:100]} | Solution: {m.get('solution', '')[:100]}",
                "tags": m.get("tags", [])
            })

        # Errors
        for m in self.bm.index.get("errors", []):
            summaries.append({
                "id": m.get("id", ""),
                "type": "error",
                "summary": f"Error: {m.get('error_message', '')[:100]} | Resolution: {m.get('resolution', '')[:100]}"
            })

        # Preferences
        for m in self.bm.index.get("preferences", []):
            summaries.append({
                "id": m.get("id", ""),
                "type": "preference",
                "summary": f"[{m.get('category', '')}] {m.get('content', '')[:150]}"
            })

        # Antipatterns
        for m in self.bm.index.get("antipatterns", []):
            summaries.append({
                "id": m.get("id", ""),
                "type": "antipattern",
                "summary": f"Don't: {m.get('pattern', '')[:80]} | Instead: {m.get('alternative', '')[:80]}"
            })

        # Pinned
        for m in self.bm.get_pinned_memories():
            summaries.append({
                "id": m.get("id", ""),
                "type": "pinned",
                "summary": f"[{m.get('category', '')}] {m.get('name', '')}: {m.get('content', '')[:100]}"
            })

        return summaries

    def _get_memory_by_id(self, memory_id: str) -> Optional[Dict]:
        """Retrieve full memory content by ID."""
        for mem_type in ["solutions", "errors", "preferences", "antipatterns"]:
            for m in self.bm.index.get(mem_type, []):
                if m.get("id", "").startswith(memory_id) or memory_id in m.get("id", ""):
                    return {"type": mem_type, "data": m}

        for m in self.bm.get_pinned_memories():
            if m.get("id", "").startswith(memory_id) or memory_id in m.get("id", ""):
                return {"type": "pinned", "data": m}

        return None

    def scan(self, task: str, memory_types: List[str] = None) -> List[Dict]:
        """Perform deep scan and return relevant memories.

        Args:
            task: Task description to find relevant context for
            memory_types: Optional filter for memory types

        Returns:
            List of full memory objects deemed relevant
        """
        summaries = self._get_all_memory_summaries()

        if memory_types:
            summaries = [s for s in summaries if s["type"] in memory_types]

        if not summaries:
            return []

        # Format summaries for AI
        summary_text = "\n".join([
            f"[{s['id'][:8]}] ({s['type']}) {s['summary']}"
            for s in summaries
        ])

        # Call Haiku for relevance analysis
        try:
            response = self.client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=500,
                system=self.SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Task: {task}\n\nMemories:\n{summary_text}"
                }]
            )

            # Parse response
            content = response.content[0].text.strip()
            # Extract JSON array from response
            if "[" in content and "]" in content:
                start = content.find("[")
                end = content.rfind("]") + 1
                memory_ids = json.loads(content[start:end])
            else:
                memory_ids = []

        except Exception as e:
            print(f"Deep scan error: {e}")
            return []

        # Fetch full memories
        relevant_memories = []
        for mid in memory_ids:
            # Handle both full and partial IDs
            mem = self._get_memory_by_id(mid)
            if mem:
                relevant_memories.append(mem)

        return relevant_memories


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
    """Manages the CLAUDE.md file with memberberries integration.

    Now supports Claude-managed memory architecture where Claude writes
    its own memories using [MEMORY #tags] markers.
    """

    # Session detection threshold (minutes)
    SESSION_TIMEOUT_MINUTES = 30

    # Maximum active memories in CLAUDE.md
    MAX_ACTIVE_MEMORIES = 15

    def __init__(self, project_path: Path, storage_mode: str = 'auto'):
        self.project_path = Path(project_path)
        self.claude_md_path = self.project_path / "CLAUDE.md"
        self.bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

    def _is_new_session(self) -> bool:
        """Detect if this is a new session based on time gap.

        Returns True if:
        - CLAUDE.md doesn't exist
        - No last sync timestamp found
        - Time since last sync > SESSION_TIMEOUT_MINUTES
        """
        last_sync = self._get_last_sync_time()
        if last_sync is None:
            return True
        gap = datetime.now() - last_sync
        return gap.total_seconds() > (self.SESSION_TIMEOUT_MINUTES * 60)

    def _get_last_sync_time(self) -> Optional[datetime]:
        """Get last sync timestamp from CLAUDE.md."""
        if not self.claude_md_path.exists():
            return None

        try:
            content = self.claude_md_path.read_text()
            # Parse: *Last sync: 2026-01-03 12:15*
            match = re.search(r'\*Last sync: (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\*', content)
            if match:
                return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M')
        except:
            pass
        return None

    def _parse_active_memories_from_claude_md(self) -> List[Dict]:
        """Parse active memories from existing CLAUDE.md.

        Preserves memories Claude has been working with during the session.
        """
        if not self.claude_md_path.exists():
            return []

        try:
            content = self.claude_md_path.read_text()

            # Find the Active Memories section
            memories = []
            # Pattern: - `id` [timestamp] #tags: summary
            pattern = r'- `([a-f0-9]{8})` \[([^\]]+)\] ([^:]+): (.+?)(?:\n|$)'
            matches = re.finditer(pattern, content)

            for match in matches:
                mem_id = match.group(1)
                timestamp = match.group(2)
                tags_str = match.group(3)
                summary = match.group(4).strip()

                # Parse tags
                tags = re.findall(r'#(\w+)', tags_str)

                memories.append({
                    'id': mem_id,
                    'timestamp': timestamp,
                    'tags': tags,
                    'problem': summary,
                    'parsed_from_claude_md': True
                })

            return memories
        except:
            return []

    def _get_relevant_memories_for_session(self, query: str = None, limit: int = 12) -> List[Dict]:
        """Get relevant memories from index for new session start.

        Uses semantic search to find the most relevant memories for the current
        query/project context, plus a serendipity slot for unexpected insights.

        Memory retrieval philosophy:
        - 95% relevance-based (pinned, high-gravity, task, semantic)
        - 5% serendipity (random deep memory that might spark unexpected insights)

        This emulates human memory, where sometimes a random old observation
        unlocks progress on a current problem.
        """
        memories = []
        existing_ids = set()
        search_query = query or "general development context"

        def add_memory(mem, priority):
            """Helper to add memory if not duplicate."""
            mem_id = mem.get('id')
            if mem_id and mem_id not in existing_ids:
                mem['priority'] = priority
                memories.append(mem)
                existing_ids.add(mem_id)
                return True
            return False

        # Get pinned memories first (always included)
        pinned = self.bm.get_pinned_memories()
        for mem in pinned[:3]:
            add_memory(mem, 'pinned')

        # Get high-gravity memories
        high_gravity = self.bm.get_high_gravity_memories(top_k=3)
        for mem in high_gravity:
            add_memory(mem, 'high_gravity')

        # Get active task memories if set
        active_task_id = self.bm.index.get("active_task")
        if active_task_id:
            task_memories = self.bm.get_task_memories(active_task_id, include_subtasks=True)
            for mem in task_memories[:3]:
                add_memory(mem, 'active_task')

        # Reserve 1 slot for serendipity (random deep memory)
        # This is the "5% magic" - a random memory that might spark insight
        serendipity_added = False
        if len(memories) < limit - 1:  # Leave room for at least 1 relevant + 1 serendipity
            serendipity_mem = self._get_serendipity_memory(existing_ids)
            if serendipity_mem:
                add_memory(serendipity_mem, 'serendipity')
                serendipity_added = True

        # Fill remaining slots with semantically relevant memories
        remaining = limit - len(memories)
        if remaining > 0:
            solutions = self.bm.search_solutions(search_query, top_k=remaining + 5)  # Get extras to filter
            for mem in solutions:
                if add_memory(mem, 'relevant'):
                    if len(memories) >= limit:
                        break

        return memories[:limit]

    def _get_serendipity_memory(self, exclude_ids: set) -> Optional[Dict]:
        """Get a random 'deep' memory for serendipitous recall.

        Selects from older, lower-gravity memories that might not normally
        surface but could spark unexpected insights. This emulates how human
        memory sometimes surfaces old observations that unlock current problems.

        Args:
            exclude_ids: Set of memory IDs already in the session

        Returns:
            A random memory dict, or None if no candidates
        """
        candidates = []

        # Collect all non-archived memories from all types
        memory_types = ['solutions', 'errors', 'antipatterns', 'preferences',
                        'git_conventions', 'dependencies', 'testing', 'api_notes']

        for mem_type in memory_types:
            for mem in self.bm.index.get(mem_type, []):
                mem_id = mem.get('id')
                # Skip if already included, archived, or pinned
                if (mem_id in exclude_ids or
                    mem.get('archived') or
                    mem.get('pinned')):
                    continue

                # Prefer older memories (more likely to be "forgotten")
                # and lower gravity (not frequently accessed)
                gravity = mem.get('gravitational_mass', 1.0)
                if gravity < 2.0:  # Not high-gravity
                    candidates.append(mem)

        if not candidates:
            return None

        # Weight selection toward older memories
        # Older = more "forgotten" = more serendipitous when recalled
        def age_weight(mem):
            try:
                ts = datetime.fromisoformat(mem.get('timestamp', ''))
                age_days = (datetime.now() - ts).days
                return max(1, age_days)  # Older = higher weight
            except:
                return 1

        weights = [age_weight(m) for m in candidates]
        total = sum(weights)
        if total == 0:
            return random.choice(candidates)

        # Weighted random selection
        r = random.uniform(0, total)
        cumulative = 0
        for mem, weight in zip(candidates, weights):
            cumulative += weight
            if r <= cumulative:
                return mem

        return candidates[-1] if candidates else None

    def _generate_claude_managed_section(self, active_memories: List[Dict], query: str = None) -> str:
        """Generate Claude-managed memory section.

        This is the new architecture where Claude writes its own memories using
        [MEMORY #tags] markers and archives drifting memories with [ARCHIVE id].
        """
        lines = [
            "",
            "## Memory Instructions (for Claude)",
            "You manage this section. After completing significant work, write a memory marker in your response:",
            "  `[MEMORY #tag1 #tag2] one-line summary of insight or decision`",
            "",
            "To archive a memory that's no longer relevant to the current task, include in your response:",
            "  `[ARCHIVE id]` (use the 8-char ID from Active Memories below)",
            "",
            "These markers are parsed after your response and persisted to the memory index.",
            "",
            "## Active Memories",
        ]

        # Add active memories (up to MAX_ACTIVE_MEMORIES)
        if active_memories:
            for mem in active_memories[:self.MAX_ACTIVE_MEMORIES]:
                mem_id = mem.get('id', '')[:8] if mem.get('id') else '????????'
                timestamp = mem.get('timestamp', '')[:16] if mem.get('timestamp') else datetime.now().strftime('%Y-%m-%d %H:%M')
                tags = ' '.join(f"#{t}" for t in mem.get('tags', [])) if mem.get('tags') else '#general'
                # Get summary from various possible fields
                summary = (
                    mem.get('problem') or
                    mem.get('summary') or
                    mem.get('content') or
                    mem.get('name', 'Memory')
                )
                # Truncate long summaries
                if len(summary) > 100:
                    summary = summary[:97] + "..."
                # Clean up summary (remove newlines, etc.)
                summary = summary.replace('\n', ' ').strip()

                # Add priority indicator if present
                priority = mem.get('priority', '')
                prefix = ''
                if priority == 'pinned':
                    prefix = '📌 '
                elif priority == 'high_gravity':
                    prefix = '⚫ '
                elif priority == 'active_task':
                    prefix = '🎯 '

                lines.append(f"- `{mem_id}` [{timestamp}] {tags}: {prefix}{summary}")
        else:
            lines.append("*(No memories yet - they'll appear as you work)*")

        # Add active task context if set
        active_task_id = self.bm.index.get("active_task")
        if active_task_id:
            clusters = self.bm.index.get("task_clusters", {})
            if active_task_id in clusters:
                task = clusters[active_task_id]
                lines.extend([
                    "",
                    f"## Active Task: {task['name']}",
                ])
                if task.get('description'):
                    lines.append(f"*{task['description']}*")

        lines.extend([
            "",
            "## Session Context",
            f"*Last sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        ])

        if query:
            display_query = query[:80] + "..." if len(query) > 80 else query
            lines.append(f"*Current focus: {display_query}*")

        lines.extend([
            "",
            "<!-- END MEMBERBERRIES -->"
        ])

        return "\n".join(lines)

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

        # Find memberberries section - check for both old and new markers
        # Old: "<!-- MEMBERBERRIES CONTEXT - Auto-managed, do not edit below this line -->"
        # New: "<!-- MEMBERBERRIES CONTEXT - Auto-synced by memberberries..."
        old_marker = "<!-- MEMBERBERRIES CONTEXT - Auto-managed"
        new_marker = "<!-- MEMBERBERRIES CONTEXT - Auto-synced"

        start_idx = content.find(MB_START)
        if start_idx == -1:
            # Try old marker pattern
            start_idx = content.find(old_marker)
            if start_idx != -1:
                # Find end of this line for old marker
                line_end = content.find("-->", start_idx)
                if line_end != -1:
                    start_idx = line_end + 3  # Skip past -->
        if start_idx == -1:
            start_idx = content.find(new_marker)
            if start_idx != -1:
                line_end = content.find("-->", start_idx)
                if line_end != -1:
                    start_idx = line_end + 3

        end_idx = content.find(MB_END)

        if start_idx == -1:
            # No memberberries section, all is user content
            return content.rstrip(), ""

        # Find the actual start of the marker line (for user content extraction)
        marker_line_start = content.rfind("\n", 0, start_idx)
        if marker_line_start == -1:
            marker_line_start = 0

        # Extract user content (everything before the marker line)
        user_content = content[:marker_line_start].rstrip()

        # Extract memberberries content
        if end_idx != -1:
            mb_content = content[start_idx:end_idx].strip()
        else:
            mb_content = content[start_idx:].strip()

        return user_content, mb_content

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (1 token ≈ 4 characters)."""
        return len(text) // 4

    def _smart_truncate(self, text: str, max_len: int = 300) -> str:
        """Truncate text intelligently, preserving complete thoughts."""
        if len(text) <= max_len:
            return text

        # Look for natural break points before max_len
        break_chars = ['. ', '! ', '? ', '; ', ', ', ' - ', '\n']
        best_break = max_len

        for char in break_chars:
            idx = text.rfind(char, 0, max_len)
            if idx != -1 and idx > max_len * 0.6:
                best_break = idx + len(char)
                break

        if best_break == max_len:
            space_idx = text.rfind(' ', 0, max_len)
            if space_idx > max_len * 0.6:
                best_break = space_idx

        return text[:best_break].strip() + "..."

    def _contains_credential_pattern(self, text: str) -> bool:
        """Check if text contains credential-like patterns that shouldn't be compressed."""
        import re
        credential_patterns = [
            r'ssh\s+\w+@',           # SSH connections
            r'[\w.-]+@[\w.-]+:\d+',  # user@host:port
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP addresses
            r':[A-Za-z0-9+/=]{20,}', # Long base64-like tokens
            r'sk-[a-zA-Z0-9]{20,}',  # API keys (OpenAI style)
            r'ghp_[a-zA-Z0-9]{30,}', # GitHub tokens
            r'Bearer\s+\S{20,}',     # Bearer tokens
            r'-----BEGIN',           # PEM keys
            r'~/.ssh/',              # SSH paths
            r'\.pem\b',              # PEM files
            r'\.key\b',              # Key files
            r'password[=:]\s*\S+',   # Password assignments
            r'api[_-]?key[=:]\s*\S+', # API key assignments
        ]
        for pattern in credential_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _compress_shorthand(self, text: str, protect_credentials: bool = True) -> str:
        """Compress text using shorthand abbreviations to save tokens.

        Applies common programming abbreviations while preserving meaning.
        Skips compression for credential-containing text to preserve accuracy.

        Args:
            text: Text to compress
            protect_credentials: If True, skip compression for credential patterns
        """
        import re

        # Don't compress if text contains credentials
        if protect_credentials and self._contains_credential_pattern(text):
            return text

        # Common abbreviations (ordered from longest to shortest to avoid conflicts)
        abbrevs = [
            ('configuration', 'config'),
            ('authentication', 'auth'),
            ('authorization', 'authz'),
            ('implementation', 'impl'),
            ('specification', 'spec'),
            ('requirements', 'reqs'),
            ('dependencies', 'deps'),
            ('initialization', 'init'),
            ('administrator', 'admin'),
            ('documentation', 'docs'),
            ('application', 'app'),
            ('environment', 'env'),
            ('development', 'dev'),
            ('production', 'prod'),
            ('information', 'info'),
            ('dependency', 'dep'),
            ('repository', 'repo'),
            ('directory', 'dir'),
            ('components', 'comps'),
            ('component', 'comp'),
            ('initialize', 'init'),
            ('management', 'mgmt'),
            ('attributes', 'attrs'),
            ('properties', 'props'),
            ('expression', 'expr'),
            ('utilities', 'utils'),
            ('libraries', 'libs'),
            ('temporary', 'tmp'),
            ('javascript', 'JS'),
            ('typescript', 'TS'),
            ('function', 'fn'),
            ('variable', 'var'),
            ('parameter', 'param'),
            ('interface', 'iface'),
            ('attribute', 'attr'),
            ('arguments', 'args'),
            ('property', 'prop'),
            ('database', 'db'),
            ('argument', 'arg'),
            ('packages', 'pkgs'),
            ('messages', 'msgs'),
            ('commands', 'cmds'),
            ('response', 'resp'),
            ('previous', 'prev'),
            ('original', 'orig'),
            ('objects', 'objs'),
            ('request', 'req'),
            ('message', 'msg'),
            ('execute', 'exec'),
            ('command', 'cmd'),
            ('current', 'curr'),
            ('utility', 'util'),
            ('library', 'lib'),
            ('package', 'pkg'),
            ('version', 'ver'),
            ('maximum', 'max'),
            ('minimum', 'min'),
            ('boolean', 'bool'),
            ('integer', 'int'),
            ('context', 'ctx'),
            ('source', 'src'),
            ('number', 'num'),
            ('string', 'str'),
            ('object', 'obj'),
            ('buffer', 'buf'),
            ('python', 'py'),
            ('button', 'btn'),
            ('image', 'img'),
            ('index', 'idx'),
            ('char', 'ch'),
        ]

        result = text
        for full, short in abbrevs:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(full), re.IGNORECASE)
            result = pattern.sub(short, result)

        return result

    def _get_memory_quality(self, item: dict) -> tuple:
        """Check memory quality and return (quality_indicator, needs_refinement).

        Returns:
            Tuple of (indicator_string, bool for needs_refinement)
            - "" = good quality
            - " ⚠️" = has minor issues
            - " ❓" = needs refinement
        """
        # Get content to check
        content = item.get('problem', '') + item.get('solution', '') + item.get('content', '')

        issues = 0

        # Check for quality problems
        if len(content) < 20:
            issues += 1
        if '→' in content:  # Line numbers from stack traces
            issues += 1
        if content.count('{') > 2 or content.count('[') > 2:  # JSON-like
            issues += 1
        if '...' in content[-15:]:  # Truncated awkwardly
            issues += 1
        if 'stop_reason' in content or 'input_tokens' in content:  # API fragments
            issues += 2
        if 'MEMBERBERRIES' in content or 'Auto-managed' in content:  # Template text
            issues += 2

        if issues == 0:
            return ("", False)
        elif issues <= 1:
            return (" ⚠️", False)
        else:
            return (" ❓", True)

    def _format_memory_item(self, memory_type: str, item: dict, compress: bool = True,
                            include_id: bool = True) -> str:
        """Format a single memory item for display.

        Uses smart truncation to preserve meaningful context.
        Applies shorthand compression to save tokens.
        Includes memory ID for lookup capability.

        Args:
            memory_type: Type of memory (pinned, preference, solution, etc.)
            item: Memory data dictionary
            compress: Whether to apply shorthand compression (default: True)
            include_id: Whether to include memory ID for lookup (default: True)
        """
        def process(text: str, max_len: int) -> str:
            """Truncate and optionally compress text."""
            result = self._smart_truncate(text, max_len=max_len)
            if compress:
                result = self._compress_shorthand(result)
            return result

        # Get ID prefix if available
        mem_id = item.get('id', '')[:8] if include_id and item.get('id') else ''
        id_prefix = f"`{mem_id}` " if mem_id else ""

        # Get quality indicator
        quality_indicator, _ = self._get_memory_quality(item)

        if memory_type == 'pinned':
            name = item.get('name', 'Pinned')
            content = process(item.get('content', ''), 500)
            category = item.get('category', '')
            sensitive_marker = " 🔒" if item.get('sensitive') else ""
            return f"- {id_prefix}**{name}**{sensitive_marker} [{category}]: {content}"
        elif memory_type == 'preference':
            content = process(item['content'], 400)
            return f"- {id_prefix}**{item['category']}**: {content}"
        elif memory_type == 'solution':
            problem = process(item['problem'], 200)
            solution = process(item['solution'], 400)
            tags = item.get('tags', [])

            # Special formatting for Claude response types
            if 'decision' in tags:
                return f"- {id_prefix}**🧠 Decision**: {solution}"
            elif 'summary' in tags:
                return f"- {id_prefix}**📋 Summary**: {solution}"
            elif 'code' in tags and item.get('code_snippet'):
                lang = next((t for t in tags if t not in ['code', 'claude-response']), 'code')
                snippet = item['code_snippet'][:200] + "..." if len(item.get('code_snippet', '')) > 200 else item.get('code_snippet', '')
                return f"- {id_prefix}**{problem}**: `{lang}` implementation\n  ```\n  {snippet}\n  ```"

            # Standard solution format
            pin_marker = " 📌" if item.get('pinned') else ""
            return f"- {id_prefix}**{problem}**{pin_marker}{quality_indicator}: {solution}"
        elif memory_type == 'error':
            msg = process(item['error_message'], 200)
            resolution = process(item['resolution'], 400)
            # Structured format for debugging
            lines = [f"- {id_prefix}**Error**{quality_indicator}: {msg}"]
            lines.append(f"  - *Resolution*: {resolution}")
            # Add actionable first step if we can infer one
            if 'check' in resolution.lower() or 'verify' in resolution.lower():
                lines.append(f"  - *First*: Verify the fix applies to current situation")
            elif 'install' in resolution.lower() or 'add' in resolution.lower():
                lines.append(f"  - *First*: Check if dependency already exists")
            elif 'config' in resolution.lower() or 'setting' in resolution.lower():
                lines.append(f"  - *First*: Locate and review config file")
            return "\n".join(lines)
        elif memory_type == 'antipattern':
            pattern = process(item['pattern'], 200)
            reason = process(item['reason'], 200)
            alt = process(item['alternative'], 200)
            return f"- {id_prefix}**Don't**{quality_indicator}: {pattern}\n  - *Why*: {reason}\n  - *Instead*: {alt}"
        elif memory_type == 'git_convention':
            pattern = process(item['pattern'], 200)
            example = process(item['example'], 150)
            return f"- {id_prefix}**{item['convention_type']}**: {pattern}\n  - *Example*: `{example}`"
        elif memory_type == 'testing':
            pattern = process(item['pattern'], 300)
            return f"- {id_prefix}**{item['strategy']} ({item['framework']})**: {pattern}"
        elif memory_type == 'api_note':
            notes = process(item['notes'], 400)
            return f"- {id_prefix}**{item['service_name']}**: {notes}"
        return ""

    def generate_memberberries_section(self, query: str = None, max_tokens: int = 1500) -> str:
        """Generate the memberberries section for CLAUDE.md with token budget.

        Args:
            query: Query to focus context (task description or prompt)
            max_tokens: Maximum tokens for the section (keeps CLAUDE.md lean)

        Returns:
            Formatted memberberries section content
        """
        # Get query for search, or use generic
        search_query = query or "general development context"

        # Header with actionable context for Claude
        header_lines = [
            f"\n*Synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "**How to use this context:**",
            "- 📌 Pinned = Protected info (credentials, configs) - preserve exactly",
            "- ⚫ High Gravity = Frequently referenced - likely relevant",
            "- 🎯 Active Task = Current focus area - prioritize these memories",
            "- Memories ranked by importance; top items most critical",
        ]

        # Show active task if set
        active_task_id = self.bm.index.get("active_task")
        if active_task_id:
            clusters = self.bm.index.get("task_clusters", {})
            if active_task_id in clusters:
                task = clusters[active_task_id]
                header_lines.append(f"\n🎯 **Active Task: {task['name']}**")
                if task.get('description'):
                    header_lines.append(f"   {task['description']}")

        if query:
            display_query = query[:80] + "..." if len(query) > 80 else query
            header_lines.append(f"\n*Current query: {display_query}*")

        header = "\n".join(header_lines)
        current_tokens = self._estimate_tokens(header)

        # Collect all memories with priority scores
        # Priority: Higher = more important = added first
        memory_groups = []

        # Priority 0 (HIGHEST): Pinned memories - always shown first
        pinned = self.bm.get_pinned_memories()
        if pinned:
            memory_groups.append(('📌 Pinned', 'pinned', pinned, 200))

        # Priority 0.5: Active task memories (if task is focused)
        if active_task_id:
            task_memories = self.bm.get_task_memories(active_task_id, include_subtasks=True)
            if task_memories:
                memory_groups.append(('🎯 Active Task Memories', 'solution', task_memories[:5], 175))

        # Priority 0.6: High-gravity memories (most referenced/important)
        high_gravity = self.bm.get_high_gravity_memories(top_k=3)
        if high_gravity:
            memory_groups.append(('⚫ High Gravity', 'solution', high_gravity, 150))

        # Priority 1: High-priority tagged items (repeated, confirmed)
        solutions = self.bm.search_solutions(search_query, top_k=5)
        high_priority = [s for s in solutions if any(t in s.get('tags', []) for t in ['repeated', 'confirmed', 'high-priority'])]
        if high_priority:
            memory_groups.append(('High Priority', 'solution', high_priority, 100))

        # Priority 2: Preferences (always relevant)
        prefs = self.bm.get_preferences(search_query, top_k=3)
        if prefs:
            memory_groups.append(('Your Preferences', 'preference', prefs, 90))

        # Priority 3: Regular solutions
        regular_solutions = [s for s in solutions if s not in high_priority][:3]
        if regular_solutions:
            memory_groups.append(('Relevant Solutions', 'solution', regular_solutions, 80))

        # Priority 4: Error patterns
        errors = self.bm.search_errors(search_query, top_k=2)
        if errors:
            memory_groups.append(('Known Error Patterns', 'error', errors, 70))

        # Priority 5: Antipatterns
        antipatterns = self.bm.search_antipatterns(search_query, top_k=2)
        if antipatterns:
            memory_groups.append(('Antipatterns (Avoid)', 'antipattern', antipatterns, 60))

        # Priority 6: Git conventions
        git_convs = self.bm.search_git_conventions(search_query, top_k=2)
        if git_convs:
            memory_groups.append(('Git Conventions', 'git_convention', git_convs, 50))

        # Priority 7: Testing patterns
        testing = self.bm.search_testing_patterns(search_query, top_k=2)
        if testing:
            memory_groups.append(('Testing Patterns', 'testing', testing, 40))

        # Priority 8: API notes
        api_notes = self.bm.search_api_notes(search_query, top_k=2)
        if api_notes:
            memory_groups.append(('API Notes', 'api_note', api_notes, 30))

        # Sort by priority (highest first)
        memory_groups.sort(key=lambda x: x[3], reverse=True)

        # Build sections within token budget
        # Track seen memory IDs to avoid duplication
        seen_ids = set()
        sections = [header]
        items_added = 0
        memories_needing_refinement = []  # Track low-quality memories

        for group_name, memory_type, items, _ in memory_groups:
            if current_tokens >= max_tokens:
                break

            group_header = f"\n## {group_name}"
            group_tokens = self._estimate_tokens(group_header)

            # Check if we can fit at least the header + one item
            if current_tokens + group_tokens > max_tokens:
                break

            group_lines = [group_header]
            group_tokens = self._estimate_tokens(group_header)

            for item in items:
                # Deduplication: skip if we've already seen this memory
                item_id = item.get('id')
                if item_id:
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                # Check quality and track if needs refinement
                _, needs_refinement = self._get_memory_quality(item)
                if needs_refinement and item_id:
                    memories_needing_refinement.append(item_id[:8])

                formatted = self._format_memory_item(memory_type, item)
                item_tokens = self._estimate_tokens(formatted)

                if current_tokens + group_tokens + item_tokens > max_tokens:
                    break

                group_lines.append(formatted)
                group_tokens += item_tokens
                items_added += 1

            if len(group_lines) > 1:  # Has items beyond header
                sections.append("\n".join(group_lines))
                current_tokens += group_tokens

        # Add project context if we have room
        project_ctx = self.bm.get_project_context(str(self.project_path))
        if project_ctx and current_tokens < max_tokens - 100:
            ctx_lines = ["\n## Project Context"]
            if project_ctx.get('description'):
                ctx_lines.append(f"- **Description**: {project_ctx['description'][:100]}")
            if project_ctx.get('tech_stack'):
                ctx_lines.append(f"- **Tech Stack**: {', '.join(project_ctx['tech_stack'][:5])}")
            ctx_text = "\n".join(ctx_lines)
            if current_tokens + self._estimate_tokens(ctx_text) <= max_tokens:
                sections.append(ctx_text)

        # Add self-reflection instruction if there are low-quality memories
        if memories_needing_refinement and current_tokens < max_tokens - 50:
            refinement_hint = (
                "\n*💭 Some memories marked with ❓ may need refinement. "
                "To improve: `memberberry refine <id>: <better summary>`*"
            )
            sections.append(refinement_hint)

        # If no content was generated, show a friendly message
        if items_added == 0:
            sections.append("\n*Building your memory...*")
            sections.append("*Insights will be captured automatically as you work.*")

        return "\n".join(sections)

    def _generate_deep_context(self, memories: List[Dict], task: str) -> str:
        """Generate context section from AI-selected memories.

        Args:
            memories: List of memory dicts from DeepScan
            task: Task description for context header

        Returns:
            Formatted context section for CLAUDE.md
        """
        lines = [
            f"\n*Deep scan: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            f"*Task: {task[:80]}*",
            ""
        ]

        # Group by type
        solutions = [m for m in memories if m["type"] == "solution"]
        errors = [m for m in memories if m["type"] == "error"]
        preferences = [m for m in memories if m["type"] == "preference"]
        pinned = [m for m in memories if m["type"] == "pinned"]
        antipatterns = [m for m in memories if m["type"] == "antipattern"]

        if pinned:
            lines.append("## 📌 Pinned Context")
            for m in pinned:
                data = m["data"]
                lines.append(f"- **{data.get('name', 'Pinned')}**: {data.get('content', '')}")
            lines.append("")

        if preferences:
            lines.append("## ⚙️ Relevant Preferences")
            for m in preferences:
                data = m["data"]
                lines.append(f"- **{data.get('category', '')}**: {data.get('content', '')}")
            lines.append("")

        if solutions:
            lines.append("## 💡 Relevant Solutions")
            for m in solutions:
                data = m["data"]
                mem_id = data.get("id", "")[:8]
                lines.append(f"- `{mem_id}` **{data.get('problem', '')}**: {data.get('solution', '')}")
            lines.append("")

        if errors:
            lines.append("## ⚠️ Related Errors")
            for m in errors:
                data = m["data"]
                mem_id = data.get("id", "")[:8]
                lines.append(f"- `{mem_id}` **{data.get('error_message', '')}**")
                lines.append(f"  - Resolution: {data.get('resolution', '')}")
            lines.append("")

        if antipatterns:
            lines.append("## 🚫 Antipatterns to Avoid")
            for m in antipatterns:
                data = m["data"]
                lines.append(f"- **Don't**: {data.get('pattern', '')}")
                lines.append(f"  - Instead: {data.get('alternative', '')}")
            lines.append("")

        return "\n".join(lines)

    def sync_claude_md(self, query: str = None, quiet: bool = False) -> bool:
        """Sync CLAUDE.md with fresh memberberries context.

        Uses Claude-managed memory architecture:
        - New session (>30 min gap): scrape index for relevant memories
        - Continuing session: preserve active memories from CLAUDE.md

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

        # Detect if this is a new session
        is_new_session = self._is_new_session()

        if is_new_session:
            # New session: scrape index for relevant memories
            active_memories = self._get_relevant_memories_for_session(query, limit=12)
            if not quiet:
                print(f"🫐 New session - loaded {len(active_memories)} relevant memories")
        else:
            # Continuing session: preserve existing active memories
            active_memories = self._parse_active_memories_from_claude_md()
            if active_memories:
                if not quiet:
                    print(f"🫐 Continuing session - preserved {len(active_memories)} active memories")
            else:
                # No memories to preserve - load from index
                # This handles the case where CLAUDE.md was cleaned or is empty
                active_memories = self._get_relevant_memories_for_session(query, limit=12)
                if not quiet and active_memories:
                    print(f"🫐 Loaded {len(active_memories)} memories from index")

        # Generate new Claude-managed section
        mb_section = self._generate_claude_managed_section(active_memories, query)

        # Combine and write
        # Only add separator if user content doesn't already end with one
        separator = "" if user_content.rstrip().endswith("---") else "\n\n---"
        new_content = f"""{user_content}{separator}

{MB_START}
{mb_section}
"""

        with open(self.claude_md_path, 'w') as f:
            f.write(new_content)

        if not quiet and not created:
            print(f"Synced memberberries to {self.claude_md_path}")

        return True

    def update_claude_md(self, mb_section: str) -> bool:
        """Update CLAUDE.md with specific memberberries content.

        Args:
            mb_section: Pre-formatted memberberries section content

        Returns:
            True if update was successful
        """
        # Ensure file exists
        self.ensure_claude_md_exists()

        # Read existing content
        user_content, _ = self.read_claude_md()

        # Combine and write
        separator = "" if user_content.rstrip().endswith("---") else "\n\n---"
        new_content = f"""{user_content}{separator}

{MB_START}
{mb_section}
{MB_END}
"""

        with open(self.claude_md_path, 'w') as f:
            f.write(new_content)

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


def _get_shell_config_path() -> Path:
    """Detect the user's shell and return the appropriate config file path.

    Returns:
        Path to shell config file, or None if unknown shell
    """
    shell = os.environ.get("SHELL", "")
    home = Path.home()

    if "zsh" in shell:
        return home / ".zshrc"
    elif "bash" in shell:
        # Prefer .bashrc on Linux, .bash_profile on macOS
        if (home / ".bash_profile").exists():
            return home / ".bash_profile"
        return home / ".bashrc"
    elif "fish" in shell:
        return home / ".config" / "fish" / "config.fish"

    # Default to .profile as fallback
    return home / ".profile"


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
    installed = False
    needs_path_update = False
    install_path = None

    # Try /usr/local/bin first (if writable)
    if Path("/usr/local/bin").exists() and os.access("/usr/local/bin", os.W_OK):
        install_path = Path("/usr/local/bin")
    else:
        # Use ~/.local/bin (create if needed)
        local_bin = Path.home() / ".local" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        install_path = local_bin

        # Check if ~/.local/bin is in PATH
        current_path = os.environ.get("PATH", "")
        if str(local_bin) not in current_path:
            needs_path_update = True

    # Create the symlink
    if install_path:
        link_path = install_path / "member"
        try:
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink()
            link_path.symlink_to(member_py)
            print(f"  Created symlink: {link_path}")
            installed = True
        except OSError as e:
            print(f"  Warning: Could not create symlink: {e}")

    # Update shell config if needed
    if installed and needs_path_update:
        shell_config = _get_shell_config_path()

        if shell_config:
            # Check if already in config
            config_content = ""
            if shell_config.exists():
                config_content = shell_config.read_text()

            if ".local/bin" not in config_content:
                with open(shell_config, 'a') as f:
                    f.write(f'\n# Added by Memberberries\nexport PATH="$HOME/.local/bin:$PATH"\n')
                print(f"  Added ~/.local/bin to PATH in {shell_config.name}")
                print(f"\n  NOTE: Run 'source {shell_config}' or restart your terminal")
                print(f"        for the 'member' command to be available.")
            else:
                print(f"  ~/.local/bin already in {shell_config.name}")
        else:
            print(f"\n  Add this to your shell config:")
            print(f'    export PATH="$HOME/.local/bin:$PATH"')

    if not installed:
        print(f"\n  Fallback: Add this alias to your shell config:")
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
  member pin                      Pin a new memory (interactive)
  member pins                     List all pinned memories
  member unpin <id>               Remove a pinned memory

Options:
  member --sync-only              Just sync CLAUDE.md, don't launch
  member --sync-only --query "x"  Sync with specific query (for hooks)
  member --clean                  Remove memberberries section
  member --status                 Show memberberries status

The 'member' command:
1. Syncs relevant memories into CLAUDE.md
2. Launches Claude Code with pre-loaded context
3. Hooks keep context fresh on every prompt

Pinned Memories:
  Pinned memories are protected and always shown at the top.
  Use them for SSH credentials, API configs, server details, etc.

Task Clusters (Gravitational Memory Organization):
  member task "name"              Create a new task cluster
  member task "name" --parent ID  Create subtask under parent
  member tasks                    List all task clusters
  member task-show <id>           Show memories for a task

Git Workflow:
  member --install-hook           Install git pre-commit hook (auto-cleans CLAUDE.md)
  member --regenerate-hooks       Regenerate Claude Code hooks with correct paths
  member --clean                  Manually clean memberberries section before commit

Mid-Session Context:
  member refresh                  Output current context (Claude can re-read mid-session)
  member context                  Show what's currently in CLAUDE.md memberberries section
  member feedback <id> useful     Mark a memory as useful (increases gravity)
  member feedback <id> not-useful Mark a memory as not useful (decreases gravity)

Analytics:
  member stats                    Show memory analytics and gravity distribution
  member stats --detailed         Show detailed breakdown with individual memories

Memory Lookup:
  member lookup <id>              Show full content of a memory by ID
  member expand                   Expand all memories in current context (full detail)

Active Task:
  member focus <task_id>          Set active task (highlighted in context)
  member focus --clear            Clear active task focus

Maintenance:
  member update                   Pull latest memberberries and regenerate hooks
  member clean                    Remove low-quality and duplicate memories
  member report                   Generate bug report with system info
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
    parser.add_argument('--install-hook', action='store_true',
                        help='Install git pre-commit hook to auto-clean CLAUDE.md')
    parser.add_argument('--regenerate-hooks', action='store_true',
                        help='Regenerate Claude Code hooks with correct paths')

    args = parser.parse_args()

    # Handle --install-hook
    if args.install_hook:
        project_path = Path(args.project) if args.project else Path.cwd()
        git_dir = project_path / ".git"
        if not git_dir.exists():
            print("Error: Not a git repository.")
            return

        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        pre_commit = hooks_dir / "pre-commit"

        hook_content = f'''#!/bin/bash
# Memberberries pre-commit hook
# Cleans the memberberries section from CLAUDE.md before committing

CLAUDE_MD="CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
    # Check if CLAUDE.md is staged
    if git diff --cached --name-only | grep -q "^$CLAUDE_MD$"; then
        # Clean the memberberries section
        python3 "{MEMBERBERRIES_DIR}/member.py" --clean --quiet 2>/dev/null
        # Re-stage the cleaned file
        git add "$CLAUDE_MD"
    fi
fi
'''
        # Check if pre-commit already exists
        if pre_commit.exists():
            existing = pre_commit.read_text()
            if "Memberberries" in existing:
                print("Memberberries hook already installed.")
                return
            # Append to existing hook
            with open(pre_commit, 'a') as f:
                f.write("\n" + hook_content)
        else:
            with open(pre_commit, 'w') as f:
                f.write(hook_content)

        os.chmod(pre_commit, 0o755)
        print("✅ Git pre-commit hook installed!")
        print("   CLAUDE.md will be auto-cleaned before each commit.")
        return

    # Handle --regenerate-hooks
    if args.regenerate_hooks:
        project_path = Path(args.project) if args.project else Path.cwd()
        if not ClaudeCodeInstaller.is_installed():
            print("Error: Claude Code is not installed.")
            return

        print(f"Regenerating Claude Code hooks for {project_path}...")
        print(f"  Using memberberries from: {MEMBERBERRIES_DIR}")
        ClaudeCodeInstaller.setup_hooks(project_path)
        print("✅ Hooks regenerated successfully!")
        print("   Hook scripts now use the correct paths.")
        return

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

    # Handle pin command
    if args.task == 'pin':
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        print("\n📌 Pin a New Memory")
        print("="*50)
        print("Pinned memories are protected and always shown.\n")

        name = input("Name (short, memorable): ").strip()
        if not name:
            print("Cancelled - name is required.")
            return

        print("\nCategories: credentials, config, server, api, database, general")
        category = input("Category [general]: ").strip() or "general"

        print("\nEnter the content (can be multi-line, end with empty line):")
        content_lines = []
        while True:
            line = input()
            if not line:
                break
            content_lines.append(line)
        content = "\n".join(content_lines)

        if not content:
            print("Cancelled - content is required.")
            return

        tags_input = input("\nTags (comma-separated, optional): ").strip()
        tags = [t.strip() for t in tags_input.split(",")] if tags_input else []

        sensitive = input("Contains sensitive data? [y/N]: ").strip().lower() == 'y'

        pin = bm.add_pinned_memory(name, content, category, tags, sensitive)
        print(f"\n✅ Pinned memory created!")
        print(f"   ID: {pin['id']}")
        print(f"   Name: {pin['name']}")
        return

    # Handle pins (list) command
    if args.task == 'pins':
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        pinned = bm.get_pinned_memories()
        if not pinned:
            print("\nNo pinned memories found.")
            print("Use 'member pin' to create one.")
            return

        print(f"\n📌 Pinned Memories ({len(pinned)})")
        print("="*60)
        for p in pinned:
            sensitive_marker = " 🔒" if p.get('sensitive') else ""
            print(f"\n[{p['id']}] {p['name']}{sensitive_marker}")
            print(f"  Category: {p['category']}")
            if p.get('tags'):
                print(f"  Tags: {', '.join(p['tags'])}")
            # Show content preview (truncate for display)
            content_preview = p['content'][:100] + "..." if len(p['content']) > 100 else p['content']
            print(f"  Content: {content_preview}")
        print()
        return

    # Handle unpin command
    if args.task and args.task.startswith('unpin'):
        parts = args.task.split(maxsplit=1)
        if len(parts) < 2:
            print("Usage: member unpin <id>")
            print("Use 'member pins' to see available IDs.")
            return

        pin_id = parts[1].strip()
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        # Confirm deletion
        pin = None
        for p in bm.get_pinned_memories():
            if p['id'] == pin_id:
                pin = p
                break

        if not pin:
            print(f"Pinned memory '{pin_id}' not found.")
            print("Use 'member pins' to see available IDs.")
            return

        confirm = input(f"Remove pinned memory '{pin['name']}'? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return

        if bm.unpin_memory(pin_id):
            print(f"✅ Unpinned: {pin['name']}")
        else:
            print("Failed to unpin memory.")
        return

    # Handle task cluster commands
    if args.task and args.task.startswith('task '):
        # Create new task: member task "name"
        task_name = args.task[5:].strip().strip('"\'')
        if not task_name:
            print("Usage: member task \"task name\"")
            return

        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        # Check for --parent flag (simple parsing)
        parent_id = None
        if '--parent' in task_name:
            parts = task_name.split('--parent')
            task_name = parts[0].strip().strip('"\'')
            if len(parts) > 1:
                parent_id = parts[1].strip()

        print(f"\n🎯 Creating Task Cluster: {task_name}")
        description = input("Description (optional): ").strip()

        task_id = bm.create_task_cluster(task_name, description, parent_id)
        print(f"✅ Task cluster created!")
        print(f"   ID: {task_id}")
        print(f"   Name: {task_name}")
        if parent_id:
            print(f"   Parent: {parent_id}")
        print("\nMemories will automatically cluster around this task.")
        return

    if args.task == 'tasks':
        # List all task clusters
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        hierarchy = bm.get_task_hierarchy()
        if not hierarchy:
            print("\nNo task clusters found.")
            print("Use 'member task \"name\"' to create one.")
            return

        print(f"\n🎯 Task Clusters (Gravitational Organization)")
        print("="*60)

        def print_tree(tasks, indent=0):
            for t in tasks:
                mass_bar = "●" * min(t['mass'], 10)
                prefix = "  " * indent
                print(f"{prefix}[{t['id']}] {t['name']}")
                print(f"{prefix}  Mass: {mass_bar} ({t['mass']})")
                print(f"{prefix}  Memories: {t['memory_count']}")
                if t.get('subtasks'):
                    print_tree(t['subtasks'], indent + 1)

        print_tree(hierarchy)
        print()
        return

    if args.task and args.task.startswith('task-show '):
        # Show memories for a task
        task_id = args.task[10:].strip()
        if not task_id:
            print("Usage: member task-show <task_id>")
            return

        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        clusters = bm.index.get("task_clusters", {})
        if task_id not in clusters:
            print(f"Task '{task_id}' not found.")
            print("Use 'member tasks' to see available tasks.")
            return

        cluster = clusters[task_id]
        memories = bm.get_task_memories(task_id)

        print(f"\n🎯 Task: {cluster['name']}")
        print("="*60)
        if cluster.get('description'):
            print(f"Description: {cluster['description']}")
        print(f"Mass: {cluster.get('mass', 1)} | Memories: {len(memories)}")
        print()

        if not memories:
            print("No memories attached to this task yet.")
            print("Memories will auto-cluster as you work.")
        else:
            print("Memories (sorted by gravitational mass):")
            for m in memories[:10]:  # Limit display
                mass = m.get('_gravity_mass', 1)
                problem = m.get('problem', m.get('error_message', 'Unknown'))[:60]
                print(f"  [{mass:.1f}⚫] {problem}")
        print()
        return

    # Handle refresh command - outputs context for Claude to re-read mid-session
    if args.task == 'refresh':
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        manager = ClaudeMDManager(project_path, storage_mode)

        print("\n" + "="*60)
        print("📚 MEMBERBERRIES CONTEXT REFRESH")
        print("="*60)
        print("(Claude: Re-read the following to update your context)\n")

        # Generate and output fresh context
        context = manager.generate_memberberries_section(max_tokens=2000)
        print(context)
        print("\n" + "="*60)
        print("End of context refresh")
        print("="*60)
        return

    # Handle context command - show current CLAUDE.md memberberries section
    if args.task == 'context':
        project_path = Path(args.project) if args.project else Path.cwd()
        claude_md = project_path / "CLAUDE.md"

        if not claude_md.exists():
            print("No CLAUDE.md found.")
            return

        content = claude_md.read_text()
        delimiter = "<!-- MEMBERBERRIES CONTEXT"

        if delimiter in content:
            start = content.find(delimiter)
            print("\n📚 Current Memberberries Context in CLAUDE.md:")
            print("="*60)
            print(content[start:])
        else:
            print("No memberberries section found in CLAUDE.md")
        return

    # Handle feedback command - adjust memory gravity based on usefulness
    if args.task and args.task.startswith('feedback '):
        parts = args.task.split()
        if len(parts) < 3:
            print("Usage: member feedback <memory_id> useful|not-useful")
            return

        memory_id = parts[1]
        feedback = parts[2].lower()

        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        gravity = bm.index.get("memory_gravity", {})

        if memory_id not in gravity:
            gravity[memory_id] = {"mass": 1, "references": 0, "tasks": [], "last_accessed": datetime.now().isoformat()}

        if feedback in ['useful', 'good', 'helpful', '+']:
            gravity[memory_id]["mass"] += 2
            gravity[memory_id]["references"] += 1
            print(f"✅ Memory {memory_id} marked as useful (+2 gravity)")
        elif feedback in ['not-useful', 'bad', 'irrelevant', '-']:
            gravity[memory_id]["mass"] = max(0.1, gravity[memory_id]["mass"] - 1)
            print(f"⬇️ Memory {memory_id} marked as not useful (-1 gravity)")
        else:
            print("Feedback should be 'useful' or 'not-useful'")
            return

        bm.index["memory_gravity"] = gravity
        bm._save_index()
        return

    # Handle lookup command - get full memory content by ID
    if args.task and args.task.startswith('lookup '):
        parts = args.task.split()
        if len(parts) < 2:
            print("Usage: member lookup <memory_id>")
            return

        memory_id = parts[1]
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        # Search across all memory types for matching ID
        found = False
        for mem_type in ['solutions', 'errors', 'preferences', 'antipatterns', 'git_conventions', 'testing', 'api_notes']:
            memories = bm.index.get(mem_type, [])
            for m in memories:
                mem_id = m.get('id', '')
                if mem_id.startswith(memory_id) or memory_id in mem_id:
                    found = True
                    print(f"\n📖 Memory: {mem_id}")
                    print("="*60)
                    print(f"Type: {mem_type}")
                    print(f"Created: {m.get('created_at', 'Unknown')}")
                    if m.get('tags'):
                        print(f"Tags: {', '.join(m['tags'])}")
                    print("-"*60)
                    # Print full content based on type
                    if 'problem' in m:
                        print(f"Problem: {m['problem']}")
                    if 'solution' in m:
                        print(f"Solution: {m['solution']}")
                    if 'error_message' in m:
                        print(f"Error: {m['error_message']}")
                    if 'resolution' in m:
                        print(f"Resolution: {m['resolution']}")
                    if 'content' in m:
                        print(f"Content: {m['content']}")
                    if 'pattern' in m:
                        print(f"Pattern: {m['pattern']}")
                    if 'alternative' in m:
                        print(f"Alternative: {m['alternative']}")
                    if m.get('code_snippet'):
                        print(f"\nCode:\n{m['code_snippet']}")
                    print()

        # Also check pinned
        for p in bm.get_pinned_memories():
            if p.get('id', '').startswith(memory_id) or memory_id in p.get('id', ''):
                found = True
                print(f"\n📌 Pinned Memory: {p.get('id', '')}")
                print("="*60)
                print(f"Name: {p.get('name', 'Unnamed')}")
                print(f"Category: {p.get('category', 'uncategorized')}")
                print(f"Content: {p.get('content', '')}")
                print()

        if not found:
            print(f"No memory found matching ID: {memory_id}")
        return

    # Handle stats command - memory analytics
    if args.task and args.task.startswith('stats'):
        detailed = '--detailed' in args.task or '-d' in args.task
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        print("\n📊 MEMBERBERRIES ANALYTICS")
        print("="*60)

        # Basic stats
        stats = bm.get_stats()
        total = sum(v for v in stats.values() if isinstance(v, int))
        print(f"\n📦 Memory Storage ({total} total)")
        print("-"*40)
        for mem_type, count in sorted(stats.items(), key=lambda x: -x[1] if isinstance(x[1], int) else 0):
            if isinstance(count, int) and count > 0:
                bar = "█" * min(count, 20)
                print(f"  {mem_type:20} {bar} {count}")

        # Gravity distribution
        gravity = bm.index.get("memory_gravity", {})
        if gravity:
            print(f"\n⚫ Gravity Distribution ({len(gravity)} tracked)")
            print("-"*40)

            masses = [g.get("mass", 1) for g in gravity.values()]
            if masses:
                avg_mass = sum(masses) / len(masses)
                max_mass = max(masses)
                min_mass = min(masses)
                print(f"  Average mass: {avg_mass:.2f}")
                print(f"  Range: {min_mass:.2f} - {max_mass:.2f}")

                # Distribution buckets
                low = sum(1 for m in masses if m < 2)
                med = sum(1 for m in masses if 2 <= m < 5)
                high = sum(1 for m in masses if m >= 5)
                print(f"\n  Low gravity (<2):    {'●' * low} {low}")
                print(f"  Medium gravity (2-5): {'●' * med} {med}")
                print(f"  High gravity (≥5):   {'●' * high} {high}")

        # Task clusters
        clusters = bm.index.get("task_clusters", {})
        if clusters:
            print(f"\n🎯 Task Clusters ({len(clusters)})")
            print("-"*40)
            for tid, cluster in sorted(clusters.items(), key=lambda x: -x[1].get("mass", 1)):
                mem_count = len(cluster.get("memories", []))
                mass = cluster.get("mass", 1)
                active = " ← ACTIVE" if bm.index.get("active_task") == tid else ""
                print(f"  [{tid[:8]}] {cluster['name'][:25]:25} mass:{mass:3} memories:{mem_count}{active}")

        # Staleness report
        now = datetime.now()
        stale_count = 0
        for mid, gdata in gravity.items():
            last = gdata.get("last_accessed")
            if last:
                try:
                    days = (now - datetime.fromisoformat(last)).days
                    if days >= 7:
                        stale_count += 1
                except:
                    pass

        if stale_count > 0:
            print(f"\n⏳ Staleness Report")
            print("-"*40)
            print(f"  {stale_count} memories inactive for 7+ days (decaying)")

        # Learned signals
        learned = bm.index.get("learned_signals", {})
        emphasis = learned.get("emphasis", {})
        effective = learned.get("effective", [])
        if emphasis or effective:
            print(f"\n🧠 Adaptive Learning")
            print("-"*40)
            if emphasis:
                top_emphasis = sorted(emphasis.items(), key=lambda x: -x[1])[:5]
                print(f"  Top emphasis words: {', '.join(w for w,_ in top_emphasis)}")
            if effective:
                print(f"  Effective signals: {', '.join(effective[:5])}")

        # Pinned memories
        pinned = bm.get_pinned_memories()
        if pinned:
            print(f"\n📌 Pinned Memories ({len(pinned)})")
            print("-"*40)
            for p in pinned:
                sens = " 🔒" if p.get("sensitive") else ""
                print(f"  [{p['id'][:8]}] {p['name'][:30]}{sens}")

        # Detailed view
        if detailed:
            print(f"\n📋 Detailed Memory List")
            print("-"*40)

            # High gravity memories
            high_grav = bm.get_high_gravity_memories(top_k=10)
            if high_grav:
                print("\nHighest Gravity:")
                for m in high_grav:
                    problem = m.get('problem', m.get('error_message', 'Unknown'))[:50]
                    mass = m.get('_gravity_mass', 1)
                    refs = m.get('_references', 0)
                    print(f"  [{mass:.1f}⚫ {refs}refs] {problem}")

        print("\n" + "="*60)
        return

    # Handle expand command - show all memories in full detail
    if args.task == 'expand':
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        manager = ClaudeMDManager(project_path, storage_mode)

        print("\n" + "="*60)
        print("📖 EXPANDED MEMORY CONTEXT")
        print("="*60)
        print("(Claude: Full detail for all relevant memories)\n")

        # Generate expanded context without token limit
        context = manager.generate_memberberries_section(max_tokens=10000)
        print(context)
        print("\n" + "="*60)
        return

    # Handle config command - manage Memberberries configuration
    if args.task and args.task.startswith('config'):
        parts = args.task.split(maxsplit=2)
        config = ConfigManager()

        if len(parts) == 1:
            # Show current config (redacted)
            print("\n⚙️  MEMBERBERRIES CONFIGURATION")
            print("="*60)
            api_key = config.get_api_key()
            if api_key:
                print(f"Anthropic API Key: {api_key[:8]}...{api_key[-4:]}")
            else:
                print("Anthropic API Key: Not configured")
                print("\nTo enable 'member deep', set your API key:")
                print("  member config api-key sk-ant-...")
            print()
            return

        if parts[1] == 'api-key':
            if len(parts) < 3:
                print("Usage: member config api-key <your-api-key>")
                return
            key = parts[2].strip()
            if not key.startswith('sk-'):
                print("Warning: API key should start with 'sk-'")
            config.set_api_key(key)
            print(f"✅ API key saved: {key[:8]}...{key[-4:]}")
            print("You can now use 'member deep' for AI-powered context retrieval.")
            return

        print(f"Unknown config option: {parts[1]}")
        print("Available options: api-key")
        return

    # Handle update command - pull latest memberberries and regenerate hooks
    if args.task == 'update':
        print("\n📦 Updating memberberries...")

        # Check if running from git repo
        if not (MEMBERBERRIES_DIR / '.git').exists():
            print("❌ Memberberries not installed via git.")
            print(f"   Directory: {MEMBERBERRIES_DIR}")
            print("\nTo update manually:")
            print("  1. Download the latest version")
            print("  2. Replace files in the memberberries directory")
            print("  3. Run: member --regenerate-hooks")
            return

        # Pull latest changes
        print(f"Pulling from {MEMBERBERRIES_DIR}...")
        result = subprocess.run(
            ['git', 'pull'],
            cwd=MEMBERBERRIES_DIR,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ Git pull failed:")
            print(result.stderr)
            return

        if 'Already up to date' in result.stdout:
            print("✅ Already up to date!")
        else:
            print(result.stdout.strip())
            print("✅ Updated successfully!")

        # Regenerate hooks for current project
        project_path = Path(args.project) if args.project else Path.cwd()
        if ClaudeCodeInstaller.is_installed():
            print(f"\nRegenerating hooks for {project_path}...")
            ClaudeCodeInstaller.setup_hooks(project_path)
            print("✅ Hooks regenerated!")

        # Show recent changes hint
        print("\n💡 To see recent changes:")
        print(f"   cd {MEMBERBERRIES_DIR} && git log --oneline -5")
        return

    # Handle clean command - remove low-quality and duplicate memories
    if args.task == 'clean':
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        print("\n🧹 Cleaning memories...")

        # Get low-quality memories
        low_quality = bm.get_memories_needing_refinement()
        if low_quality:
            print(f"\nFound {len(low_quality)} low-quality memories:")
            for mem in low_quality[:5]:  # Show first 5
                print(f"  - `{mem['id']}` ({mem['type']}): {mem['content'][:60]}...")

        # Garbage content patterns to check
        garbage_markers = [
            'stop_reason', 'input_tokens', 'cache_creation',
            'tool_use_id', 'MEMBERBERRIES CONTEXT',
            '}}], ', "': [{'",
        ]

        # Clean each memory type
        removed = 0
        for mem_type in ['solutions', 'errors', 'antipatterns']:
            memories = bm.index.get(mem_type, [])
            original_count = len(memories)

            # Filter out garbage
            clean = []
            for m in memories:
                content = m.get('problem', '') + m.get('solution', '') + m.get('error_message', '') + m.get('resolution', '') + m.get('pattern', '')

                is_garbage = False
                for marker in garbage_markers:
                    if marker in content:
                        is_garbage = True
                        break

                # Also check for excessive special chars
                if len(content) > 20:
                    special_ratio = sum(1 for c in content if c in '{}[]"\':,') / len(content)
                    if special_ratio > 0.15:
                        is_garbage = True

                # Check for line number patterns (stack traces)
                if re.search(r'\d{2,}→', content):
                    is_garbage = True

                if not is_garbage:
                    clean.append(m)

            removed += original_count - len(clean)
            bm.index[mem_type] = clean

        bm._save_index()

        print(f"\n✅ Removed {removed} low-quality memories")

        if low_quality and removed < len(low_quality):
            remaining = len(low_quality) - removed
            print(f"\n💡 {remaining} memories still need refinement.")
            print("   Use `memberberry refine <id>: <better summary>` in conversation")
            print("   to help Claude improve them.")

        return

    # Handle report command - generate bug report with context
    if args.task == 'report':
        import platform
        import sys

        print("\n📋 Generating Memberberries Bug Report...")
        print("=" * 50)

        # System info
        print("\n## System Information\n")
        print(f"- **OS**: {platform.system()} {platform.release()}")
        print(f"- **Python**: {sys.version.split()[0]}")
        print(f"- **Memberberries**: {MEMBERBERRIES_DIR}")

        # Check Claude Code
        claude_installed = ClaudeCodeInstaller.is_installed()
        print(f"- **Claude Code**: {'Installed' if claude_installed else 'Not found'}")

        # Memory stats (anonymized)
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'

        try:
            bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))
            print(f"\n## Memory Statistics\n")
            print(f"- **Solutions**: {len(bm.index.get('solutions', []))}")
            print(f"- **Errors**: {len(bm.index.get('errors', []))}")
            print(f"- **Antipatterns**: {len(bm.index.get('antipatterns', []))}")
            print(f"- **Preferences**: {len(bm.index.get('preferences', []))}")
            print(f"- **Pinned**: {len(bm.index.get('pinned', []))}")

            # Check for low-quality memories
            low_quality = bm.get_memories_needing_refinement()
            if low_quality:
                print(f"- **Low-quality memories**: {len(low_quality)}")
        except Exception as e:
            print(f"\n## Memory Statistics\n")
            print(f"- **Error loading memories**: {type(e).__name__}")

        # Hooks status
        print(f"\n## Hooks Status\n")
        hooks_file = project_path / ".claude" / "settings.json"
        if hooks_file.exists():
            try:
                settings = json.loads(hooks_file.read_text())
                hooks = settings.get('hooks', {})
                print(f"- **PreToolUse hooks**: {len(hooks.get('PreToolUse', []))}")
                print(f"- **PostToolUse hooks**: {len(hooks.get('PostToolUse', []))}")
                print(f"- **Stop hooks**: {len(hooks.get('Stop', []))}")
            except:
                print("- **Error reading hooks config**")
        else:
            print("- **No hooks configured**")

        # Issue template
        print(f"\n## Issue Description\n")
        print("<!-- Describe your issue here -->")
        print("")
        print("### Steps to Reproduce")
        print("1. ")
        print("2. ")
        print("3. ")
        print("")
        print("### Expected Behavior")
        print("<!-- What should happen? -->")
        print("")
        print("### Actual Behavior")
        print("<!-- What actually happened? -->")

        print("\n" + "=" * 50)
        print("\n📋 Copy the above and paste into a new issue at:")
        print("   https://github.com/wylloh/memberberries/issues/new")
        print("\n💡 Tip: Add any error messages or screenshots to help diagnose.")
        return

    # Handle deep command - AI-powered context retrieval
    if args.task and args.task.startswith('deep '):
        task_description = args.task[5:].strip()

        if not task_description:
            print("Usage: member deep \"your task description\"")
            print("\nExamples:")
            print("  member deep \"implement OAuth authentication\"")
            print("  member deep \"fix the database connection timeout\"")
            print("  member deep \"refactor the payment module\" --focus")
            return

        # Check for flags
        set_focus = '--focus' in task_description
        types_filter = None
        if '--types' in task_description:
            # Parse --types errors,solutions
            match = re.search(r'--types\s+([\w,]+)', task_description)
            if match:
                types_filter = match.group(1).split(',')
                task_description = re.sub(r'--types\s+[\w,]+', '', task_description)

        task_description = task_description.replace('--focus', '').strip()

        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        config = ConfigManager()
        api_key = config.get_api_key()

        if not api_key:
            print("❌ Deep scan requires an Anthropic API key.")
            print("\nTo configure:")
            print("  member config api-key sk-ant-...")
            print("\nOr set ANTHROPIC_API_KEY environment variable.")
            return

        if not ANTHROPIC_AVAILABLE:
            print("❌ Anthropic SDK not installed.")
            print("Run: pip install anthropic")
            return

        print(f"\n🔍 Deep scanning memories for: \"{task_description}\"")
        print("-"*60)

        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))
        scanner = DeepScan(api_key, bm)

        try:
            relevant = scanner.scan(task_description, memory_types=types_filter)
        except Exception as e:
            print(f"❌ Deep scan failed: {e}")
            return

        if not relevant:
            print("No highly relevant memories found for this task.")
            return

        print(f"✅ Found {len(relevant)} relevant memories:\n")

        # Display and optionally update CLAUDE.md
        manager = ClaudeMDManager(project_path, storage_mode)

        for mem in relevant:
            mem_type = mem["type"]
            data = mem["data"]
            mem_id = data.get("id", "")[:8]

            if mem_type == "solution":
                print(f"  [{mem_id}] 💡 {data.get('problem', '')[:60]}")
            elif mem_type == "error":
                print(f"  [{mem_id}] ⚠️  {data.get('error_message', '')[:60]}")
            elif mem_type == "preference":
                print(f"  [{mem_id}] ⚙️  [{data.get('category', '')}] {data.get('content', '')[:50]}")
            elif mem_type == "pinned":
                print(f"  [{mem_id}] 📌 {data.get('name', '')}")
            elif mem_type == "antipattern":
                print(f"  [{mem_id}] 🚫 {data.get('pattern', '')[:60]}")

        print()

        # Update CLAUDE.md with deep context
        deep_context = manager._generate_deep_context(relevant, task_description)
        manager.update_claude_md(deep_context)

        print(f"📝 CLAUDE.md updated with task-specific context.")

        if set_focus:
            # Create or update task cluster
            bm.create_task_cluster(task_description[:50], task_description)
            print(f"🎯 Task focus set: {task_description[:50]}")

        print("\nRun 'claude' to start your session with optimized context.")
        return

    # Handle focus command - set active task for session
    if args.task and args.task.startswith('focus'):
        parts = args.task.split(maxsplit=1)
        project_path = Path(args.project) if args.project else Path.cwd()
        storage_mode = 'global' if getattr(args, 'global_storage', False) else 'auto'
        bm = BerryManager(storage_mode=storage_mode, project_path=str(project_path))

        if len(parts) == 1 or parts[1] == '--clear':
            # Clear focus
            if "active_task" in bm.index:
                del bm.index["active_task"]
                bm._save_index()
            print("🎯 Active task focus cleared.")
            return

        task_id = parts[1].strip()
        clusters = bm.index.get("task_clusters", {})

        if task_id not in clusters:
            print(f"Task '{task_id}' not found. Use 'member tasks' to see available tasks.")
            return

        bm.index["active_task"] = task_id
        bm._save_index()

        cluster = clusters[task_id]
        print(f"🎯 Active task set: {cluster['name']}")
        print(f"   ID: {task_id}")
        print("   This task's memories will be prioritized in context.")
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
