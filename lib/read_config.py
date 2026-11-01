#!/usr/bin/env python3
"""Read a single validated directory setting from the switcher's XML config."""
import os
import sys
import xml.etree.ElementTree as ET


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("accounts-dir", "shared-home"):
        raise ValueError("expected a config file and a supported setting")
    path, key = sys.argv[1:]
    with open(path, "rb") as config:
        data = config.read(65537)
    if len(data) > 65536 or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("config is too large or contains an XML declaration that is not allowed")
    root = ET.fromstring(data)
    if root.tag != "codex-account-config":
        raise ValueError("expected a codex-account-config root element")
    entries = root.findall(key)
    if len(entries) != 1 or len(entries[0]) or not entries[0].text or not entries[0].text.strip():
        raise ValueError(f"expected exactly one nonempty {key} element")
    value = os.path.expanduser(entries[0].text.strip())
    if not os.path.isabs(value) or '\n' in value or '\r' in value:
        raise ValueError(f"{key} must be an absolute path or start with ~/")
    print(os.path.normpath(value))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ET.ParseError) as error:
        print(f"Invalid switcher config: {error}", file=sys.stderr)
        sys.exit(1)
