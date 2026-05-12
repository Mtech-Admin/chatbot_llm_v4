"""
Upload the HR Compendium PDF to the same S3 bucket used by DMRC_HRMS_API.

Loads AWS credentials from DMRC_HRMS_API/.env (same variables as Nest):
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_S3_BUCKET

Output URL format matches AwsS3Service.uploadFile:
  https://{bucket}.s3.amazonaws.com/{module}/{filename}

Usage (from dmrc_chatbot/):
  PYTHONPATH=. python3 scripts/upload_hr_compendium_s3.py \\
      --file ./Updated_HR_Compendium_NOV23.pdf

By default the object is uploaded with ACL **public-read** (anonymous HTTPS GET on the
printed URL). Use **--private** to skip the ACL if you use a locked-down bucket.

Optional: --presign to also print a presigned URL (usually unnecessary when public-read).

Then set in dmrc_chatbot/.env.local:
  HR_COMPENDIUM_PDF_URL=<printed URL>
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv


def _default_api_env() -> Path:
    """Resolve DMRC_HRMS_API/.env next to dmrc_chatbot or inside it."""
    chatbot_root = Path(__file__).resolve().parent.parent
    candidates = [
        chatbot_root.parent / "DMRC_HRMS_API" / ".env",
        chatbot_root / "DMRC_HRMS_API" / ".env",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def _public_object_url(bucket: str, key: str) -> str:
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload HR Compendium PDF to S3 (HRMS credentials)")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Path to DMRC_HRMS_API .env (default: <repo>/DMRC_HRMS_API/.env)",
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

    env_path = (args.env_file or _default_api_env()).expanduser().resolve()
    if not env_path.is_file():
        raise FileNotFoundError(
            f"Env file not found: {env_path}\n"
            "Pass --env-file /path/to/DMRC_HRMS_API/.env"
        )

    load_dotenv(env_path, override=False)

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
        chatbot_root = Path(__file__).resolve().parent.parent
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
