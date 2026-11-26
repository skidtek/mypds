"""Command line: mypds serve | migrate | create-user | gen-key | doctor | demo."""

import argparse
import asyncio
import getpass
import sys
from importlib.resources import files
from pathlib import Path


def _alembic_config():  # noqa: ANN202
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(files("mypds") / "migrations"))
    return cfg


def cmd_migrate(_: argparse.Namespace) -> int:
    from alembic import command

    command.upgrade(_alembic_config(), "head")
    print("Database is up to date.")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from mypds.core.settings import get_settings

    s = get_settings()
    uvicorn.run(
        "mypds.app:create_app",
        factory=True,
        host=args.host or s.host,
        port=args.port or s.port,
        proxy_headers=False,
        log_config=None,
        reload=args.reload,
        reload_dirs=[str(Path(__file__).parent)] if args.reload else None,
    )
    return 0


def cmd_gen_key(args: argparse.Namespace) -> int:
    from mypds.core.crypto import generate_key_file

    path = Path(args.path)
    if path.exists():
        print(f"{path} already exists: nothing changed.", file=sys.stderr)
        return 1
    generate_key_file(path)
    print(f"Key created: {path} (back it up somewhere safe).")
    return 0


async def _create_user(username: str, display: str, role: str, password: str) -> None:
    from sqlalchemy import select

    from mypds.auth.models import User
    from mypds.auth.service import hash_password, normalize_username
    from mypds.core.db import dispose_engine, sessionmaker

    async with sessionmaker()() as db:
        uname = normalize_username(username)
        user = await db.scalar(select(User).where(User.username == uname))
        if user is None:
            db.add(User(username=uname, display_name=display, role=role, password_hash=hash_password(password)))
            print(f'User "{uname}" created ({role}).')
        else:
            user.password_hash, user.role, user.display_name = hash_password(password), role, display
            print(f'User "{uname}" updated.')
        await db.commit()
    await dispose_engine()


def cmd_create_user(args: argparse.Namespace) -> int:
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Password (at least 12 characters): ")
        if password != getpass.getpass("Confirm password: "):
            print("The passwords don't match.", file=sys.stderr)
            return 1
    try:
        asyncio.run(_create_user(args.username, args.display_name or args.username, args.role, password))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


async def _demo() -> list[str]:
    """Adds one demo connector for each type not configured yet (fake data, labeled on screen)."""
    import uuid

    from sqlalchemy import select

    from mypds.connectors.models import ConnectorInstance
    from mypds.connectors.sdk import registry
    from mypds.core.db import dispose_engine, sessionmaker

    added = []
    async with sessionmaker()() as db:
        present = set(await db.scalars(select(ConnectorInstance.type)))
        for type_id, cls in sorted(registry().items()):
            if type_id in present:
                continue
            db.add(
                ConnectorInstance(
                    id=uuid.uuid4(),
                    type=type_id,
                    name=f"{cls.display_name} (demo)",
                    enabled=True,
                    config=cls.config_model.model_validate({"mode": "demo"}).model_dump(mode="json", exclude_none=True),
                    poll_interval_s=cls.default_interval_s,
                )
            )
            added.append(type_id)
        await db.commit()
    await dispose_engine()
    return added


def cmd_demo(_: argparse.Namespace) -> int:
    added = asyncio.run(_demo())
    print(f"Demo connectors added: {', '.join(added)}." if added else "Nothing to add.")
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    from mypds.core.crypto import SecretKeyError, _key
    from mypds.core.settings import get_settings

    s = get_settings()
    ok = True
    try:
        _key()
        print(f"[ok] encryption key: {s.secret_key_file}")
    except SecretKeyError as exc:
        ok = False
        print(f"[!!] {exc}")

    async def db_check() -> str:
        from sqlalchemy import text

        from mypds.core.db import dispose_engine, sessionmaker

        try:
            async with sessionmaker()() as db:
                rev = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            return f"[ok] database, migration {rev}"
        except Exception as exc:  # noqa: BLE001
            return f"[!!] database: {exc}"
        finally:
            await dispose_engine()

    line = asyncio.run(db_check())
    ok = ok and line.startswith("[ok]")
    print(line)
    if s.static_dir and (Path(s.static_dir) / "index.html").exists():
        print(f"[ok] interface: {s.static_dir}")
    else:
        print(f"[--] interface missing ({s.static_dir})")
    return 0 if ok else 1


def main() -> None:
    p = argparse.ArgumentParser(prog="mypds")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("serve")
    sp.add_argument("--host")
    sp.add_argument("--port", type=int)
    sp.add_argument("--reload", action="store_true")
    sp.set_defaults(fn=cmd_serve)
    sub.add_parser("migrate").set_defaults(fn=cmd_migrate)
    cu = sub.add_parser("create-user")
    cu.add_argument("username")
    cu.add_argument("--display-name")
    cu.add_argument("--role", choices=["viewer", "operator", "admin"], default="admin")
    cu.add_argument("--password-stdin", action="store_true")
    cu.set_defaults(fn=cmd_create_user)
    gk = sub.add_parser("gen-key")
    gk.add_argument("path")
    gk.set_defaults(fn=cmd_gen_key)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    sub.add_parser("demo", help="add demo connectors").set_defaults(fn=cmd_demo)
    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
