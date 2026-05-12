"""
Upload the HR Compendium PDF to S3.

Loads AWS settings from **dmrc_chatbot** env files (same variable names as HRMS):
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_S3_BUCKET

Copy those four keys from DMRC_HRMS_API/.env into **dmrc_chatbot/.env.local** (do not
point this script at HRMS .env).

Default env file: dmrc_chatbot/.env.local, then fallback dmrc_chatbot/.env.
Override with --env-file if needed.

Output URL format matches AwsS3Service.uploadFile:
  https://{bucket}.s3.amazonaws.com/{module}/{filename}

Usage (from dmrc_chatbot/):
  PYTHONPATH=. python3 scripts/upload_hr_compendium_s3.py \\
      --file ./Updated_HR_Compendium_NOV23.pdf

By default the object is uploaded with ACL **public-read** (anonymous HTTPS GET on the
printed URL). Use **--private** to skip the ACL if you use a locked-down bucket.

Optional: --presign to also print a presigned URL (usually unnecessary when public-read).

After upload, ensure .env.local contains the stable PDF URL:
  HR_COMPENDIUM_PDF_URL=<printed URL>
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv


def _chatbot_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_chatbot_env_file() -> Path:
    """Prefer dmrc_chatbot/.env.local, then .env."""
    root = _chatbot_root()
    for name in (".env.local", ".env"):
        candidate = (root / name).resolve()
        if candidate.is_file():
            return candidate
    return (root / ".env.local").resolve()


def _resolve_env_file(arg_path: Path | None) -> Path:
    if arg_path is not None:
        p = arg_path.expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Env file not found: {p}")
        return p
    p = _default_chatbot_env_file()
    if not p.is_file():
        root = _chatbot_root()
        raise FileNotFoundError(
            f"No .env.local or .env under {root}.\n"
            "Copy into .env.local from DMRC_HRMS_API:\n"
            "  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_S3_BUCKET"
        )
    return p


def _public_object_url(bucket: str, key: str) -> str:
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload HR Compendium PDF to S3 (AWS vars from dmrc_chatbot/.env.local)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Env file to load (default: dmrc_chatbot/.env.local, then .env)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Local path to the PDF (default: dmrc_chatbot/Updated_HR_Compendium*.pdf if present)",
    )
    parser.add_argument(
        "--module",
        default="hr_compendium",
        help="S3 key prefix folder (same idea as Nest uploadFile module)",
    )
    parser.add_argument(
        "--key-name",
        default="",
        help="Object file name inside module/ (default: local file basename)",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Do not set ACL (object stays private; use presign or bucket policy instead)",
    )
    parser.add_argument(
        "--presign",
        action="store_true",
        help="Also print a presigned GET URL (for private objects; expires)",
    )
    parser.add_argument(
        "--presign-seconds",
        type=int,
        default=604800,
        help="Presigned URL lifetime in seconds (default 7 days)",
    )
    args = parser.parse_args()

    env_path = _resolve_env_file(args.env_file)
    # Let this file define AWS_* for this script run (typical: only set in .env.local).
    load_dotenv(env_path, override=True)

    bucket = (os.environ.get("AWS_S3_BUCKET") or "").strip()
    region = (os.environ.get("AWS_REGION") or "").strip()
    access_key = (os.environ.get("AWS_ACCESS_KEY_ID") or "").strip()
    secret_key = (os.environ.get("AWS_SECRET_ACCESS_KEY") or "").strip()

    if not all([bucket, region, access_key, secret_key]):
        raise RuntimeError(
            "Missing AWS_S3_BUCKET / AWS_REGION / AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY "
            f"in {env_path}"
        )

    local = Path(args.file).expanduser().resolve() if args.file else None
    if local is None:
        chatbot_root = _chatbot_root()
        for name in (
            "Updated_HR_Compendium_-NOV23.pdf",
            "Updated_HR_Compendium_NOV23.pdf",
            "Updated_HR_Compendium_NOV23.PDF",
        ):
            candidate = (chatbot_root / name).resolve()
            if candidate.is_file():
                local = candidate
                break
        if local is None:
            raise FileNotFoundError(
                "Pass --file /path/to/Updated_HR_Compendium_NOV23.pdf "
                f"(searched under {chatbot_root})"
            )
    elif not local.is_file():
        raise FileNotFoundError(f"PDF not found: {local}")

    file_name = (args.key_name or local.name).strip()
    module = args.module.strip().strip("/")
    key = f"{module}/{file_name}"

    import boto3
    from botocore.client import Config

    client = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

    extra: dict = {"ContentType": "application/pdf"}
    use_public_acl = not args.private
    if use_public_acl:
        extra["ACL"] = "public-read"

    client.upload_file(str(local), bucket, key, ExtraArgs=extra)

    static_url = _public_object_url(bucket, key)
    acl_note = "public-read" if use_public_acl else "none (private object)"
    print(f"Uploaded s3://{bucket}/{key} (ACL={acl_note})")
    if use_public_acl:
        print(f"\nHTTPS URL (stable; use in HR_COMPENDIUM_PDF_URL):\n  {static_url}")
    else:
        print(f"\nObject URL (403 for anonymous users until you presign or open policy):\n  {static_url}")
    print(
        f"\nAdd to dmrc_chatbot/.env.local:\n  HR_COMPENDIUM_PDF_URL={static_url}\n"
    )

    if args.presign:
        presigned = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=max(60, int(args.presign_seconds)),
        )
        print(f"Presigned GET URL (expires in {args.presign_seconds}s):\n  {presigned}\n")


if __name__ == "__main__":
    main()
