import subprocess
import sys
from typing import Optional

db: Optional["Prisma"] = None

def _generate_prisma_client() -> None:
    """
    Generate the Prisma client even when the CLI shim isn't on PATH.
    Tries the standard entrypoint first, then falls back to `python -m prisma`.
    """
    last_error: Exception | None = None
    for cmd in (["prisma", "generate"], [sys.executable, "-m", "prisma", "generate"]):
        try:
            subprocess.run(cmd, check=True)
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

    try:
        from prisma import Prisma
    except RuntimeError as exc:
        if "hasn't been generated yet" in str(exc):
            _generate_prisma_client()
            from prisma import Prisma  # re-import after generation
        else:
            raise

    db = Prisma()
    return db


async def connect_db():
    prisma = _ensure_prisma_client()
    if not prisma.is_connected():
        await prisma.connect()


async def disconnect_db():
    prisma = _ensure_prisma_client()
    if prisma.is_connected():
        await prisma.disconnect()
