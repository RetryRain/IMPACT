from __future__ import annotations

from pathlib import Path


def download_file(gcs_uri: str, destination: Path) -> Path:
    """Download gs://bucket/object to a local path."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Expected gs:// URI, got {gcs_uri!r}")

    without_scheme = gcs_uri[len("gs://") :]
    bucket_name, _, blob_name = without_scheme.partition("/")
    if not bucket_name or not blob_name:
        raise ValueError(f"Invalid GCS URI: {gcs_uri!r}")

    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(destination))
    return destination
