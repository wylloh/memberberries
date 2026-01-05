#!/usr/bin/env python3
"""
Memberberries Auto-Concentrate

Processes Claude's berry markers from conversation transcripts.
Simple file I/O - no embeddings, no search algorithms.
"""

import re
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def extract_assistant_text(transcript_path: Path) -> str:
    """Extract the LAST assistant response from a Claude Code transcript.

    Only processing the last message prevents re-capturing markers from
    earlier in the conversation on every hook invocation.
    """
    if not transcript_path.exists():
        return ""

    last_assistant_text = ""
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                msg = json.loads(line)
                # Claude Code nests messages inside msg['message']
                message = msg.get('message', msg)
                if isinstance(message, dict) and message.get('role') == 'assistant':
                    content = message.get('content', '')
                    texts = []
                    if isinstance(content, str):
                        texts.append(content)
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                texts.append(item['text'])
                    if texts:
                        last_assistant_text = "\n\n".join(texts)
    except Exception:
        return ""

    return last_assistant_text


def strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks to avoid capturing example markers."""
    # Remove fenced code blocks (``` ... ```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code (`...`)
    text = re.sub(r'`[^`\n]+`', '', text)
    return text


def parse_berry_markers(text: str) -> List[Dict]:
    """Parse [BERRY #tag1 #tag2] summary patterns."""
    # Strip code blocks to avoid capturing documentation examples
    text = strip_code_blocks(text)

    # Support both [BERRY] and legacy [MEMORY]
    # Summary captures until newline
    pattern = r'\[(?:BERRY|MEMORY)\s+((?:#\w+\s*)+)\]\s*([^\n]+)'
    matches = re.finditer(pattern, text, re.IGNORECASE)

    berries = []
    for match in matches:
        tags = re.findall(r'#(\w+)', match.group(1))
        summary = match.group(2).strip()
        if not summary or not tags:
            continue

        berries.append({
            'id': hashlib.md5(f"{summary}{datetime.now().isoformat()}".encode()).hexdigest()[:8],
            'tags': tags,
            'summary': summary,
            'created': datetime.now().isoformat(),
        })

    return berries


def parse_archive_markers(text: str) -> List[str]:
    """Parse [ARCHIVE id] patterns."""
    pattern = r'\[ARCHIVE\s+([a-f0-9]{8})\]'
    return re.findall(pattern, text, re.IGNORECASE)


def parse_retrieve_markers(text: str) -> List[str]:
    """Parse [RETRIEVE #tag] patterns."""
    pattern = r'\[RETRIEVE\s+#(\w+)\]'
    return re.findall(pattern, text, re.IGNORECASE)


def parse_autoberry_marker(text: str) -> Optional[str]:
    """Parse [AUTOBERRY] checkpoint pattern. Returns the checkpoint text or None."""
    # Strip code blocks to avoid capturing documentation examples
    text = strip_code_blocks(text)

    # Capture everything after [AUTOBERRY] until end of line
    pattern = r'\[AUTOBERRY\]\s*([^\n]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


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


def load_active(project_path: Path) -> List[Dict]:
    """Load active berries from storage (convenience wrapper)."""
    return load_storage(project_path).get("berries", [])


def save_storage(project_path: Path, storage: Dict):
    """Save full storage structure."""
    memberberries_dir = project_path / ".memberberries"
    memberberries_dir.mkdir(parents=True, exist_ok=True)

    active_file = memberberries_dir / "active.json"
    with open(active_file, 'w') as f:
        json.dump(storage, f, indent=2)


def save_active(project_path: Path, berries: List[Dict]):
    """Save active berries to storage (preserves autoberry)."""
    storage = load_storage(project_path)
    storage["berries"] = berries
    save_storage(project_path, storage)


def save_autoberry(project_path: Path, content: str):
    """Save or update the autoberry checkpoint."""
    storage = load_storage(project_path)
    storage["autoberry"] = {
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    save_storage(project_path, storage)


def load_autoberry(project_path: Path) -> Optional[Dict]:
    """Load current autoberry if exists."""
    return load_storage(project_path).get("autoberry")


def archive_berry(project_path: Path, berry: Dict):
    """Move a berry to its archive folder (by primary tag)."""
    if not berry.get('tags'):
        return

    primary_tag = berry['tags'][0]
    archive_dir = project_path / ".memberberries" / "archive" / primary_tag
    archive_dir.mkdir(parents=True, exist_ok=True)

    berry['archived'] = datetime.now().isoformat()
    archive_file = archive_dir / f"{berry['id']}.json"
    with open(archive_file, 'w') as f:
        json.dump(berry, f, indent=2)


def process_transcript(transcript_path: str, project_path: str) -> Dict[str, int]:
    """Process a transcript for berry markers. Main entry point for hooks."""
    transcript_path = Path(transcript_path)
    project_path = Path(project_path) if project_path else Path.cwd()

    text = extract_assistant_text(transcript_path)
    if not text:
        return {'berries': 0, 'archives': 0, 'retrieves': 0, 'autoberry': 0}

    # Parse all markers
    new_berries = parse_berry_markers(text)
    archive_ids = parse_archive_markers(text)
    retrieve_tags = parse_retrieve_markers(text)
    autoberry_content = parse_autoberry_marker(text)

    # Load current active berries
    active = load_active(project_path)
    active_by_id = {b['id']: b for b in active}
    existing_summaries = {b.get('summary', '') for b in active}

    # Add new berries (skip duplicates by summary)
    for berry in new_berries:
        if berry['summary'] not in existing_summaries:
            active.append(berry)
            existing_summaries.add(berry['summary'])

    # Archive requested berries
    archived_count = 0
    for berry_id in archive_ids:
        if berry_id in active_by_id:
            berry = active_by_id[berry_id]
            archive_berry(project_path, berry)
            active = [b for b in active if b['id'] != berry_id]
            archived_count += 1

    # Save updated active list
    save_active(project_path, active)

    # Save autoberry checkpoint if present
    autoberry_saved = 0
    if autoberry_content:
        save_autoberry(project_path, autoberry_content)
        autoberry_saved = 1

    # Store retrieve requests for next sync
    if retrieve_tags:
        retrieve_file = project_path / ".memberberries" / "pending_retrieves.json"
        with open(retrieve_file, 'w') as f:
            json.dump(retrieve_tags, f)

    return {
        'berries': len(new_berries),
        'archives': archived_count,
        'retrieves': len(retrieve_tags),
        'autoberry': autoberry_saved
    }


def main():
    """CLI entry point for the concentrate hook."""
    parser = argparse.ArgumentParser(description='Process berry markers from transcripts')
    parser.add_argument('--transcript', '-t', required=True, help='Path to transcript file')
    parser.add_argument('--project', '-p', help='Project path')

    args = parser.parse_args()
    project_path = args.project or str(Path.cwd())

    result = process_transcript(args.transcript, project_path)

    # Log results (visible in debug log)
    if result['berries'] > 0 or result['archives'] > 0 or result['autoberry'] > 0:
        parts = []
        if result['berries']:
            parts.append(f"{result['berries']} new")
        if result['archives']:
            parts.append(f"{result['archives']} archived")
        if result['autoberry']:
            parts.append("checkpoint saved")
        print(f"🫐 Processed: {', '.join(parts)}")


if __name__ == '__main__':
    main()
