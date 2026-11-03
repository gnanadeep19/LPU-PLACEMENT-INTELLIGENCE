"""Provision accounts for the local credential provider.

Examples:
    py backend/manage_users.py create-user --username mentor.cse --display-name "Mentor CSE" \\
        --role mentor --cohort CSE-2027
    py backend/manage_users.py list-users
    py backend/manage_users.py set-password --username mentor.cse
    py backend/manage_users.py deactivate-user --username mentor.cse

Passwords are hashed with Werkzeug (scrypt) and never stored in plain text.
There is no self-registration: the placement office provisions every account.
"""

from __future__ import annotations

import argparse
import getpass
import sys

import auth
from config import load_settings


def _password_from_args(args: argparse.Namespace) -> str:
    if args.password:
        print(
            "WARNING: passing --password exposes it in shell history; prefer the prompt.",
            file=sys.stderr,
        )
        return args.password
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        raise SystemExit("Passwords do not match.")
    return first


def build_parser() -> argparse.ArgumentParser:
    defaults = load_settings()
    parser = argparse.ArgumentParser(description="Manage LPU Placement Intelligence accounts.")
    parser.add_argument(
        "--auth-db",
        default=defaults.auth_database_path,
        help="Path to the auth SQLite database (default: %(default)s)",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    create = subcommands.add_parser("create-user", help="Create an account")
    create.add_argument("--username", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--role", required=True, choices=auth.ROLES)
    create.add_argument("--cohort", default=None, help="Required for mentor accounts")
    create.add_argument("--password", default=None, help="Non-interactive password (avoid)")

    password = subcommands.add_parser("set-password", help="Reset a password and end sessions")
    password.add_argument("--username", required=True)
    password.add_argument("--password", default=None)

    for name, help_text in (
        ("deactivate-user", "Disable an account and revoke its sessions"),
        ("activate-user", "Re-enable an account"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--username", required=True)

    subcommands.add_parser("list-users", help="List accounts without password hashes")
    subcommands.add_parser("purge-sessions", help="Delete expired sessions")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "create-user":
        try:
            user = auth.create_user(
                args.auth_db,
                username=args.username,
                password=_password_from_args(args),
                display_name=args.display_name,
                role=args.role,
                cohort=args.cohort,
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Created {user['role']} account '{user['username']}' (id={user['id']}).")
        return 0

    if args.command == "set-password":
        try:
            updated = auth.set_password(args.auth_db, args.username, _password_from_args(args))
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        if not updated:
            print("Error: account not found.", file=sys.stderr)
            return 1
        print(f"Password updated for '{args.username}'. Existing sessions were revoked.")
        return 0

    if args.command in {"deactivate-user", "activate-user"}:
        active = args.command == "activate-user"
        if not auth.set_active(args.auth_db, args.username, active):
            print("Error: account not found.", file=sys.stderr)
            return 1
        state = "activated" if active else "deactivated"
        print(f"Account '{args.username}' {state}.")
        return 0

    if args.command == "list-users":
        users = auth.list_users(args.auth_db)
        if not users:
            print("No accounts exist yet.")
            return 0
        print(f"{'USERNAME':<24}{'ROLE':<20}{'COHORT':<14}{'ACTIVE':<8}DISPLAY NAME")
        for user in users:
            print(
                f"{user['username']:<24}{user['role']:<20}{(user['cohort'] or '-'):<14}"
                f"{'yes' if user['is_active'] else 'no':<8}{user['display_name']}"
            )
        return 0

    if args.command == "purge-sessions":
        removed = auth.purge_expired_sessions(args.auth_db)
        print(f"Removed {removed} expired session(s).")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
