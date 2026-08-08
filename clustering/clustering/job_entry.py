"""Cloud Run Job entrypoint: optional migrate, GCS download, then process."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _truthy(value: str | None) -> bool:
    return (value or "").lower() in {"1", "true", "yes", "on"}


def main() -> int:
    if _truthy(os.getenv("RUN_MIGRATIONS")):
        subprocess.check_call(["alembic", "upgrade", "head"])

    data_path = Path(os.getenv("DATA_FILE", "/tmp/data.json"))
    gcs_uri = os.getenv("GCS_URI")
    if gcs_uri:
        from clustering.gcs_io import download_file
        from clustering.log import info

        info(f"Downloading {gcs_uri} -> {data_path}")
        download_file(gcs_uri, data_path)

    if not data_path.is_file():
        print(
            f"Missing data file: {data_path}. Set GCS_URI or mount DATA_FILE.",
            file=sys.stderr,
        )
        return 1

    argv = ["process", "--file", str(data_path)]
    if _truthy(os.getenv("QUIET")):
        argv.insert(0, "-q")
    if _truthy(os.getenv("FORCE_READY")):
        argv.append("--force-ready")

    limit = os.getenv("PROCESS_LIMIT")
    if limit:
        argv.extend(["--limit", limit])

    from clustering.cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
