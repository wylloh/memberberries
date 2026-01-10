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

# Berry marker patterns (both structured and freeform)
BERRY_PATTERN = re.compile(r'\[BERRY[:\s][^\]]*\]', re.IGNORECASE)
AUTOBERRY_PATTERN = re.compile(r'\[AUTOBERRY\]', re.IGNORECASE)

# Trigger phrases that suggest berry-worthy insights
# When Claude says these but doesn't berry, we nudge with a specific suggestion
TRIGGER_PATTERNS = [
    # Discovery triggers → suggest gotcha or pattern
    (re.compile(r"I (?:just )?(?:discovered|found|learned|realized|noticed) (?:that )?", re.IGNORECASE), "gotcha"),
    (re.compile(r"(?:It turns out|Turns out|Interestingly|Surprisingly)", re.IGNORECASE), "gotcha"),
    (re.compile(r"The (?:issue|problem|bug|error) (?:is|was) ", re.IGNORECASE), "gotcha"),

    # Preference triggers → suggest preference
    (re.compile(r"(?:The user|You) (?:prefer|want|like|need)s? ", re.IGNORECASE), "preference"),
    (re.compile(r"(?:They|You) (?:mentioned|said|indicated|specified) ", re.IGNORECASE), "preference"),
    (re.compile(r"(?:Your|Their) preference ", re.IGNORECASE), "preference"),

    # Decision triggers → suggest decision
    (re.compile(r"(?:I |We )?(?:chose|decided|went with|opted for|picked) ", re.IGNORECASE), "decision"),
    (re.compile(r"(?:I |We )?(?:recommend|suggest)(?:ing|ed)? (?:using |that )?", re.IGNORECASE), "decision"),
    (re.compile(r"(?:The reason|This is because|Because) ", re.IGNORECASE), "decision"),

    # Rule/pattern triggers → suggest rule or pattern
    (re.compile(r"(?:Always|Never|Must|Should always|Should never) ", re.IGNORECASE), "rule"),
    (re.compile(r"(?:The pattern|The convention|The standard) (?:is|here) ", re.IGNORECASE), "pattern"),
    (re.compile(r"(?:This codebase|This project|This repo) (?:uses|follows|requires) ", re.IGNORECASE), "pattern"),

    # Architecture triggers → suggest architecture
    (re.compile(r"(?:The architecture|The structure|The system) ", re.IGNORECASE), "architecture"),
    (re.compile(r"(?:communicates? with|connects? to|depends? on|calls?) ", re.IGNORECASE), "architecture"),
]


def detect_trigger_phrases(text: str) -> list[tuple[str, str]]:
    """Detect trigger phrases in text.

    Returns list of (matched_phrase, suggested_type) tuples.
    """
    matches = []
    for pattern, suggested_type in TRIGGER_PATTERNS:
        match = pattern.search(text)
        if match:
            # Get some context around the match
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 50)
            context = text[start:end].replace('\n', ' ').strip()
            if len(context) > 60:
                context = context[:57] + "..."
            matches.append((context, suggested_type))
    return matches


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


def should_nudge_berry(tools_used: list[str], assistant_text: str) -> tuple[bool, list[tuple[str, str]]]:
    """Determine if a berry nudge is warranted.

    Returns (should_nudge, trigger_matches) where trigger_matches is a list of
    (context, suggested_type) tuples from detected trigger phrases.
    """
    # Already berried? No nudge needed
    if BERRY_PATTERN.search(assistant_text):
        return False, []

    # Check for trigger phrases first (most specific nudge)
    triggers = detect_trigger_phrases(assistant_text)

    # Check for exploration tools
    exploration_count = len(set(tools_used) & EXPLORATION_TOOLS)

    # Check for substantive length
    text_length = len(assistant_text)

    # Nudge criteria (discovery-focused):
    # 1. Trigger phrases detected (regardless of tools)
    # 2. Multiple exploration tools used (deep dive)
    # 3. Single exploration + long response (investigation with analysis)
    if triggers:
        return True, triggers
    if exploration_count >= 2:
        return True, []
    if exploration_count >= 1 and text_length >= MIN_RESPONSE_LENGTH:
        return True, []

    return False, []


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
    should_nudge, triggers = should_nudge_berry(tools_used, assistant_text)
    if should_nudge:
        if triggers:
            # Specific nudge based on detected trigger phrase
            # Use the first trigger as the primary suggestion
            context, suggested_type = triggers[0]
            print(f"🫐 Berry this {suggested_type}? `[BERRY:{suggested_type}]`")
        else:
            # Generic nudge for exploration without trigger phrases
            print("🫐 Anything worth berrying?")


if __name__ == '__main__':
    main()
