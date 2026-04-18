#!/usr/bin/env python3
import os
import sys
import argparse
import asyncio

from hyperbrowser import AsyncHyperbrowser
from hyperbrowser.models import (
    StartHyperAgentTaskParams,
    CreateSessionParams,
    ScreenConfig,
    SessionGetParams,
)


def parse_args():
    p = argparse.ArgumentParser(
        description="Run Hyperbrowser tasks and manage reusable browser sessions"
    )
    p.add_argument("--task", help="Natural-language browser task")
    p.add_argument(
        "--stop-session",
        help="Stop an existing session and exit",
    )
    p.add_argument(
        "--create-session-only",
        action="store_true",
        help="Create a reusable session and exit without running a task",
    )
    p.add_argument("--session-id", help="Reuse an existing Hyperbrowser session")
    p.add_argument(
        "--region",
        default=None,
        help="Hyperbrowser region, e.g. us-east, europe-west, asia-south (default: provider-chosen)",
    )
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--max-steps", type=int, default=20)
    p.add_argument(
        "--llm",
        default="gemini-3-flash-preview",
        choices=[
            "gpt-5.2",
            "gpt-5.1",
            "gpt-5",
            "gpt-5-mini",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "claude-sonnet-4-6",
            "claude-sonnet-4-5",
            "gemini-2.5-flash",
            "gemini-3-flash-preview",
        ],
        help="Hyperbrowser model for browser tasks",
    )
    p.add_argument(
        "--keep-browser-open",
        action="store_true",
        help="Keep the browser session open after the task completes",
    )
    p.add_argument(
        "--timeout-minutes",
        type=int,
        default=None,
        help="Requested session timeout in minutes",
    )
    p.add_argument(
        "--extend-session-minutes",
        type=int,
        default=None,
        help="Extend an existing session before running the task",
    )
    p.add_argument(
        "--live-view-ttl-seconds",
        type=int,
        default=None,
        help="Requested TTL for live view URLs",
    )
    p.add_argument(
        "--view-only-live-view",
        action="store_true",
        help="Request a view-only live URL instead of an interactive live URL",
    )
    p.add_argument(
        "--enable-window-manager",
        action="store_true",
        help="Enable Hyperbrowser window manager for richer manual interaction",
    )
    p.add_argument(
        "--print-session-details",
        action="store_true",
        help="Print session details before exit",
    )
    args = p.parse_args()

    if args.stop_session and (args.task or args.create_session_only):
        p.error("--stop-session cannot be combined with --task or --create-session-only")
    if args.create_session_only and args.task:
        p.error("--create-session-only cannot be combined with --task")
    if not args.stop_session and not args.create_session_only and not args.task:
        p.error("Provide one of: --task, --create-session-only, or --stop-session")
    if args.extend_session_minutes is not None and not (
        args.session_id or args.create_session_only or args.task
    ):
        p.error("--extend-session-minutes requires a session flow")

    return args


def build_session_params(args):
    return CreateSessionParams(
        screen=ScreenConfig(width=args.width, height=args.height),
        region=args.region,
        timeout_minutes=args.timeout_minutes,
        live_view_ttl_seconds=args.live_view_ttl_seconds,
        view_only_live_view=True if args.view_only_live_view else None,
        enable_window_manager=True if args.enable_window_manager else None,
    )


def print_session_details(session):
    print(f"SESSION_ID: {session.id}")
    print(f"SESSION_STATUS: {session.status}")
    print(f"SESSION_URL: {session.session_url}")
    print(f"LIVE_URL: {session.live_url}")


async def fetch_session(client, session_id, live_view_ttl_seconds=None):
    params = SessionGetParams(live_view_ttl_seconds=live_view_ttl_seconds)
    return await client.sessions.get(session_id, params)


async def ensure_session(client, args):
    if args.session_id:
        session = await fetch_session(
            client,
            args.session_id,
            live_view_ttl_seconds=args.live_view_ttl_seconds,
        )
        return session, False

    session = await client.sessions.create(build_session_params(args))
    return session, True


async def maybe_extend_session(client, session_id, minutes):
    if minutes is None:
        return
    result = await client.sessions.extend_session(session_id, minutes)
    print(f"SESSION_EXTENDED_MINUTES: {minutes}")
    print(f"SESSION_EXTEND_SUCCESS: {result.success}")


async def run_task(client, args, session_id):
    result = await client.agents.hyper_agent.start_and_wait(
        StartHyperAgentTaskParams(
            task=args.task,
            version="1.1.0",
            llm=args.llm,
            session_id=session_id,
            max_steps=args.max_steps,
            keep_browser_open=args.keep_browser_open,
        )
    )

    print(f"JOB_ID: {result.job_id}")
    print(f"TASK_STATUS: {result.status}")
    if result.live_url:
        print(f"TASK_LIVE_URL: {result.live_url}")
    if result.error:
        print(f"ERROR: {result.error}")
    final = getattr(getattr(result, "data", None), "final_result", None)
    if final:
        print("FINAL_RESULT:")
        print(final)


async def main():
    args = parse_args()
    api_key = os.environ.get("HYPERBROWSER_API_KEY")
    if not api_key:
        print("Error: HYPERBROWSER_API_KEY is not set.", file=sys.stderr)
        raise SystemExit(2)

    async with AsyncHyperbrowser(api_key=api_key) as client:
        if args.stop_session:
            result = await client.sessions.stop(args.stop_session)
            print(f"STOP_SESSION_ID: {args.stop_session}")
            print(f"STOP_SUCCESS: {result.success}")
            return

        session, created = await ensure_session(client, args)

        if created or args.print_session_details or args.create_session_only or args.session_id:
            print_session_details(session)

        if args.extend_session_minutes is not None:
            await maybe_extend_session(client, session.id, args.extend_session_minutes)
            session = await fetch_session(
                client,
                session.id,
                live_view_ttl_seconds=args.live_view_ttl_seconds,
            )
            print_session_details(session)

        if args.create_session_only:
            return

        await run_task(client, args, session.id)

        if args.keep_browser_open or args.print_session_details or created or args.session_id:
            session = await fetch_session(
                client,
                session.id,
                live_view_ttl_seconds=args.live_view_ttl_seconds,
            )
            print_session_details(session)


if __name__ == "__main__":
    asyncio.run(main())
