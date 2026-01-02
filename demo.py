#!/usr/bin/env python3
"""
Demo script showing Claude Code Memory System in action
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from integration import ClaudeCodeMemory
import time


def print_section(title):
    """Print a section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def demo():
    """Run a complete demonstration of the memory system."""
    
    print_section("Claude Code Memory System Demo")
    
    # Initialize
    memory = ClaudeCodeMemory()
    
    # Demo 1: Add some preferences
    print_section("1. Adding User Preferences")
    
    memory.save_preference(
        category="coding_style",
        preference="Always use type hints in Python functions. Prefer explicit over implicit.",
        tags=["python", "style"]
    )
    
    memory.save_preference(
        category="testing",
        preference="Write tests first (TDD approach). Use pytest with fixtures.",
        tags=["python", "testing", "tdd"]
    )
    
    memory.save_preference(
        category="documentation",
        preference="Use Google-style docstrings. Include examples in docstrings for complex functions.",
        tags=["python", "docs"]
    )
    
    time.sleep(1)
    
    # Demo 2: Add project context
    print_section("2. Adding Project Context")
    
    project_path = "/home/claude/demo-project"
    memory.update_project_context(
        project_path=project_path,
        updates={
            "name": "Demo Web API",
            "description": "FastAPI-based REST API with PostgreSQL",
            "architecture": "Clean Architecture: API layer -> Service layer -> Repository layer",
            "tech_stack": ["Python 3.11", "FastAPI", "PostgreSQL", "Redis", "Docker"],
            "conventions": [
                "snake_case for Python",
                "Async functions for I/O operations",
                "Pydantic models for validation"
            ]
        }
    )
    
    time.sleep(1)
    
    # Demo 3: Save some solutions
    print_section("3. Saving Solutions to Common Problems")
    
    memory.save_insight(
        problem="How to handle database connections in FastAPI",
        solution="Use lifespan context manager with connection pooling. Initialize pool on startup, close on shutdown.",
        code="""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(
        "postgresql://user:pass@localhost/db",
        min_size=5,
        max_size=20
    )
    yield
    # Shutdown
    await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)
""",
        tags=["python", "fastapi", "database", "postgresql"]
    )
    
    memory.save_insight(
        problem="How to implement JWT authentication in FastAPI",
        solution="Use python-jose for JWT encoding/decoding. Store tokens in HTTP-only cookies for web apps, or Authorization header for mobile/API clients.",
        code="""
from jose import jwt, JWTError
from datetime import datetime, timedelta

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
""",
        tags=["python", "fastapi", "authentication", "jwt", "security"]
    )
    
    memory.save_insight(
        problem="How to structure FastAPI project for scalability",
        solution="Use routers for different domains, separate models/schemas/services, dependency injection for database access.",
        code="""
project/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── users.py
│   │       │   └── auth.py
│   │       └── router.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
""",
        tags=["python", "fastapi", "architecture", "project-structure"]
    )
    
    time.sleep(1)
    
    # Demo 4: Search for solutions
    print_section("4. Searching for Relevant Solutions")
    
    print("🔍 Searching for: 'database connection handling'\n")
    results = memory.quick_search("database connection handling", limit=2)
    
    for i, result in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Problem: {result['problem']}")
        print(f"  Solution: {result['solution'][:100]}...")
        print(f"  Tags: {', '.join(result['tags'])}")
        print()
    
    time.sleep(1)
    
    # Demo 5: Get context for a new task
    print_section("5. Getting Context for New Task")
    
    print("📋 Task: 'Implement user registration endpoint with email verification'\n")
    
    context = memory.session_start(
        task_description="implement user registration endpoint with email verification",
        project_path=project_path
    )
    
    print(context)
    
    time.sleep(1)
    
    # Demo 6: End session with summary
    print_section("6. Ending Session with Summary")
    
    memory.session_end(
        summary="Implemented user registration with email verification using FastAPI and SendGrid",
        learnings=[
            "Use background tasks for sending verification emails to avoid blocking the response",
            "Store verification tokens in Redis with expiry (24 hours)",
            "Always validate email format with pydantic before sending verification",
            "Rate limit registration endpoint to prevent spam (max 3 per hour per IP)"
        ],
        project_path=project_path
    )
    
    time.sleep(1)
    
    # Demo 7: Show statistics
    print_section("7. Memory Statistics")
    
    stats = memory.mm.get_stats()
    print(f"📊 Current Memory Status:")
    print(f"   Preferences: {stats['preferences']}")
    print(f"   Projects: {stats['projects']}")
    print(f"   Solutions: {stats['solutions']}")
    print(f"   Sessions: {stats['sessions']}")
    
    print_section("Demo Complete!")
    
    print("✅ The memory system now contains:")
    print("   • Your coding preferences")
    print("   • Project-specific context")
    print("   • Solutions to common problems")
    print("   • Session history")
    print()
    print("💡 Try running:")
    print("   python3 claude_memory.py stats")
    print("   python3 claude_memory.py search 'authentication'")
    print("   python3 integration.py 'add password reset' /home/claude/demo-project")
    print()


if __name__ == "__main__":
    demo()
