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
    """Extracts memories from conversation text.

    Includes adaptive learning to detect user-specific communication patterns.
    """

    # === SEMANTIC SIGNALS ===
    # These indicate important moments worth capturing

    # Signals that a request/need is being expressed
    REQUEST_SIGNALS = [
        'please', 'help me', 'how do i', 'how can i', 'can you', 'could you',
        'i need', 'i want', 'trying to', 'looking for', 'wondering how'
    ]

    # Signals that something is being repeated (should have been remembered!)
    REPETITION_SIGNALS = [
        'again', 'still', 'keep getting', 'keeps happening', 'every time',
        'always forget', 'remind me', 'one more time', 'as i mentioned',
        'like before', 'same issue', 'recurring'
    ]

    # Signals that a solution worked (high-value memories)
    SUCCESS_SIGNALS = [
        'that worked', 'works now', 'fixed it', 'solved', 'perfect',
        'thanks', 'thank you', 'got it', 'makes sense', 'understood',
        'exactly what i needed', 'great'
    ]

    # Signals of failure/problems (learning opportunities)
    FAILURE_SIGNALS = [
        "doesn't work", "not working", "didn't work", 'broke', 'broken',
        'wrong', 'failed', 'failing', 'error', 'issue', 'problem',
        'stuck', 'confused'
    ]

    # Signals of new learning (worth storing)
    LEARNING_SIGNALS = [
        "i didn't know", "til", "today i learned", "good to know",
        "interesting", "never knew", "new to me", 'discovered',
        "that's useful", 'noted'
    ]

    # Signals of best practices/conventions
    BEST_PRACTICE_SIGNALS = [
        'always', 'never', 'should', "shouldn't", 'must', "mustn't",
        'avoid', 'recommended', 'best practice', 'convention',
        'prefer', 'important to', 'make sure', 'remember to'
    ]

    # Signals of emphasis (explicit memory requests)
    EMPHASIS_SIGNALS = [
        'important', 'critical', 'crucial', "don't forget", 'remember',
        'note that', 'key thing', 'essential', 'vital', 'must remember'
    ]

    # === EXTRACTION PATTERNS ===

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

    def __init__(self, berry_manager: 'BerryManager' = None):
        self.extracted_memories = []
        self.bm = berry_manager  # For adaptive learning

    def detect_emphasis_patterns(self, text: str) -> List[str]:
        """Detect words that appear to be emphasized by the user.

        Looks for:
        - ALL CAPS words
        - Words followed by exclamation marks
        - Words in asterisks or underscores
        - Repeated words within a short span
        """
        emphasized = []

        # ALL CAPS words (3+ letters, not common acronyms)
        caps_pattern = r'\b([A-Z]{3,})\b'
        common_acronyms = {'API', 'URL', 'HTTP', 'HTML', 'CSS', 'SQL', 'JSON', 'XML', 'SDK', 'CLI'}
        for match in re.finditer(caps_pattern, text):
            word = match.group(1)
            if word not in common_acronyms:
                emphasized.append(word.lower())

        # Words before exclamation marks
        exclaim_pattern = r'(\w+)!'
        for match in re.finditer(exclaim_pattern, text):
            emphasized.append(match.group(1).lower())

        # Words in emphasis markers (*word*, _word_, **word**)
        emphasis_markers = [
            r'\*\*(\w+)\*\*',  # **bold**
            r'\*(\w+)\*',      # *italic*
            r'_(\w+)_',        # _underline_
        ]
        for pattern in emphasis_markers:
            for match in re.finditer(pattern, text):
                emphasized.append(match.group(1).lower())

        # Detect repeated words within close proximity (sign of emphasis)
        words = text.lower().split()
        word_positions = {}
        for i, word in enumerate(words):
            if len(word) > 3:  # Skip short words
                word = re.sub(r'[^\w]', '', word)
                if word in word_positions:
                    # If same word appears within 10 words, it's emphasized
                    if i - word_positions[word] < 10:
                        emphasized.append(word)
                word_positions[word] = i

        return list(set(emphasized))

    def learn_from_text(self, text: str):
        """Learn user-specific signal words from their communication.

        Analyzes text for emphasis patterns and updates the learning model.
        """
        if not self.bm:
            return

        # Detect emphasis patterns
        emphasized = self.detect_emphasis_patterns(text)
        for word in emphasized:
            self.bm.learn_signal(word, "emphasis", weight=1)

        # Track word frequencies for repetition learning
        words = text.lower().split()
        word_counts = {}
        for word in words:
            word = re.sub(r'[^\w]', '', word)
            if len(word) > 4:  # Skip short words
                word_counts[word] = word_counts.get(word, 0) + 1

        # Learn words that appear frequently in this text
        for word, count in word_counts.items():
            if count >= 3:  # Appeared 3+ times in this message
                self.bm.learn_signal(word, "repeated", weight=count // 3)

    def _smart_truncate(self, text: str, max_len: int = 500) -> str:
        """Truncate text intelligently, preserving complete thoughts.

        Instead of cutting mid-word/sentence, finds natural break points.
        """
        if len(text) <= max_len:
            return text

        # Look for natural break points before max_len
        break_chars = ['. ', '! ', '? ', '; ', ', ', ' - ', '\n']
        best_break = max_len

        # Find the last natural break before max_len
        for char in break_chars:
            idx = text.rfind(char, 0, max_len)
            if idx != -1 and idx > max_len * 0.6:  # At least 60% of content
                best_break = idx + len(char)
                break

        # If no good break found, break at word boundary
        if best_break == max_len:
            space_idx = text.rfind(' ', 0, max_len)
            if space_idx > max_len * 0.6:
                best_break = space_idx

        return text[:best_break].strip() + "..."

    def _compress_to_shorthand(self, text: str) -> str:
        """Compress text using intelligent shorthand while preserving meaning.

        Uses common abbreviations and removes filler words.
        """
        # Common abbreviations
        abbrevs = {
            'function': 'fn',
            'variable': 'var',
            'parameter': 'param',
            'configuration': 'config',
            'application': 'app',
            'directory': 'dir',
            'repository': 'repo',
            'environment': 'env',
            'development': 'dev',
            'production': 'prod',
            'authentication': 'auth',
            'authorization': 'authz',
            'database': 'db',
            'information': 'info',
            'documentation': 'docs',
            'implementation': 'impl',
            'specification': 'spec',
            'requirements': 'reqs',
            'dependencies': 'deps',
            'dependency': 'dep',
            'component': 'comp',
            'components': 'comps',
            'interface': 'iface',
            'initialize': 'init',
            'initialization': 'init',
            'administrator': 'admin',
            'management': 'mgmt',
            'message': 'msg',
            'messages': 'msgs',
            'response': 'resp',
            'request': 'req',
            'execute': 'exec',
            'command': 'cmd',
            'commands': 'cmds',
            'reference': 'ref',
            'attribute': 'attr',
            'attributes': 'attrs',
            'property': 'prop',
            'properties': 'props',
            'expression': 'expr',
            'argument': 'arg',
            'arguments': 'args',
            'maximum': 'max',
            'minimum': 'min',
            'number': 'num',
            'string': 'str',
            'integer': 'int',
            'boolean': 'bool',
            'character': 'char',
            'temporary': 'tmp',
            'source': 'src',
            'destination': 'dest',
            'previous': 'prev',
            'current': 'curr',
            'original': 'orig',
            'package': 'pkg',
            'packages': 'pkgs',
            'version': 'ver',
            'utility': 'util',
            'utilities': 'utils',
            'library': 'lib',
            'libraries': 'libs',
            'object': 'obj',
            'objects': 'objs',
            'index': 'idx',
            'buffer': 'buf',
            'buffer': 'buf',
            'context': 'ctx',
            'navigation': 'nav',
            'button': 'btn',
            'image': 'img',
            'javascript': 'JS',
            'typescript': 'TS',
            'python': 'py',
            'because': 'b/c',
            'without': 'w/o',
            'with': 'w/',
            'approximately': '~',
            'greater than': '>',
            'less than': '<',
        }

        # Filler words to remove (carefully - only when they don't add meaning)
        filler_words = [
            'actually', 'basically', 'essentially', 'literally',
            'just', 'simply', 'really', 'very', 'quite',
        ]

        result = text

        # Apply abbreviations (case-insensitive, preserve casing)
        for full, short in abbrevs.items():
            pattern = re.compile(re.escape(full), re.IGNORECASE)
            result = pattern.sub(short, result)

        # Remove filler words (only at word boundaries)
        for filler in filler_words:
            pattern = re.compile(r'\b' + filler + r'\b\s*', re.IGNORECASE)
            result = pattern.sub('', result)

        # Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    def detect_signals(self, text: str) -> Dict[str, bool]:
        """Detect which semantic signals are present in the text."""
        text_lower = text.lower()
        return {
            'request': any(s in text_lower for s in self.REQUEST_SIGNALS),
            'repetition': any(s in text_lower for s in self.REPETITION_SIGNALS),
            'success': any(s in text_lower for s in self.SUCCESS_SIGNALS),
            'failure': any(s in text_lower for s in self.FAILURE_SIGNALS),
            'learning': any(s in text_lower for s in self.LEARNING_SIGNALS),
            'best_practice': any(s in text_lower for s in self.BEST_PRACTICE_SIGNALS),
            'emphasis': any(s in text_lower for s in self.EMPHASIS_SIGNALS),
        }

    def calculate_importance(self, text: str) -> int:
        """Calculate importance score (0-10) based on signals present.

        Now includes adaptive learning: user-specific emphasized words
        boost the importance score.
        """
        signals = self.detect_signals(text)
        score = 0

        # High importance signals
        if signals['repetition']:
            score += 3  # This was forgotten before - must remember!
        if signals['emphasis']:
            score += 2  # Explicitly marked as important
        if signals['success']:
            score += 2  # Confirmed working solution

        # Medium importance signals
        if signals['failure']:
            score += 1  # Learning opportunity
        if signals['learning']:
            score += 1  # New knowledge
        if signals['best_practice']:
            score += 1  # Worth following

        # Adaptive learning boost: check for learned signal words
        if self.bm:
            words = text.lower().split()
            for word in words:
                word = re.sub(r'[^\w]', '', word)
                learned_score = self.bm.get_signal_score(word)
                if learned_score > 0:
                    score += min(learned_score, 2)  # Cap per-word boost

        return min(score, 10)

    def _is_garbage_content(self, text: str) -> bool:
        """Check if text is garbage (raw JSON, API responses, etc.)."""
        garbage_markers = [
            "{'model':", "'type': 'msg'", "'role': 'assistant'",
            '"model":', '"type": "message"', '"role": "assistant"',
            '<', '</', 'claude-opus', 'claude-sonnet',
            'msg_01', '{"id":', 'noreply@anthropic',
        ]
        return any(marker in text for marker in garbage_markers)

    def extract_user_needs(self, text: str) -> List[Dict]:
        """Extract user needs/requests from 'please' and request patterns."""
        needs = []
        text_lower = text.lower()

        # Look for request patterns
        request_patterns = [
            r"(?:please|help me|can you|could you)\s+([^.?!]+)[.?!]?",
            r"(?:i need|i want|trying to)\s+([^.?!]+)[.?!]?",
            r"(?:how do i|how can i)\s+([^.?!]+)\??",
        ]

        for pattern in request_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                need = match.group(1).strip()
                # Skip garbage content and too-short matches
                if len(need) > 10 and not self._is_garbage_content(need):
                    # Smart truncation: preserve complete sentences/phrases
                    truncated = self._smart_truncate(need, max_len=500)
                    needs.append({
                        'type': 'user_need',
                        'need': truncated,
                        'tags': self.extract_tags(need),
                        'importance': self.calculate_importance(text)
                    })

        return needs[:3]

    def extract_forgotten_items(self, text: str) -> List[Dict]:
        """Extract things that were repeated (should have been remembered)."""
        forgotten = []
        text_lower = text.lower()

        # Look for repetition indicators
        repetition_patterns = [
            r"(?:again|still|keep getting|keeps happening)\s*[,:]?\s*([^.!?]+)[.!?]?",
            r"(?:same|recurring)\s+(?:issue|problem|error)[:\s]+([^.!?]+)[.!?]?",
            r"(?:as i mentioned|like before)[,:]?\s*([^.!?]+)[.!?]?",
        ]

        for pattern in repetition_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                item = match.group(1).strip()
                # Skip garbage content
                if len(item) > 10 and not self._is_garbage_content(item):
                    # Smart truncation with larger limit for forgotten items (high value)
                    truncated = self._smart_truncate(item, max_len=600)
                    forgotten.append({
                        'type': 'forgotten_item',
                        'description': truncated,
                        'tags': self.extract_tags(item),
                        'importance': 10  # High priority - should have been remembered!
                    })

        return forgotten[:2]

    def extract_confirmed_solutions(self, text: str) -> List[Dict]:
        """Extract solutions that were confirmed to work."""
        confirmed = []

        # Look for success + solution patterns
        success_patterns = [
            r"(?:that worked|works now|fixed it|solved)[.!]?\s*([^.!?]*(?:by|with|using)[^.!?]+)[.!?]?",
            r"(?:perfect|exactly what i needed)[.!]?\s*([^.!?]+)[.!?]?",
        ]

        for pattern in success_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                solution = match.group(1).strip() if match.groups() else ""
                if len(solution) > 10:
                    # Larger limit for confirmed solutions - they're valuable
                    truncated = self._smart_truncate(solution, max_len=800)
                    confirmed.append({
                        'type': 'confirmed_solution',
                        'solution': truncated,
                        'tags': self.extract_tags(solution),
                        'importance': 8  # High value - confirmed working
                    })

        return confirmed[:2]

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
                    context_start = max(0, match.start() - 300)
                    context = text[context_start:match.start()].strip()

                    # Extract a problem description from context
                    problem = self._extract_problem(context) or "General solution"
                    problem = self._smart_truncate(problem, max_len=300)
                    solution_truncated = self._smart_truncate(solution_text, max_len=800)

                    solutions.append({
                        'type': 'solution',
                        'problem': problem,
                        'solution': solution_truncated,
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
                after_error = text[match.end():match.end() + 800]
                resolution = self._extract_resolution(after_error)

                if resolution and len(error_msg) > 10:
                    error_truncated = self._smart_truncate(error_msg, max_len=400)
                    resolution_truncated = self._smart_truncate(resolution, max_len=800)
                    errors.append({
                        'type': 'error',
                        'error_message': error_truncated,
                        'resolution': resolution_truncated,
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
                context = text[match.start():match.end() + 500]
                reason = self._extract_reason(context)
                alternative = self._extract_alternative(context)

                if len(bad_pattern) > 10 and (reason or alternative):
                    pattern_truncated = self._smart_truncate(bad_pattern, max_len=300)
                    reason_truncated = self._smart_truncate(reason, max_len=300) if reason else "Not recommended"
                    alt_truncated = self._smart_truncate(alternative, max_len=300) if alternative else "See context"
                    antipatterns.append({
                        'type': 'antipattern',
                        'pattern': pattern_truncated,
                        'reason': reason_truncated,
                        'alternative': alt_truncated,
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
        """Extract all types of memories from text using semantic signals."""
        memories = []

        # Signal-based extractions (highest priority)
        memories.extend(self.extract_forgotten_items(text))      # "again" - must remember!
        memories.extend(self.extract_confirmed_solutions(text))  # "that worked" - high value
        memories.extend(self.extract_user_needs(text))           # "please" - user's goals

        # Pattern-based extractions
        memories.extend(self.extract_solutions(text))
        memories.extend(self.extract_error_patterns(text))
        memories.extend(self.extract_antipatterns(text))

        # Sort by importance (highest first)
        memories.sort(key=lambda m: m.get('importance', 0), reverse=True)

        return memories


class AutoConcentrator:
    """Automatically concentrates memories from conversations.

    Includes adaptive learning to improve memory extraction over time.
    """

    def __init__(self, project_path: str = None, storage_mode: str = 'auto'):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.bm = BerryManager(storage_mode=storage_mode, project_path=str(self.project_path))
        # Pass BerryManager to extractor for adaptive learning
        self.extractor = MemoryExtractor(berry_manager=self.bm)

    def process_transcript(self, transcript_path: str, last_n_messages: int = 5) -> List[Dict]:
        """Process a Claude Code transcript file and extract memories.

        Also learns from user's communication patterns to improve future extraction.

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
        except Exception:
            return []

        # Get the last N messages
        recent_messages = messages[-last_n_messages:] if len(messages) > last_n_messages else messages

        # Extract text content from messages
        conversation_text = self._extract_text_from_messages(recent_messages)

        # Learn from the user's communication patterns
        self.extractor.learn_from_text(conversation_text)

        # Extract memories
        extracted = self.extractor.extract_all(conversation_text)

        # Store extracted memories
        stored = self._store_memories(extracted)

        # Record effective signals when memories are successfully extracted
        if stored:
            emphasized = self.extractor.detect_emphasis_patterns(conversation_text)
            for word in emphasized[:5]:
                self.bm.record_effective_signal(word)

        return stored

    def process_text(self, text: str) -> List[Dict]:
        """Process raw text and extract memories.

        Also learns from user's communication patterns to improve future extraction.

        Args:
            text: Conversation text to analyze

        Returns:
            List of extracted and stored memories
        """
        # Learn from the user's communication patterns
        self.extractor.learn_from_text(text)

        # Extract and store memories
        extracted = self.extractor.extract_all(text)
        stored = self._store_memories(extracted)

        # Record effective signals when memories are successfully extracted
        if stored:
            emphasized = self.extractor.detect_emphasis_patterns(text)
            for word in emphasized[:5]:  # Limit to top 5
                self.bm.record_effective_signal(word)

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
        """Store extracted memories in the berry manager.

        Now includes:
        - Auto-pinning of credentials/configs
        - Automatic task clustering based on tags
        """
        stored = []

        for memory in memories:
            try:
                # Check for auto-pin patterns in any memory content
                content_to_check = ""
                if memory['type'] == 'solution':
                    content_to_check = f"{memory['problem']} {memory['solution']}"
                elif memory['type'] == 'error':
                    content_to_check = f"{memory['error_message']} {memory['resolution']}"
                elif memory['type'] == 'confirmed_solution':
                    content_to_check = memory.get('solution', '')

                # Auto-pin if credentials/configs detected
                if content_to_check:
                    pin_result = self.bm.auto_pin_if_needed(
                        content_to_check,
                        name_hint=memory.get('problem', memory.get('type', 'Auto-detected'))[:50]
                    )
                    if pin_result:
                        memory['_auto_pinned'] = True

                if memory['type'] == 'solution':
                    result = self.bm.add_solution(
                        problem=memory['problem'],
                        solution=memory['solution'],
                        tags=memory.get('tags', []),
                        code_snippet=None
                    )
                    # Auto-cluster based on tags
                    if result and result.get('id'):
                        self.bm.auto_cluster_memory(
                            result['id'],
                            memory.get('tags', []),
                            f"{memory['problem']} {memory['solution']}"
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

                elif memory['type'] == 'user_need':
                    # Store user needs as solutions (what they're trying to accomplish)
                    self.bm.add_solution(
                        problem=f"User need: {memory['need']}",
                        solution="(Captured from conversation - pending resolution)",
                        tags=memory.get('tags', []) + ['user-need'],
                        code_snippet=None
                    )
                    stored.append(memory)

                elif memory['type'] == 'forgotten_item':
                    # High priority - this was repeated, should be remembered!
                    self.bm.add_solution(
                        problem=f"Repeated issue: {memory['description']}",
                        solution="(Auto-captured - user had to repeat this)",
                        tags=memory.get('tags', []) + ['repeated', 'high-priority'],
                        code_snippet=None
                    )
                    stored.append(memory)

                elif memory['type'] == 'confirmed_solution':
                    # Confirmed working - high value!
                    self.bm.add_solution(
                        problem="Confirmed working solution",
                        solution=memory['solution'],
                        tags=memory.get('tags', []) + ['confirmed', 'working'],
                        code_snippet=None
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
