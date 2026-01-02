#!/usr/bin/env python3
"""
Memberberries Auto-Concentrate Module

Automatically extracts and stores memories from Claude Code conversations.
Works like meeting minutes - captures insights, solutions, and patterns
without requiring manual entry.
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from berry_manager import BerryManager


class MemoryExtractor:
    """Extracts memories from conversation text."""

    # Patterns that indicate a solution
    SOLUTION_PATTERNS = [
        r"(?:the solution is|to fix this|the fix is|you can solve this by|here's how to|the way to|to resolve this)(.*?)(?:\.|$)",
        r"(?:solved by|fixed by|resolved by|the answer is)(.*?)(?:\.|$)",
        r"(?:you should|you need to|make sure to|remember to)(.*?)(?:\.|$)",
    ]

    # Patterns that indicate an error resolution
    ERROR_PATTERNS = [
        r"(?:error|exception|failed|failure)[\s:]+([^\n]+)",
        r"(?:ModuleNotFoundError|ImportError|TypeError|ValueError|KeyError|AttributeError|RuntimeError)[\s:]+([^\n]+)",
    ]

    # Patterns that indicate antipatterns
    ANTIPATTERN_PATTERNS = [
        r"(?:don't|do not|avoid|never|shouldn't|should not)\s+([^.]+?)(?:\s+because|\s+since|\s+as\s+it|\.)",
        r"(?:instead of|rather than)\s+([^,]+),?\s+(?:use|try|consider)",
    ]

    # Patterns for dependencies/packages
    DEPENDENCY_PATTERNS = [
        r"(?:install|add|use)\s+(?:the\s+)?[`'\"]?(\w+(?:-\w+)*)[`'\"]?\s+(?:package|library|module)",
        r"(?:pip install|npm install|yarn add)\s+([^\s]+)",
        r"(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    ]

    # Common tech keywords for auto-tagging
    TECH_KEYWORDS = {
        'python': ['python', 'pip', 'pytest', 'django', 'flask', 'fastapi', 'asyncio'],
        'javascript': ['javascript', 'js', 'node', 'npm', 'yarn', 'react', 'vue', 'angular'],
        'typescript': ['typescript', 'ts', 'tsx'],
        'database': ['sql', 'postgres', 'mysql', 'mongodb', 'redis', 'database', 'query'],
        'api': ['api', 'rest', 'graphql', 'endpoint', 'request', 'response'],
        'auth': ['auth', 'authentication', 'authorization', 'jwt', 'oauth', 'token', 'password'],
        'testing': ['test', 'testing', 'unittest', 'pytest', 'jest', 'mock'],
        'docker': ['docker', 'container', 'dockerfile', 'compose'],
        'git': ['git', 'commit', 'branch', 'merge', 'push', 'pull'],
        'security': ['security', 'vulnerability', 'xss', 'csrf', 'injection', 'sanitize'],
        'performance': ['performance', 'optimize', 'cache', 'speed', 'slow', 'fast'],
        'error': ['error', 'exception', 'bug', 'fix', 'debug', 'issue'],
    }

    def __init__(self):
        self.extracted_memories = []

    def extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from text based on keywords."""
        text_lower = text.lower()
        tags = set()

        for tag, keywords in self.TECH_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                tags.add(tag)

        return list(tags)[:5]  # Limit to 5 tags

    def extract_solutions(self, text: str) -> List[Dict]:
        """Extract solution patterns from text."""
        solutions = []

        for pattern in self.SOLUTION_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                solution_text = match.group(1).strip() if match.groups() else match.group(0).strip()
                if len(solution_text) > 20:  # Filter out too short matches
                    # Try to find context (what problem this solves)
                    context_start = max(0, match.start() - 200)
                    context = text[context_start:match.start()].strip()

                    # Extract a problem description from context
                    problem = self._extract_problem(context) or "General solution"

                    solutions.append({
                        'type': 'solution',
                        'problem': problem[:200],
                        'solution': solution_text[:500],
                        'tags': self.extract_tags(text[context_start:match.end()])
                    })

        return solutions[:3]  # Limit to prevent spam

    def extract_error_patterns(self, text: str) -> List[Dict]:
        """Extract error patterns and their resolutions."""
        errors = []

        for pattern in self.ERROR_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                error_msg = match.group(1).strip() if match.groups() else match.group(0).strip()

                # Look for resolution after the error
                after_error = text[match.end():match.end() + 500]
                resolution = self._extract_resolution(after_error)

                if resolution and len(error_msg) > 10:
                    errors.append({
                        'type': 'error',
                        'error_message': error_msg[:200],
                        'resolution': resolution[:500],
                        'tags': self.extract_tags(error_msg + " " + resolution)
                    })

        return errors[:2]  # Limit

    def extract_antipatterns(self, text: str) -> List[Dict]:
        """Extract antipatterns from text."""
        antipatterns = []

        for pattern in self.ANTIPATTERN_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                bad_pattern = match.group(1).strip()

                # Look for the reason and alternative
                context = text[match.start():match.end() + 300]
                reason = self._extract_reason(context)
                alternative = self._extract_alternative(context)

                if len(bad_pattern) > 10 and (reason or alternative):
                    antipatterns.append({
                        'type': 'antipattern',
                        'pattern': bad_pattern[:200],
                        'reason': reason or "Not recommended",
                        'alternative': alternative or "See context",
                        'tags': self.extract_tags(context)
                    })

        return antipatterns[:2]  # Limit

    def _extract_problem(self, context: str) -> Optional[str]:
        """Try to extract a problem description from context."""
        # Look for question patterns
        question_match = re.search(r'(?:how (?:do|can|to)|what|why|when)[^?]*\?', context, re.IGNORECASE)
        if question_match:
            return question_match.group(0).strip()

        # Look for "I need to" or "trying to" patterns
        need_match = re.search(r'(?:i need to|trying to|want to|need help with)([^.]+)', context, re.IGNORECASE)
        if need_match:
            return need_match.group(1).strip()

        return None

    def _extract_resolution(self, text: str) -> Optional[str]:
        """Extract resolution from text following an error."""
        # Look for fix/solution indicators
        fix_match = re.search(r'(?:to fix|solution|resolve|try|use|change|update|install)([^.]+\.)', text, re.IGNORECASE)
        if fix_match:
            return fix_match.group(0).strip()
        return None

    def _extract_reason(self, text: str) -> Optional[str]:
        """Extract reason from antipattern context."""
        reason_match = re.search(r'(?:because|since|as it|this causes|leads to|results in)([^.]+)', text, re.IGNORECASE)
        if reason_match:
            return reason_match.group(1).strip()
        return None

    def _extract_alternative(self, text: str) -> Optional[str]:
        """Extract alternative from antipattern context."""
        alt_match = re.search(r'(?:instead|use|try|prefer|better to|should)([^.]+)', text, re.IGNORECASE)
        if alt_match:
            return alt_match.group(1).strip()
        return None

    def extract_all(self, text: str) -> List[Dict]:
        """Extract all types of memories from text."""
        memories = []
        memories.extend(self.extract_solutions(text))
        memories.extend(self.extract_error_patterns(text))
        memories.extend(self.extract_antipatterns(text))
        return memories


class AutoConcentrator:
    """Automatically concentrates memories from conversations."""

    def __init__(self, project_path: str = None, storage_mode: str = 'auto'):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.bm = BerryManager(storage_mode=storage_mode, project_path=str(self.project_path))
        self.extractor = MemoryExtractor()

    def process_transcript(self, transcript_path: str, last_n_messages: int = 5) -> List[Dict]:
        """Process a Claude Code transcript file and extract memories.

        Args:
            transcript_path: Path to the .jsonl transcript file
            last_n_messages: Number of recent messages to analyze

        Returns:
            List of extracted and stored memories
        """
        transcript_path = Path(transcript_path)
        if not transcript_path.exists():
            return []

        # Read the transcript (JSONL format)
        messages = []
        try:
            with open(transcript_path, 'r') as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))
        except Exception as e:
            return []

        # Get the last N messages
        recent_messages = messages[-last_n_messages:] if len(messages) > last_n_messages else messages

        # Extract text content from messages
        conversation_text = self._extract_text_from_messages(recent_messages)

        # Extract memories
        extracted = self.extractor.extract_all(conversation_text)

        # Store extracted memories
        stored = self._store_memories(extracted)

        return stored

    def process_text(self, text: str) -> List[Dict]:
        """Process raw text and extract memories.

        Args:
            text: Conversation text to analyze

        Returns:
            List of extracted and stored memories
        """
        extracted = self.extractor.extract_all(text)
        stored = self._store_memories(extracted)
        return stored

    def _extract_text_from_messages(self, messages: List[Dict]) -> str:
        """Extract text content from message objects."""
        texts = []

        for msg in messages:
            # Handle different message formats
            if isinstance(msg, dict):
                # Try common message structures
                if 'content' in msg:
                    content = msg['content']
                    if isinstance(content, str):
                        texts.append(content)
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                texts.append(item['text'])
                            elif isinstance(item, str):
                                texts.append(item)
                elif 'text' in msg:
                    texts.append(msg['text'])
                elif 'message' in msg:
                    texts.append(str(msg['message']))

        return "\n\n".join(texts)

    def _store_memories(self, memories: List[Dict]) -> List[Dict]:
        """Store extracted memories in the berry manager."""
        stored = []

        for memory in memories:
            try:
                if memory['type'] == 'solution':
                    self.bm.add_solution(
                        problem=memory['problem'],
                        solution=memory['solution'],
                        tags=memory.get('tags', []),
                        code_snippet=None
                    )
                    stored.append(memory)

                elif memory['type'] == 'error':
                    self.bm.add_error(
                        error_message=memory['error_message'],
                        resolution=memory['resolution'],
                        context="Auto-extracted from conversation",
                        tags=memory.get('tags', [])
                    )
                    stored.append(memory)

                elif memory['type'] == 'antipattern':
                    self.bm.add_antipattern(
                        pattern=memory['pattern'],
                        reason=memory['reason'],
                        alternative=memory['alternative'],
                        tags=memory.get('tags', [])
                    )
                    stored.append(memory)

            except Exception as e:
                # Silently skip failed extractions
                pass

        return stored


def main():
    """CLI for testing auto-concentrate."""
    import argparse

    parser = argparse.ArgumentParser(description='Auto-concentrate memories from text')
    parser.add_argument('--transcript', '-t', help='Path to transcript file')
    parser.add_argument('--text', help='Raw text to analyze')
    parser.add_argument('--project', '-p', help='Project path')
    parser.add_argument('--dry-run', action='store_true', help='Extract but do not store')

    args = parser.parse_args()

    concentrator = AutoConcentrator(project_path=args.project)

    if args.transcript:
        if args.dry_run:
            extractor = MemoryExtractor()
            with open(args.transcript, 'r') as f:
                text = f.read()
            memories = extractor.extract_all(text)
        else:
            memories = concentrator.process_transcript(args.transcript)

        print(f"Extracted {len(memories)} memories:")
        for m in memories:
            print(f"  - [{m['type']}] {list(m.values())[1][:50]}...")

    elif args.text:
        if args.dry_run:
            extractor = MemoryExtractor()
            memories = extractor.extract_all(args.text)
        else:
            memories = concentrator.process_text(args.text)

        print(f"Extracted {len(memories)} memories:")
        for m in memories:
            print(f"  - [{m['type']}] {list(m.values())[1][:50]}...")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
