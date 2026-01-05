#!/usr/bin/env python3
"""
Berry nudge - gentle reminder after substantive responses.
Only fires when exploration happened but no berries were captured.
Also handles autoberry checkpoint timing.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


# Tools that suggest discovery/exploration
EXPLORATION_TOOLS = {'Read', 'Grep', 'Glob', 'Task', 'LSP', 'WebFetch', 'WebSearch'}

# Tools that suggest substantive work (for autoberry timing)
WORK_TOOLS = {'Edit', 'Write', 'Bash', 'NotebookEdit'} | EXPLORATION_TOOLS

# Minimum response length to consider substantive
MIN_RESPONSE_LENGTH = 800

# Autoberry timing: nudge after this many minutes of active work
AUTOBERRY_INTERVAL_MINUTES = 15

# Berry marker patterns
BERRY_PATTERN = re.compile(r'\[BERRY\s+#\w+[^\]]*\]')
AUTOBERRY_PATTERN = re.compile(r'\[AUTOBERRY\]')


def get_last_exchange(transcript_path: str) -> tuple[list[str], str]:
    """
    Extract tools used and assistant text from the last exchange.
    Returns (tools_used, assistant_text).
    """
    path = Path(transcript_path)
    if not path.exists():
        return [], ""

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, IOError):
        return [], ""

    messages = data if isinstance(data, list) else data.get('messages', [])

    # Find the last assistant message
    tools_used = []
    assistant_text = ""

    for msg in reversed(messages):
        role = msg.get('role', '')

        if role == 'assistant':
            content = msg.get('content', [])
            if isinstance(content, str):
                assistant_text = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get('type') == 'text':
                            assistant_text += block.get('text', '')
                        elif block.get('type') == 'tool_use':
                            tools_used.append(block.get('name', ''))
            break

    return tools_used, assistant_text


def should_nudge_berry(tools_used: list[str], assistant_text: str) -> bool:
    """Determine if a berry nudge is warranted."""
    # Already berried? No nudge needed
    if BERRY_PATTERN.search(assistant_text):
        return False

    # Check for exploration tools
    exploration_count = len(set(tools_used) & EXPLORATION_TOOLS)

    # Check for substantive length
    text_length = len(assistant_text)

    # Nudge criteria (discovery-focused):
    # - Multiple exploration tools used (deep dive)
    # - Single exploration + long response (investigation with analysis)
    # Pure explanations without exploration don't trigger nudge
    if exploration_count >= 2:
        return True
    if exploration_count >= 1 and text_length >= MIN_RESPONSE_LENGTH:
        return True

    return False


def get_project_path_from_transcript(transcript_path: str) -> Path:
    """Infer project path from transcript location.

    Transcripts are typically at ~/.claude/projects/<hash>/...
    We need to find the actual project from this.
    """
    # Try to find .memberberries in parent directories
    path = Path(transcript_path).resolve()
    for parent in path.parents:
        if (parent / ".memberberries").exists():
            return parent
    return Path.cwd()


def load_autoberry_state(project_path: Path) -> dict:
    """Load autoberry state including last checkpoint and last nudge time."""
    active_file = project_path / ".memberberries" / "active.json"
    nudge_file = project_path / ".memberberries" / "autoberry_nudge.json"

    state = {
        "last_checkpoint": None,
        "last_nudge": None
    }

    # Get last checkpoint time from active.json
    if active_file.exists():
        try:
            with open(active_file, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("autoberry"):
                state["last_checkpoint"] = data["autoberry"].get("timestamp")
        except Exception:
            pass

    # Get last nudge time
    if nudge_file.exists():
        try:
            with open(nudge_file, 'r') as f:
                state["last_nudge"] = json.load(f).get("timestamp")
        except Exception:
            pass

    return state


def save_autoberry_nudge_time(project_path: Path):
    """Record that we nudged for an autoberry."""
    nudge_file = project_path / ".memberberries" / "autoberry_nudge.json"
    try:
        with open(nudge_file, 'w') as f:
            json.dump({"timestamp": datetime.now().isoformat()}, f)
    except Exception:
        pass


def should_nudge_autoberry(tools_used: list[str], assistant_text: str, project_path: Path) -> bool:
    """Determine if an autoberry checkpoint nudge is warranted."""
    # Already wrote an autoberry? No nudge needed
    if AUTOBERRY_PATTERN.search(assistant_text):
        return False

    # Check if substantive work happened
    work_count = len(set(tools_used) & WORK_TOOLS)
    if work_count == 0:
        return False

    # Check timing
    state = load_autoberry_state(project_path)
    now = datetime.now()

    # Determine reference time (last checkpoint, last nudge, or None)
    reference_time = None
    for ts_str in [state.get("last_checkpoint"), state.get("last_nudge")]:
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str)
                if reference_time is None or ts > reference_time:
                    reference_time = ts
            except Exception:
                pass

    # If no reference time, this is the first session - don't nudge immediately
    if reference_time is None:
        # But do track that we've started (save a nudge time to establish baseline)
        save_autoberry_nudge_time(project_path)
        return False

    # Check if enough time has passed
    elapsed_minutes = (now - reference_time).total_seconds() / 60
    if elapsed_minutes >= AUTOBERRY_INTERVAL_MINUTES:
        return True

    return False


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    transcript_path = sys.argv[1]
    project_path = Path(sys.argv[2]) if len(sys.argv) > 2 else get_project_path_from_transcript(transcript_path)

    tools_used, assistant_text = get_last_exchange(transcript_path)

    # Check for autoberry nudge first (higher priority)
    if should_nudge_autoberry(tools_used, assistant_text, project_path):
        save_autoberry_nudge_time(project_path)
        print("⏰ Time for a checkpoint! Write an `[AUTOBERRY]` with your current task state.")
        return

    # Check for regular berry nudge
    if should_nudge_berry(tools_used, assistant_text):
        print("🫐 Anything worth berrying?")


if __name__ == '__main__':
    main()
