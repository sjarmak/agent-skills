#!/usr/bin/env python3
"""
Standalone CLI router - no server required.

Usage:
    python3 route_cli.py "Your task description here"
    python3 route_cli.py --prompt "Your task" --prefer-speed

Output: JSON with routing decision

This can be called directly from Claude Code skills without running uvicorn.
"""

import argparse
import json
import sys

from classifier import classify_prompt, select_agent


def main():
    parser = argparse.ArgumentParser(
        description="Route coding tasks to the optimal AI agent (no server required)"
    )
    parser.add_argument("prompt", nargs="?", help="The task description")
    parser.add_argument(
        "--prompt", "-p", dest="prompt_flag", help="Task description (alternative)"
    )
    parser.add_argument(
        "--prefer-speed", action="store_true", help="Prefer faster agents"
    )
    parser.add_argument(
        "--prefer-cost", action="store_true", help="Prefer cheaper agents"
    )
    parser.add_argument(
        "--exclude", nargs="*", default=[], help="Agents to exclude"
    )
    parser.add_argument(
        "--include-unavailable",
        action="store_true",
        help="Include agents that aren't installed",
    )
    parser.add_argument(
        "--classify-only",
        action="store_true",
        help="Only classify, don't select agent",
    )
    parser.add_argument(
        "--compact", action="store_true", help="Output compact single-line JSON"
    )

    args = parser.parse_args()

    prompt = args.prompt or args.prompt_flag
    if not prompt:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()

    if not prompt:
        parser.print_help()
        sys.exit(1)

    classification = classify_prompt(prompt)

    if args.classify_only:
        result = classification
    else:
        result = select_agent(
            classification,
            prefer_speed=args.prefer_speed,
            prefer_cost=args.prefer_cost,
            exclude_agents=args.exclude,
            available_only=not args.include_unavailable,
            prompt=prompt,
        )

    if args.compact:
        print(json.dumps(result, separators=(",", ":")))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
