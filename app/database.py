import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

db: Optional["Prisma"] = None
PrismaType = Optional["Prisma"]

def _generate_prisma_client() -> None:
    """
    Generate the Prisma client even when the CLI shim isn't on PATH.
    Tries the standard entrypoint first, then falls back to `python -m prisma`.
    """
    # Lambda/Edge filesystems are often read-only outside /tmp, so redirect Prisma caches there.
    env = os.environ.copy()
    env["HOME"] = "/tmp"  # force Path.home() inside prisma CLI to land on a writable path

    cache_root = Path(env.get("XDG_CACHE_HOME", "/tmp/.cache"))
    engines_cache = cache_root / "prisma-engines"
    cli_cache = cache_root / "prisma-python"
    for path in (cache_root, engines_cache, cli_cache):
        path.mkdir(parents=True, exist_ok=True)

    env.setdefault("XDG_CACHE_HOME", str(cache_root))
    env.setdefault("PRISMA_ENGINES_CACHE_DIR", str(engines_cache))
    env.setdefault("PRISMA_PYTHON_CLI_CACHE_DIR", str(cli_cache))

    last_error: Exception | None = None
    for cmd in (["prisma", "generate"], [sys.executable, "-m", "prisma", "generate"]):
        try:
            subprocess.run(cmd, check=True, env=env)
            return
        except FileNotFoundError as exc:
            last_error = exc
        except subprocess.CalledProcessError as exc:
            last_error = exc

    raise RuntimeError(
        "Prisma client generation failed. Ensure `prisma generate` runs during build "
        "or that the Prisma CLI is available at runtime."
    ) from last_error


def _ensure_prisma_client():
    """
    Lazy-load Prisma client and generate on-demand if it was not built during deployment.
    This guards against Vercel builds skipping `prisma generate`.
    """
    global db
    if db is not None:
        return db

    PrismaClass = None
    # Prefer vendored client generated into the repo (app/prisma_client).
    try:
        from app.prisma_client import Prisma as VendoredPrisma  # type: ignore

        PrismaClass = VendoredPrisma
    except Exception:
        PrismaClass = None

    allow_runtime_generate = os.environ.get("PRISMA_GENERATE_AT_RUNTIME", "").lower() in (
        "1",
        "true",
        "yes",
    )

    try:
        if PrismaClass is None:
            from prisma import Prisma as InstalledPrisma  # type: ignore

            PrismaClass = InstalledPrisma
    except RuntimeError as exc:
        if "hasn't been generated yet" in str(exc):
            if not allow_runtime_generate:
                raise RuntimeError(
                    "Prisma client is missing. Run `prisma generate` during build or set "
                    "PRISMA_GENERATE_AT_RUNTIME=1 to allow runtime generation (not recommended on read-only/serverless)."
                ) from exc
            _generate_prisma_client()
            from prisma import Prisma as InstalledPrisma  # re-import after generation

            PrismaClass = InstalledPrisma
        else:
            raise

    if PrismaClass is None:
        raise RuntimeError(
            "Prisma client module not found. Ensure `prisma generate` wrote to app/prisma_client "
            "or that the default prisma package is installed."
        )

    db = PrismaClass()
    return db


async def connect_db():
    prisma = _ensure_prisma_client()
    if not prisma.is_connected():
        await prisma.connect()


async def disconnect_db():
    prisma = _ensure_prisma_client()
    if prisma.is_connected():
        await prisma.disconnect()
