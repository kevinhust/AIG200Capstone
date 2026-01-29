"""
Convenience entrypoint so `python agent.py` works from the repo root.

You can pass the task via CLI args or the AGENT_TASK env var.
Example:
    python agent.py "帮我写一个快速排序算法"
"""
import os
import sys

from src.agent import GeminiAgent


def main():
    task = " ".join(sys.argv[1:]).strip() or os.environ.get(
        "AGENT_TASK", "帮助我查看今天的天气"
    )

    agent = GeminiAgent()
    try:
        agent.run(task)
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
