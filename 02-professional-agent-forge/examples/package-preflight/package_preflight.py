"""Offline structural preflight for generated professional-agent packages.

This is a contract checker, not a persona evaluator or security scanner.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

VERSION = "0.1.0"
MAX_BYTES = 1024 * 1024
PROFILE_SOURCE = "https://github.com/Aliciawque/openclaw-personalized-agent-forge/blob/15e51e7c05bddf5bf94d69d550b504346721efc0/02-professional-agent-forge/SKILL.md"
REQUIRED = {
    "soul.md": ["Core drive", "Professional beliefs", "Quality standard", "Non-negotiables", "The role's built-in tension"],
    "identity.md": ["Role definition", "Expertise stack", "Communication style by audience", "Decision framework", "Professional boundaries"],
    "memory.md": ["Core methodology", "Domain knowledge", "Templates and common artifacts", "Reference standards", "Common pitfalls"],
    "agents.md": ["Core workflows", "Output format defaults", "Stakeholder protocols", "Escalation rules", "Sample interactions"],
    "tools.md": ["Primary toolstack", "AI-augmented tools", "OpenClaw skill mapping", "Open-source resources", "Tool selection logic", "Recommended MCP integrations"],
}
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
LINK = re.compile(r"!?\[[^\[\]\n]*\]\((<[^>\n]*>|[^\s()]+)(?:\s+\"[^\"\n]*\")?\)")


def normalize(value):
    """Case/punctuation-insensitive contract labels, not fuzzy semantic matching."""
    return " ".join(re.findall(r"\w+", value.casefold(), re.UNICODE))


def escaped(text, index):
    backslashes = 0
    while index > 0 and text[index - 1] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def visible_lines(text):
    """Mask code/comment content in lexical order, preserving line numbers."""
    masked = list(text)
    def blank(start, end):
        for k in range(start, end):
            if masked[k] not in "\r\n":
                masked[k] = " "
    i = 0
    while i < len(text):
        if i == 0 or text[i-1] == "\n":
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            match = FENCE.match(text[i:end])
            if match and not (match[1][0] == "`" and "`" in match[2]):
                char, width = match[1][0], len(match[1])
                close = re.compile(r"^ {0,3}" + re.escape(char) + "{" + str(width) + r",}[ \t\r]*$", re.M).search(text, end + 1)
                stop = close.end() if close else len(text)
                blank(i, stop)
                i = stop
                continue
        if text.startswith("<!--", i):
            close = text.find("-->", i+4)
            stop = close+3 if close >= 0 else len(text)
            blank(i, stop)
            i = stop
            continue
        if text[i] == "`" and not escaped(text, i):
            end = i+1
            while end < len(text) and text[end] == "`":
                end += 1
            close = re.compile(r"(?<!`)`{" + str(end-i) + r"}(?!`)").search(text, end)
            block_break = close and re.search(r"\n[ \t]*\n|\n {0,3}(?:#{1,6}\s|`{3,}|~{3,})", text[end:close.start()])
            if close and not block_break:
                blank(i, close.end())
                i = close.end()
            else:
                i = end
            continue
        i += 1
    yield from enumerate("".join(masked).splitlines(), 1)


def sections(text):
    result, active = [], []
    for number, line in visible_lines(text):
        match = HEADING.match(line)
        if match:
            level = len(match[1])
            while active and active[-1][0] >= level:
                active.pop()
            item = {"heading": match[2], "key": normalize(match[2]), "line": number, "nonempty": False}
            result.append(item)
            active.append((level, item))
        elif re.search(r"[\w\d]", line, re.UNICODE):
            for _, item in active:
                item["nonempty"] = True
    return result


def read_text_file(path):
    """Read one regular UTF-8 file, refusing leaf symlinks and oversized input."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("not a regular file (symlinks are not followed)")
    if before.st_size > MAX_BYTES:
        raise ValueError("file exceeds 1 MiB limit")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        actual = os.fstat(stream.fileno())
        if not stat.S_ISREG(actual.st_mode) or (actual.st_dev, actual.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("file changed during open")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("file exceeds 1 MiB limit")
    return raw.decode("utf-8-sig")


def load_profile(path=None):
    if path is None:
        return {"name": "forge-professional-v1", "source": PROFILE_SOURCE,
                "files": {name: [[label] for label in labels] for name, labels in REQUIRED.items()}}
    try:
        data = json.loads(read_text_file(Path(path)))
    except RecursionError as exc:
        raise ValueError("profile nesting exceeds JSON parser limit") from exc
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not data["name"].strip():
        raise ValueError("profile needs a nonempty name")
    if data.get("source") is not None and (not isinstance(data["source"], str) or len(data["source"]) > 2048):
        raise ValueError("profile source must be text up to 2048 characters or null")
    data["name"].encode("utf-8")
    if data.get("source") is not None:
        data["source"].encode("utf-8")
    files = data.get("files")
    if not isinstance(files, dict) or not 1 <= len(files) <= 20:
        raise ValueError("profile files must contain 1 to 20 entries")
    for filename, groups in files.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.md", filename):
            raise ValueError("profile filenames must be simple .md basenames")
        if not isinstance(groups, list) or not 1 <= len(groups) <= 100:
            raise ValueError("each file needs 1 to 100 heading alias groups")
        seen = set()
        for aliases in groups:
            if not isinstance(aliases, list) or not 1 <= len(aliases) <= 20:
                raise ValueError("each heading needs 1 to 20 aliases")
            keys = []
            for label in aliases:
                if not isinstance(label, str) or len(label) > 200 or not normalize(label):
                    raise ValueError("heading aliases must be nonempty text, at most 200 characters")
                label.encode("utf-8")
                keys.append(normalize(label))
            if len(set(keys)) != len(keys) or any(k in seen for k in keys):
                raise ValueError("profile heading aliases must be unique within a file")
            seen.update(keys)
    return {"name": data["name"], "source": data.get("source"), "files": files}


def link_target_issue(root, target):
    """Check simple local inline link paths, without reading linked content."""
    target = target.removeprefix("<").removesuffix(">")
    try:
        parsed = urlsplit(target)
    except ValueError:
        return "invalid_link", "invalid URL"
    if parsed.scheme and not (len(parsed.scheme) == 1):
        return None  # External URLs are not fetched or validated.
    if parsed.scheme and len(parsed.scheme) == 1:
        return "unsafe_link", "Windows-style local path"
    if parsed.netloc:
        return None
    raw = unquote(parsed.path)
    if not raw:
        return None  # Fragments are deliberately not validated.
    if "\x00" in raw or "\\" in raw or parsed.scheme or raw.startswith("/"):
        return "unsafe_link", "absolute, Windows-style or invalid local path"
    candidate = root / raw
    try:
        relative = candidate.resolve(strict=False).relative_to(root)
    except (ValueError, RuntimeError, OSError):
        return "unsafe_link", "local path escapes package or cannot be resolved"
    # Check lexical components as well as resolved containment, so an internal
    # symlink is refused too. '..' is allowed only when it stays inside root.
    current = root
    try:
        for part in Path(raw).parts:
            if not current.is_dir():
                return "unreadable_link", "non-directory intermediate path component"
            if part == "..":
                current = current.parent
                if not current.is_relative_to(root):
                    return "unsafe_link", "local path escapes package"
            elif part != ".":
                current = current / part
                info = current.lstat()
                if stat.S_ISLNK(info.st_mode):
                    return "unsafe_link", "symlink in local link path"
        info = (root / relative).stat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            return "unsafe_link", "local target is not a regular file or directory"
    except FileNotFoundError:
        return "missing_link", "local target does not exist"
    except OSError as exc:
        return "unreadable_link", type(exc).__name__
    return None


def audit(root, profile=None, files_only=False):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("package root must be a directory, not a leaf symlink")
    root = root.resolve()
    profile = profile or load_profile()
    findings, checked = [], []
    def add(file, code, message, line=None):
        findings.append({"file": file, "code": code, "message": message, "line": line})
    for name, groups in profile["files"].items():
        try:
            text = read_text_file(root / name)
        except (OSError, UnicodeError, ValueError) as exc:
            add(name, "unreadable_file", f"{type(exc).__name__}: {exc}")
            continue
        checked.append(name)
        parsed = sections(text)
        if not text.strip():
            add(name, "empty_file", "required file is empty")
        if not files_only:
            for aliases in groups:
                accepted = {normalize(a) for a in aliases}
                matches = [s for s in parsed if s["key"] in accepted]
                if not matches:
                    add(name, "missing_section", "expected heading: " + " / ".join(aliases))
                elif len(matches) > 1:
                    add(name, "duplicate_section", "multiple headings match: " + " / ".join(aliases), matches[0]["line"])
                elif not matches[0]["nonempty"]:
                    add(name, "empty_section", "no prose outside fenced examples under: " + matches[0]["heading"], matches[0]["line"])
        for number, line in visible_lines(text):
            for match in LINK.finditer(line):
                if escaped(line, match.start()):
                    continue
                issue = link_target_issue(root, match[1])
                if issue:
                    add(name, *issue, line=number)
    return {"schema_version": 1, "tool_version": VERSION, "profile": profile["name"],
            "profile_source": profile.get("source"), "mode": "files-only" if files_only else "structural",
            "passed": not findings, "checked_files": checked, "findings": findings,
            "limits": ["No semantic quality, credential or security scan", "Only ATX headings and simple inline Markdown links",
                       "No remote URL, reference-link or fragment validation", "No linked content reads; no writes", "Not safe against concurrent malicious directory replacement"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--profile", help="JSON contract with heading aliases; see README")
    parser.add_argument("--files-only", action="store_true", help="skip heading contract; still check files and supported local links")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    args = parser.parse_args(argv)
    try:
        result = audit(args.package, load_profile(args.profile), args.files_only)
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"passed": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=True))
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(f"{'PASS' if result['passed'] else 'FAIL'}: {result['profile']} ({result['mode']})")
        for item in result["findings"]:
            print(f"{item['file']}:{item['line'] or '-'} {item['code']}: {item['message']}")
        print("Structural checks only; not a deployment or security approval.")
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
