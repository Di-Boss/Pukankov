import subprocess
import sys
import uvicorn
from .db import SessionLocal
from .seed import seed


def main():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    with SessionLocal() as db:
        seed(db)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
