#!/usr/bin/env python3
"""
L2-AI 决策中枢 — 启动入口
L2 AI Decision Hub — Entry point

Usage:
  # Start the API server
  python main.py serve

  # Run a quick demo (requires ANTHROPIC_API_KEY)
  python main.py demo

  # Show help
  python main.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the FastAPI server."""
    import uvicorn
    from l2_decision_hub.api.app import create_app

    app = create_app()
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


async def cmd_demo(args: argparse.Namespace) -> None:
    """Run a quick demo of the Decision Hub."""
    from l2_decision_hub.core.engine import DecisionHub
    from l2_decision_hub.models.decision import DecisionType
    from l2_decision_hub.models.priority import Priority

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print("Starting L2-AI Decision Hub demo...\n")
    hub = DecisionHub(api_key=api_key)
    await hub.start()

    decision_id = await hub.submit(
        title="Evaluate cloud provider migration",
        description=(
            "Our on-premises infrastructure is reaching end-of-life. "
            "We need to decide whether to migrate to AWS, GCP, or Azure, "
            "or invest in refreshing the existing infrastructure."
        ),
        decision_type=DecisionType.STRATEGIC,
        priority=Priority.HIGH,
        input_data={
            "current_cost_annual_usd": 500_000,
            "team_size": 50,
            "primary_workloads": ["web", "data_pipeline", "ml_training"],
            "compliance_requirements": ["SOC2", "GDPR"],
        },
        constraints=[
            "Migration must complete within 12 months",
            "Zero downtime during migration",
            "Stay within 20% cost increase in year 1",
        ],
        objectives=[
            "Maximise long-term scalability",
            "Reduce operational overhead",
            "Improve developer experience",
        ],
    )

    print(f"Decision submitted: {decision_id}")
    print("Waiting for AI reasoning (this may take a moment)...\n")

    decision = await hub.wait_for_result(decision_id, timeout=120.0)

    if decision.result:
        r = decision.result
        print("=" * 60)
        print(f"ACTION:     {r.action}")
        print(f"CONFIDENCE: {r.confidence:.0%}")
        print(f"\nREASONING:\n{r.reasoning}")
        if r.alternatives:
            print(f"\nALTERNATIVES:")
            for alt in r.alternatives:
                print(f"  • {alt.get('action', 'N/A')}")
        if r.metadata:
            print(f"\nMETADATA: {r.metadata}")
        print("=" * 60)
    else:
        print(f"Decision failed: {decision.error}")

    await hub.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="L2-AI Decision Hub")
    sub = parser.add_subparsers(dest="command")

    # serve
    serve_parser = sub.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--reload", action="store_true")

    # demo
    sub.add_parser("demo", help="Run a quick demo (requires ANTHROPIC_API_KEY)")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "demo":
        asyncio.run(cmd_demo(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
