"""Redacted secret audit for the local SmartQuerySystem workspace.

The script never prints or stores a matched value. Findings include only the
file path, line number, field name, classification, value length and a truncated
SHA-256 fingerprint so operators can compare without exposing the secret.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tarfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence" / "secret_audit.json"

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".next",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".e2e",
    "playwright-report",
    "test-results",
    "submission",
}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".woff", ".woff2", ".ico", ".dump", ".db", ".sqlite", ".pyc"}

SECRET_NAME = (
    r"(?:OPENAI_API_KEY|BYOK_ENCRYPTION_KEY|BYOK_FERNET_KEY|FERNET_KEY|JWT_SECRET_KEY|"
    r"ESCALATION_CRON_SECRET|GOOGLE_CLIENT_SECRET|VERCEL_OIDC_TOKEN|SMTP_PASSWORD|"
    r"ADMIN_PASSWORD|DATABASE_URL|ANTHROPIC_API_KEY|GOOGLE_API_KEY|RESEND_API_KEY|"
    r"SENDGRID_API_KEY|WHATSAPP_[A-Z_]*TOKEN|WHATSAPP_[A-Z_]*SECRET|"
    r"API_KEY|SECRET_KEY|ACCESS_TOKEN|REFRESH_TOKEN|CLIENT_SECRET|PASSWORD|PRIVATE_KEY)"
)
ASSIGNMENT_RE = re.compile(
    rf"(?im)^[^\n]{{0,120}}?\b({SECRET_NAME})\b\s*[:=]\s*"
    r"(?P<quote>[\"']?)(?P<value>[^\s\"'#,;\n]+)(?P=quote)"
)
AWS_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")

PLACEHOLDER_MARKERS = (
    "change-me",
    "changeme",
    "replace_with",
    "replace-with",
    "replace ",
    "localhost",
    "127.0.0.1",
    "example",
    "placeholder",
    "your-",
    "your_",
    "xxx",
    "dummy",
    "fake",
    "test",
    "testing",
    "local",
    "development",
    "not-for-production",
    "notforsproduction",
    "e2e",
    "rehearsal",
    "sample",
    "todo",
    "none",
    "null",
    "true",
    "false",
    "settings.",
    "os.environ",
    "getenv",
    "process.env",
    "${",
    "{{",
    "self.",
    "config.",
)


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]


def classify(value: str) -> str:
    lowered = value.lower()
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        return "placeholder_or_reference"
    if len(value) < 12:
        return "short_or_unknown"
    if value.startswith(("$", "{", "<", "/", "http://", "https://")):
        return "placeholder_or_reference"
    return "potential_secret"


def redact_line(line: str) -> dict | None:
    match = ASSIGNMENT_RE.search(line)
    if match:
        value = match.group("value").strip().strip("\"'")
        return {
            "field": match.group(1).upper(),
            "classification": classify(value),
            "length": len(value),
            "sha256_12": fingerprint(value),
        }
    match = AWS_RE.search(line)
    if match:
        value = match.group(0)
        return {
            "field": "AWS_ACCESS_KEY_ID",
            "classification": "potential_secret",
            "length": len(value),
            "sha256_12": fingerprint(value),
        }
    match = PRIVATE_KEY_RE.search(line)
    if match:
        value = match.group(0)
        return {
            "field": "PRIVATE_KEY_HEADER",
            "classification": "potential_secret",
            "length": len(value),
            "sha256_12": fingerprint(value),
        }
    return None


def scan_text(text: str, source: str) -> list[dict]:
    findings: list[dict] = []
    for number, line in enumerate(text.splitlines(), start=1):
        detail = redact_line(line)
        if detail:
            findings.append({"source": source, "line": number, **detail})
    return findings


def iter_workspace_files() -> Path:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(ROOT).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name == "secret_audit.py":
            continue
        yield path


def load_local_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for env_file in (ROOT / "backend" / ".env", ROOT / "backend" / ".env.local"):
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip("\"'")
            if value and classify(value) == "potential_secret":
                values[key.strip().upper()] = value
    return values


def git_output(arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def scan_git() -> tuple[list[str], list[dict]]:
    tracked = [
        line for line in git_output(["ls-files"]).splitlines() if line.strip()
    ]
    findings: list[dict] = []
    patch = git_output(["log", "--all", "--format=COMMIT %H", "-p", "--no-ext-diff", "--", "."])
    commit = "unknown"
    for line in patch.splitlines():
        if line.startswith("COMMIT "):
            commit = line.split(" ", 1)[1].strip()
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        detail = redact_line(line[1:])
        if detail:
            findings.append({"source": f"git:{commit[:12]}", "line": 0, **detail})
    return tracked, findings


def scan_image(image: str) -> list[dict]:
    created = subprocess.run(
        ["docker", "create", image],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if created.returncode != 0:
        return [{"source": image, "error": "docker create failed"}]
    container = created.stdout.strip()
    findings: list[dict] = []
    try:
        process = subprocess.Popen(
            ["docker", "export", container],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert process.stdout is not None
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            for member in archive:
                if not member.isfile() or member.size > 2_000_000:
                    continue
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                raw = handle.read()
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                name = member.name.lstrip("./")
                for finding in scan_text(text, f"{image}:{name}"):
                    if finding["classification"] == "potential_secret":
                        findings.append(finding)
        process.wait(timeout=120)
    finally:
        subprocess.run(["docker", "rm", "-f", container], cwd=ROOT, capture_output=True, check=False)
    return findings


def main() -> None:
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)

    tracked, history_findings = scan_git()
    tracked_set = set(tracked)

    workspace_findings: list[dict] = []
    for path in iter_workspace_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relative = path.relative_to(ROOT).as_posix()
        for finding in scan_text(text, relative):
            if relative in tracked_set:
                finding["tracked"] = True
            else:
                finding["tracked"] = False
            workspace_findings.append(finding)

    images = [
        "smartquery-backend:release-audit",
        "smartquery-frontend:release-audit",
        "ghcr.io/raphicsdigitalsolutions/smart-query-system:latest",
    ]
    image_findings: list[dict] = []
    for image in images:
        image_findings.extend(scan_image(image))

    local_values = load_local_env_values()
    local_digests = {fingerprint(value): key for key, value in local_values.items()}
    for finding in workspace_findings + history_findings + image_findings:
        finding["matches_current_local_env_key"] = local_digests.get(finding.get("sha256_12", ""))

    potential = [
        finding
        for finding in workspace_findings + history_findings + image_findings
        if finding.get("classification") == "potential_secret"
    ]
    compromised = [finding for finding in potential if finding.get("matches_current_local_env_key")]

    report = {
        "scanned_at_utc": datetime.now(timezone.utc).isoformat(),
        "redaction": "No matched values are stored; only field names, lengths and 12-char SHA-256 fingerprints.",
        "summary": {
            "tracked_files": len(tracked),
            "workspace_findings_all": len(workspace_findings),
            "workspace_potential_secrets": len(
                [f for f in workspace_findings if f.get("classification") == "potential_secret"]
            ),
            "git_history_potential_secrets": len(
                [f for f in history_findings if f.get("classification") == "potential_secret"]
            ),
            "docker_image_potential_secrets": len(
                [f for f in image_findings if f.get("classification") == "potential_secret"]
            ),
            "current_local_env_matches": len(compromised),
        },
        "workspace_findings": workspace_findings,
        "git_history_findings": history_findings,
        "docker_image_findings": image_findings,
        "current_local_env_matches": compromised,
        "images_scanned": images,
    }
    EVIDENCE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
