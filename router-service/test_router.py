#!/usr/bin/env python3
"""
Test script for the Agent Router Service.

Run with: python test_router.py

Requires the service to be running: uvicorn router:app --host 127.0.0.1 --port 8765
"""

import requests
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8765"


def test_health():
    """Test health endpoint."""
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    print("✓ Health check passed")


def test_route(prompt: str, expected_agent: str = None) -> Dict[str, Any]:
    """Test routing a prompt."""
    resp = requests.post(
        f"{BASE_URL}/route",
        json={"prompt": prompt}
    )
    if resp.status_code != 200:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        raise AssertionError(f"Route failed with status {resp.status_code}: {resp.text}")
    data = resp.json()

    task_type = data['task_analysis']['task_type']
    print(f"\nPrompt: {prompt[:60]}...")
    print(f"  → Task Type: {task_type} (conf: {data['task_analysis']['task_type_confidence']:.2f})")
    print(f"  → Complexity: {data['task_analysis']['complexity']} ({data['task_analysis']['complexity_score']:.2f})")
    print(f"  → Agent: {data['selected_agent']}")

    # Show signals if available
    all_scores = data['task_analysis'].get('all_scores', {})
    if all_scores.get('task_signals'):
        print(f"  → Signals: {all_scores['task_signals']}")

    if expected_agent:
        if task_type == expected_agent:
            print(f"  ✓ Task type matched: {expected_agent}")
        else:
            print(f"  ✗ Expected task type: {expected_agent}, got: {task_type}")
            assert task_type == expected_agent, (
                f"Expected task type '{expected_agent}', got '{task_type}'"
            )

    return data


def test_classify(prompt: str):
    """Test classification only."""
    resp = requests.post(
        f"{BASE_URL}/classify",
        json={"prompt": prompt}
    )
    if resp.status_code != 200:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        raise AssertionError(f"Classify failed with status {resp.status_code}")
    data = resp.json()

    print(f"\nClassification: {prompt[:50]}...")
    print(f"  → Type: {data['task_type']} ({data['task_type_confidence']:.2f})")
    print(f"  → Complexity: {data['complexity']} ({data['complexity_score']:.2f})")
    if data.get('all_scores'):
        print(f"  → Scores: {data['all_scores']}")

    return data


def test_compress():
    """Test context compression."""
    verbose_content = """
    I think I'll start by analyzing the codebase structure. Let me look at the files.

    First, I'll examine the main entry point. Actually, let me reconsider the approach.

    Here's the code I found:

    ```python
    def authenticate(user, password):
        if not validate_credentials(user, password):
            raise AuthError("Invalid credentials")
        return create_session(user)
    ```

    I modified the file at /src/auth/login.py to add the new feature.

    The implementation is complete. I successfully added the authentication module.
    It handles user login, session management, and token refresh.

    Error: Could not find config.json in the expected location.

    Let me now explain in great detail what each line does and why I chose this
    particular implementation pattern over the many alternatives that were available...
    """

    for level in ["minimal", "moderate", "aggressive"]:
        resp = requests.post(
            f"{BASE_URL}/compress",
            json={"content": verbose_content, "level": level, "max_tokens": 500}
        )
        assert resp.status_code == 200
        data = resp.json()

        print(f"\nCompression ({level}):")
        print(f"  → Original: {data['original_length']} chars")
        print(f"  → Compressed: {data['compressed_length']} chars")
        print(f"  → Ratio: {data['compression_ratio']:.2f}")
        print(f"  → Code blocks: {len(data['code_blocks'])}")
        print(f"  → Errors: {len(data['errors'])}")

    print("✓ Compression tests passed")


def test_preferences():
    """Test routing with preferences."""
    prompt = "Write a Python function to sort a list"

    # Default
    test_route(prompt)

    # Speed preference
    resp = requests.post(
        f"{BASE_URL}/route",
        json={"prompt": prompt, "prefer_speed": True}
    )
    fast_agent = resp.json()["selected_agent"]
    print(f"\n  With prefer_speed: {fast_agent}")

    # Cost preference
    resp = requests.post(
        f"{BASE_URL}/route",
        json={"prompt": prompt, "prefer_cost": True}
    )
    cheap_agent = resp.json()["selected_agent"]
    print(f"  With prefer_cost: {cheap_agent}")

    # Exclude agents
    resp = requests.post(
        f"{BASE_URL}/route",
        json={"prompt": prompt, "exclude_agents": ["codex", "copilot"]}
    )
    limited_agent = resp.json()["selected_agent"]
    print(f"  Excluding codex/copilot: {limited_agent}")
    assert limited_agent in ["cursor", "gemini"]

    print("✓ Preference tests passed")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Agent Router Service Tests")
    print("=" * 60)

    try:
        test_health()
    except requests.exceptions.ConnectionError:
        print("ERROR: Router service not running!")
        print("Start it with: uvicorn router:app --host 127.0.0.1 --port 8765")
        return

    # Test various task types
    print("\n" + "-" * 40)
    print("Testing Task Type Classification")
    print("-" * 40)

    test_cases = [
        ("Fix the authentication bug in login.py", "code_debugging"),
        ("Debug why the API returns 500 errors", "code_debugging"),
        ("The login function crashes when password is empty", "code_debugging"),
        ("Explain how the database connection pool works", "code_explanation"),
        ("What does this regex pattern do?", "code_explanation"),
        ("Write a REST API endpoint for user registration", "code_generation"),
        ("Create a Python class for handling payments", "code_generation"),
        ("Implement JWT authentication with refresh tokens", "code_generation"),
        ("Review this pull request for security issues", "code_review"),
        ("Audit the auth module for vulnerabilities", "code_review"),
        ("Refactor the payment module to use async/await", "rewrite"),
        ("Clean up and modernize the legacy utils.js file", "rewrite"),
        ("Summarize the changes in the last 10 commits", "summarization"),
        ("What's the best approach for caching user sessions?", "open_qa"),
        ("Calculate the time complexity of this algorithm", "math"),
    ]

    for prompt, expected in test_cases:
        test_route(prompt, expected)

    print("\n" + "-" * 40)
    print("Testing Classification Only")
    print("-" * 40)

    test_classify("Calculate the fibonacci sequence for n=100")
    test_classify("What does this error message mean?")

    print("\n" + "-" * 40)
    print("Testing Compression")
    print("-" * 40)

    test_compress()

    print("\n" + "-" * 40)
    print("Testing Preferences")
    print("-" * 40)

    test_preferences()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
