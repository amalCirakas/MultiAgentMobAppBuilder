"""Debug Android overlays so plaintext HTTP can reach local Node during RN dev."""

from __future__ import annotations

from pathlib import Path

# Aligns typical RN CLI debug overlays; merges with main/AndroidManifest.xml.
RN_DEBUG_MERGE = """\
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    <application
        android:usesCleartextTraffic="true"
        tools:ignore="GoogleAppIndexingWarning"/>
</manifest>


"""


def _merge_cleartext_into_existing(debug_manifest: Path) -> None:
    text = debug_manifest.read_text(encoding="utf-8")
    if "usesCleartextTraffic" in text:
        return
    if "<application " not in text and "<application\n" not in text:
        return
    if 'xmlns:tools="' not in text:
        text = text.replace(
            '<manifest ',
            '<manifest xmlns:tools="http://schemas.android.com/tools" ',
            1,
        )
    text = text.replace("<application ", '<application android:usesCleartextTraffic="true" ', 1)
    debug_manifest.write_text(text, encoding="utf-8")


def ensure_android_http_debug_manifest(build_root: Path) -> None | Path:
    """
    Prefer debug-folder manifest merge so release APK stays strict unless you opt in separately.
    Returns debug manifest path when touched, or None if android/app is missing (no RN scaffold).
    """
    android_app = build_root / "android" / "app"
    if not android_app.is_dir():
        return None

    dbg = android_app / "src" / "debug" / "AndroidManifest.xml"
    dbg.parent.mkdir(parents=True, exist_ok=True)

    if dbg.is_file():
        _merge_cleartext_into_existing(dbg)
    else:
        dbg.write_text(RN_DEBUG_MERGE, encoding="utf-8")
    return dbg
