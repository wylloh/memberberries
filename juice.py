#!/usr/bin/env python3
"""
🫐 Memberberries Juice - Claude Code Integration Helper

This script juices memberberries for Claude Code sessions.
It's designed to be called before starting Claude Code.

Member when you had to start from scratch every time? Not anymore!
"""

import sys
import os
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from berry_manager import BerryManager


class Juicer:
    """Juices memberberries for Claude Code."""
    
    def __init__(self):
        self.bm = BerryManager()
    
    def juice_for_session(self, task_description: str, project_path: str = None) -> str:
        """Juice memberberries at the start of a Claude Code session.
        
        Args:
            task_description: What the user wants to accomplish
            project_path: Path to the project (default: current directory)
            
        Returns:
            Relevant juiced berries to inject into the conversation
        """
        if project_path is None:
            project_path = os.getcwd()
        
        print(f"\n🫐 Juicing memberberries for: '{task_description}'")
        print(f"📁 Project: {project_path}\n")
        
        context = self.bm.get_relevant_context(
            query=task_description,
            project_path=project_path
        )
        
        if context and context != "No relevant context found.":
            print("✓ Berries juiced successfully\n")
            return f"""
# 🫐 MEMBERBERRIES FOR CLAUDE CODE

{context}

---
End of memberberries. Member these when helping with the task!
"""
        else:
            print("ℹ️  No existing berries found (starting fresh)\n")
            return ""
    
    def concentrate_insight(self, problem: str, solution: str, code: str = None, 
                    tags: list = None):
        """Concentrate a breakthrough insight during the session.
        
        Args:
            problem: The problem that was solved
            solution: How it was solved
            code: Optional code snippet
            tags: Optional tags for categorization
        """
        result = self.bm.add_solution(
            problem=problem,
            solution=solution,
            code_snippet=code,
            tags=tags or []
        )
        print(f"🫐 Insight berry concentrated: {result['id']}")
        return result
    
    def concentrate_preference(self, category: str, preference: str, tags: list = None):
        """Concentrate a user preference.
        
        Args:
            category: Category (e.g., 'coding_style', 'tools', 'workflow')
            preference: The preference content
            tags: Optional tags
        """
        result = self.bm.add_preference(category, preference, tags or [])
        print(f"🫐 Preference berry concentrated: {category}")
        return result
    
    def update_project_context(self, project_path: str, updates: dict):
        """Update project berry with new information.
        
        Args:
            project_path: Path to the project
            updates: Dictionary with context updates
        """
        # Get existing context or create new
        existing = self.bm.get_project_context(project_path) or {}
        
        # Merge updates
        existing.update(updates)
        
        project_hash = self.bm.add_project_context(project_path, existing)
        print(f"🫐 Project berry concentrated: {project_hash}")
        return project_hash
    
    def end_session(self, summary: str, learnings: list = None, 
                   project_path: str = None):
        """Concentrate session berry at the end of a Claude Code session.
        
        Args:
            summary: Brief summary of what was accomplished
            learnings: List of key insights or decisions
            project_path: Project this session was about
        """
        result = self.bm.save_session_summary(
            summary=summary,
            key_learnings=learnings or [],
            project_path=project_path
        )
        print(f"\n🫐 Session berry concentrated: {result['id']}")
        print(f"Summary: {summary}")
        if learnings:
            print("Key learnings:")
            for learning in learnings:
                print(f"  - {learning}")
        return result
    
    def quick_juice(self, query: str, limit: int = 3) -> list:
        """Quick juice for relevant berries.
        
        Args:
            query: What to juice for
            limit: Max number of results
            
        Returns:
            List of relevant solution berries
        """
        return self.bm.search_solutions(query, top_k=limit)


# Convenience function for command-line usage
def juice_context_for_task(task: str, project_path: str = None) -> str:
    """Quick function to juice berries - can be called from shell scripts.
    
    Usage:
        python juice.py "implement user authentication" /path/to/project
    """
    juicer = Juicer()
    return juicer.juice_for_session(task, project_path)


if __name__ == "__main__":
    # Allow calling from command line
    if len(sys.argv) < 2:
        print("🫐 Memberberries Juice")
        print("\nUsage: python juice.py <task_description> [project_path]")
        print("\nExample:")
        print("  python juice.py 'implement user authentication' ~/my-project")
        sys.exit(1)
    
    task = sys.argv[1]
    project = sys.argv[2] if len(sys.argv) > 2 else None
    
    context = juice_context_for_task(task, project)
    print(context)
