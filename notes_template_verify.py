"""Static checks for generated deterministic Notes templates."""

from __future__ import annotations

import sys
from pathlib import Path


def verify_notes_templates(build_root: Path) -> None:
    root = build_root.resolve()
    service = root / "src" / "db" / "appService.ts"
    screen = root / "src" / "screens" / "AppScreen.tsx"

    missing = [str(p.relative_to(root)) for p in (service, screen) if not p.is_file()]
    if missing:
        raise RuntimeError("[NOTES-TEMPLATE-QA] Missing generated files: " + ", ".join(missing))

    svc = service.read_text(encoding="utf-8")
    scr = screen.read_text(encoding="utf-8")

    errors: list[str] = []
    if "id: `offline-${Date.now()}`" in svc:
        errors.append("appService.ts uses timestamp-only offline ids")
    for snippet in ("let offlineSeq", "makeOfflineId()", "mergeNotesById", "upsertOfflineNote"):
        if snippet not in svc:
            errors.append(f"appService.ts missing {snippet}")
    if "offlineNotes.push(local)" in svc:
        errors.append("appService.ts appends offline notes directly instead of upserting")
    if "return [...remote, ...offlineNotes]" in svc:
        errors.append("appService.ts returns remote + offline without mergeNotesById")

    if "mergeNotesById([...prev, created])" not in scr:
        errors.append("AppScreen.tsx does not merge created notes by id")
    if "key={noteKey(item, i)}" not in scr or "return `${n.id ?? 'row'}-${index}`;" not in scr:
        errors.append("AppScreen.tsx does not use defensive unique render keys")
    if "setNotes((prev) => [...prev, created])" in scr:
        errors.append("AppScreen.tsx appends created notes directly")

    if errors:
        raise RuntimeError("[NOTES-TEMPLATE-QA] " + "; ".join(errors))

    print("[NOTES-TEMPLATE-QA] Offline note uniqueness checks OK.", flush=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python3 notes_template_verify.py BUILD_ROOT")
        return 1
    try:
        verify_notes_templates(Path(sys.argv[1]))
    except Exception as exc:  # noqa: BLE001 - CLI diagnostic
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
