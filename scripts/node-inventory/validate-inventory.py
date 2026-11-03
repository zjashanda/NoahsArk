#!/usr/bin/env python3
"""Fail-closed validator for the NoahsArk node inventory.

Validates either the commit-safe public inventory or a decrypted private
inventory. It never prints field values, because a validation error must not
turn into a secret leak.

Exit codes:
  0  valid
  1  invalid inventory (schema, duplicate keys, forbidden secret material)
  2  usage / missing dependency
  3  valid but reference resolution could not be completed
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    sys.stderr.write("ERROR dependency=pyyaml\n")
    raise SystemExit(2)

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError
except ImportError:  # pragma: no cover - dependency guard
    sys.stderr.write("ERROR dependency=jsonschema\n")
    raise SystemExit(2)

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "config" / "node-inventory" / "schema"
SCHEMA_BY_KIND = {
    "public": SCHEMA_DIR / "node-inventory.public.schema.json",
    "private": SCHEMA_DIR / "node-inventory.private.schema.json",
}

# Key names that indicate an embedded secret value. Credential *references*
# (credential_ref) are the only allowed indirection and are not matched here.
FORBIDDEN_KEY_RE = re.compile(
    r"(?i)^(password|passwd|pass|passphrase|secret|client_secret|token|bearer|"
    r"api[_-]?key|private[_-]?key|private[_-]?key[_-]?path|ssh[_-]?password|"
    r"identity[_-]?file|id_rsa|id_ed25519|authorized_keys)$"
)
FORBIDDEN_VALUE_RES = (
    ("private_key_block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("age_identity", re.compile(r"AGE-SECRET-KEY-1[0-9A-Z]{20,}")),
    ("openssh_private", re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----")),
    ("public_key_blob", re.compile(r"\b(ssh-(rsa|ed25519|dss)|ecdsa-sha2-nistp256) AAAA")),
    ("inline_password", re.compile(r"(?i)\b(password|passphrase|passwd)\s*[:=]\s*\S+")),
    ("ipv4_literal", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("user_at_host", re.compile(r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
)
PUBLIC_FORBIDDEN_KEYS = {
    "host",
    "hostname",
    "host_ref",
    "ip",
    "address",
    "user",
    "username",
    "user_ref",
    "credential_ref",
    "agent_url",
    "port",
    "ssh_command",
}


def fail(code: int, message: str) -> "None":
    sys.stderr.write(f"FAIL {message}\n")
    raise SystemExit(code)


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except OSError as exc:
        fail(2, f"cannot_read inventory errno={exc.errno}")
    except yaml.YAMLError:
        # Do not echo parser text: it may quote the offending line.
        fail(1, "yaml_parse_error")


def iter_key_paths(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            yield key_text, child
            yield from iter_key_paths(child, path + (key_text,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_key_paths(child, path + (f"[{index}]",))


def check_forbidden(kind: str, document: Any) -> list[str]:
    errors: list[str] = []
    for key, child in iter_key_paths(document):
        if FORBIDDEN_KEY_RE.match(key):
            errors.append(f"forbidden_key:{key}")
        if kind == "public" and key in PUBLIC_FORBIDDEN_KEYS:
            errors.append(f"public_forbidden_key:{key}")
        if isinstance(child, str):
            for name, pattern in FORBIDDEN_VALUE_RES:
                if name == "ipv4_literal" and kind == "private":
                    # A literal host is allowed only inside the encrypted file.
                    continue
                if name == "user_at_host" and kind == "private":
                    continue
                if pattern.search(child):
                    errors.append(f"forbidden_value:{name}:key={key}")
                    break
    return errors


def check_duplicates(document: Any) -> list[str]:
    errors: list[str] = []
    nodes = document.get("nodes", []) if isinstance(document, dict) else []
    if not isinstance(nodes, list):
        return ["nodes_not_list"]
    seen_ids: dict[str, int] = {}
    seen_aliases: dict[str, int] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = node.get("node_id")
        alias = node.get("ssh_alias")
        if isinstance(node_id, str):
            if node_id in seen_ids:
                errors.append(f"duplicate_node_id:index={index}:first={seen_ids[node_id]}")
            seen_ids[node_id] = index
        if isinstance(alias, str):
            if alias in seen_aliases:
                errors.append(f"duplicate_ssh_alias:index={index}:first={seen_aliases[alias]}")
            seen_aliases[alias] = index
    return errors


def check_refs(document: Any) -> tuple[list[str], list[str]]:
    """Return (failures, unknowns). Never prints resolved values."""
    failures: list[str] = []
    unknowns: list[str] = []
    nodes = document.get("nodes", []) if isinstance(document, dict) else []
    if not isinstance(nodes, list):
        return ["nodes_not_list"], []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = node.get("node_id")
        if not isinstance(node_id, str):
            continue
        for field in ("host_ref", "user_ref"):
            ref = node.get(field)
            if not isinstance(ref, str):
                continue
            status = resolve_ref(ref)
            if status == "unresolved":
                failures.append(f"{field}:node={node_id}")
            elif status == "unknown":
                unknowns.append(f"{field}:node={node_id}")
        credential = node.get("credential_ref")
        if isinstance(credential, str):
            status = resolve_credential(credential)
            if status == "unresolved":
                failures.append(f"credential_ref:node={node_id}")
            elif status == "unknown":
                unknowns.append(f"credential_ref:node={node_id}")
        agent_url = node.get("agent_url")
        if isinstance(agent_url, str) and agent_url:
            # Presence only; reachability is never asserted here.
            if not agent_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
                failures.append(f"agent_url_scheme:node={node_id}")
    return failures, unknowns


def resolve_ref(ref: str) -> str:
    if ref.startswith("env:"):
        name = ref[4:]
        return "ok" if os.environ.get(name) else "unresolved"
    if ref.startswith("file:"):
        path = Path(ref[5:])
        if not path.is_file():
            return "unresolved"
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
        except OSError:
            return "unresolved"
        return "ok" if mode & 0o077 == 0 else "unresolved"
    if ref.startswith("literal:"):
        return "ok"
    return "unknown"


def resolve_credential(ref: str) -> str:
    if ref.startswith("ssh-agent:"):
        socket = os.environ.get("SSH_AUTH_SOCK")
        if not socket:
            return "unresolved"
        try:
            result = subprocess.run(
                ["ssh-add", "-l"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "unresolved"
        if result.returncode != 0:
            return "unresolved"
        wanted = ref.split(":", 1)[1]
        # Match the loaded key comment/name without printing any fingerprint.
        for line in result.stdout.splitlines():
            parts = line.split(maxsplit=2)
            if len(parts) == 3 and wanted in parts[2]:
                return "ok"
        return "unresolved"
    if ref.startswith("keyfile:"):
        path = Path(ref[8:])
        if not path.is_file():
            return "unresolved"
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
        except OSError:
            return "unresolved"
        return "ok" if mode & 0o077 == 0 else "unresolved"
    if ref.startswith("vault:"):
        return "unknown"
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(SCHEMA_BY_KIND), default="public")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--check-refs", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit a machine summary")
    args = parser.parse_args()

    schema_path = SCHEMA_BY_KIND[args.kind]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail(2, f"schema_unreadable kind={args.kind}")

    try:
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
    except SchemaError:
        fail(2, f"schema_invalid kind={args.kind}")

    document = load_yaml(args.inventory)
    errors: list[str] = []

    for error in validator.iter_errors(document):
        # Only path + validator are printed. Instance values stay hidden.
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path
        )
        errors.append(f"schema:{location}:{error.validator}")

    if isinstance(document, dict):
        errors.extend(check_forbidden(args.kind, document))
        errors.extend(check_duplicates(document))
    else:
        errors.append("root_not_mapping")

    failures: list[str] = []
    unknowns: list[str] = []
    if args.check_refs and not errors and args.kind == "private":
        failures, unknowns = check_refs(document)

    node_count = 0
    if isinstance(document, dict) and isinstance(document.get("nodes"), list):
        node_count = len(document["nodes"])

    if args.json:
        print(
            json.dumps(
                {
                    "kind": args.kind,
                    "nodes": node_count,
                    "errors": errors,
                    "ref_failures": failures,
                    "ref_unknowns": unknowns,
                },
                ensure_ascii=False,
            )
        )
    else:
        for item in errors:
            print(f"ERROR {item}")
        for item in failures:
            print(f"ERROR ref={item}")
        for item in unknowns:
            print(f"WARN ref=unverified:{item}")
        print(f"KIND={args.kind} NODES={node_count}")

    if errors or failures:
        print("RESULT=FAIL")
        return 1
    if unknowns:
        print("RESULT=INCOMPLETE")
        return 3
    print("RESULT=OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
