#!/usr/bin/env python3
"""
Berry nudge - gentle reminder after substantive responses.
Only fires when exploration happened but no berries were captured.
"""

import json
import re
import sys
from pathlib import Path


# Tools that suggest discovery/exploration
EXPLORATION_TOOLS = {'Read', 'Grep', 'Glob', 'Task', 'LSP', 'WebFetch', 'WebSearch'}

# Minimum response length to consider substantive
MIN_RESPONSE_LENGTH = 800

# Berry marker pattern
BERRY_PATTERN = re.compile(r'\[BERRY\s+#\w+[^\]]*\]')


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


def should_nudge(tools_used: list[str], assistant_text: str) -> bool:
    """Determine if a gentle nudge is warranted."""
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


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    transcript_path = sys.argv[1]
    tools_used, assistant_text = get_last_exchange(transcript_path)

    if should_nudge(tools_used, assistant_text):
        print("🫐 Anything worth berrying?")


if __name__ == '__main__':
    main()
