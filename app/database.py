import subprocess
from typing import Optional

db: Optional["Prisma"] = None


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
            # Generate client at runtime as a fallback
            subprocess.run(["prisma", "generate"], check=True)
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
