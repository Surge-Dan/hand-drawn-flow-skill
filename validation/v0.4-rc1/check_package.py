"""Check Skill structure and archive fidelity, never image quality.

Run from any directory with Python, PyYAML and Git available.
"""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import hashlib
import json
import re
import subprocess

import yaml


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    root = Path(__file__).resolve().parents[2]
    skill = root / "hand-drawn-flow"
    entry = (skill / "SKILL.md").read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", entry, re.S)
    require(match is not None, "Missing YAML frontmatter")
    meta = yaml.safe_load(match.group(1))
    require(meta["name"] == skill.name, "Skill name differs from directory")
    require(isinstance(meta["description"], str) and
            0 < len(meta["description"]) <= 1024, "Invalid description")
    version = str(meta["metadata"]["version"])
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-z0-9.]+)?", version),
            "Unsafe or invalid version")

    ui = yaml.safe_load((skill / "agents/openai.yaml").read_text(encoding="utf-8"))
    require(25 <= len(ui["interface"]["short_description"]) <= 64,
            "UI description must be 25–64 characters")
    require("$hand-drawn-flow" in ui["interface"]["default_prompt"],
            "Default prompt lacks invocation")
    require(ui["policy"]["allow_implicit_invocation"] is True,
            "Unexpected invocation policy")
    subprocess.run(["git", "diff", "--check"], cwd=root, check=True)

    files = sorted(p for p in skill.rglob("*") if p.is_file())
    allowed = {".md", ".yaml"}  # This release ships instructions only.
    links = 0
    for path in files:
        require(not path.is_symlink(), f"Unexpected symlink: {path}")
        require(path.suffix in allowed, f"Unreviewed package file: {path}")
        require(path.resolve().is_relative_to(skill.resolve()),
                f"Package file escapes root: {path}")
        if path.suffix != ".md":
            continue
        for dest in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in dest or dest.startswith("#"):
                continue
            target = (path.parent / dest.split("#")[0]).resolve()
            require(target.is_relative_to(skill.resolve()) and target.is_file(),
                    f"Broken or external local reference: {path}: {dest}")
            links += 1

    archive = root / "dist" / f"hand-drawn-flow-v{version}.zip"
    archive.parent.mkdir(exist_ok=True)
    expected = {p.relative_to(root).as_posix(): p.read_bytes() for p in files}
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as out:
        for name, content in expected.items():
            info = ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            out.writestr(info, content)
    with ZipFile(archive) as out:
        require(sorted(out.namelist()) == sorted(expected), "Archive members differ")
        require(out.testzip() is None, "Archive CRC failure")
        for name, content in expected.items():
            require(out.read(name) == content, f"Archive content differs: {name}")

    result = {
        "version": version,
        "structure_validation": "passed",
        "ui_validation": "passed",
        "diff_check": "passed",
        "internal_links_checked": links,
        "archive_file_count": len(files),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_source_hashes_match": True,
        "image_quality_validation": "not_performed_by_this_checker",
        "global_install": False,
    }
    (Path(__file__).parent / "checks.json").write_bytes(
        (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
