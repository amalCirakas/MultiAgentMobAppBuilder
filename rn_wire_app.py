"""
After Crew codegen for MODULE=builder: ensure root App.tsx renders the generated screen.

The RN CLI ships a boilerplate App (New App Screen). UIScreenAgent only writes
src/screens/AppScreen.tsx, so the device keeps showing the template until App.tsx imports it.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_SCREEN_REL = Path("src/screens/AppScreen.tsx")

# Android RCTText rejects accessibilityRole="heading" (see ViewManagersPropertyCache / Fabric).
_HEADING_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ('accessibilityRole="heading"', 'accessibilityRole="header"'),
    ("accessibilityRole='heading'", "accessibilityRole='header'"),
    ("accessibilityRole={\"heading\"}", "accessibilityRole={\"header\"}"),
    ("accessibilityRole={'heading'}", "accessibilityRole={'header'}"),
)


def sanitize_generated_accessibility(build_root: Path) -> int:
    """
    Post-process generated src/**/*.tsx to replace invalid Android roles (LLM slip-ups).
    Returns number of files modified.
    """
    src = build_root / "src"
    if not src.is_dir():
        return 0

    changed = 0
    for path in sorted(src.rglob("*.tsx")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        for old, repl in _HEADING_REPLACEMENTS:
            new = new.replace(old, repl)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print(
                f"[SANITIZE] Fixed accessibilityRole heading→header in {path.relative_to(build_root)}",
                flush=True,
            )
    return changed


APP_TSX_TEMPLATE = """/**
 * Wired by multiAgentApp/build_app.py after Crew (MODULE=builder).
 * Edit src/screens/AppScreen.tsx / agents to change UI—not the RN template screen.
 */
import React from 'react';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import AppScreen from './src/screens/AppScreen';

export default function App(): React.ReactElement {
  return (
    <SafeAreaProvider>
      <AppScreen />
    </SafeAreaProvider>
  );
}
"""


def wire_builder_app_tsx(build_root: Path, *, screen_relative: Path = DEFAULT_SCREEN_REL) -> bool:
    """
    Rewrite root App.tsx so Metro loads the Crew-generated AppScreen default export.
    Returns True when App.tsx was written.
    """
    screen = build_root / screen_relative
    if not screen.is_file():
        print(
            f"[WIRE] Missing {screen_relative.as_posix()}; skipping App.tsx rewrite.",
            flush=True,
        )
        return False

    app_tsx = build_root / "App.tsx"
    app_tsx.write_text(APP_TSX_TEMPLATE.rstrip() + "\n", encoding="utf-8")
    print(
        "[WIRE] Rewrote App.tsx to render ./src/screens/AppScreen — reload Metro / rerun the native app.",
        flush=True,
    )
    return True
