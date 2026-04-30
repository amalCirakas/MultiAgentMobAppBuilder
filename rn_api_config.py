"""Emit src/config/api.ts so builder codegen can resolve getApiBase() before Crew runs."""

from __future__ import annotations

from pathlib import Path

_API_TS = """\
import {NativeModules, Platform} from 'react-native';

/**
 * Scaffold Node listener (build_app-generated `server/`). Default PORT=3090.
 * - Android emulator: host loopback via 10.0.2.2
 * - iOS Simulator: localhost
 * - Physical device: use Metro's host IP when available, or `adb reverse tcp:3090 tcp:3090`.
 */
const API_PORT = 3090;

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function metroHost(): string | null {
  const scriptURL = NativeModules.SourceCode?.scriptURL;
  if (typeof scriptURL !== 'string') {
    return null;
  }
  const match = scriptURL.match(/^[a-z]+:\\/\\/([^/:?#]+)/i);
  return match?.[1] ?? null;
}

export function getApiBaseCandidates(): string[] {
  const hosts: string[] = [];
  const host = metroHost();
  if (__DEV__ && host) {
    hosts.push(host);
  }
  if (Platform.OS === 'android') {
    hosts.push('10.0.2.2', '127.0.0.1', 'localhost');
  } else {
    hosts.push('localhost', '127.0.0.1');
  }
  return unique(hosts).map((h) => `http://${h}:${API_PORT}`);
}

export function getApiBase(): string {
  return getApiBaseCandidates()[0] ?? `http://localhost:${API_PORT}`;
}

export function notesApiRoot(): string {
  return `${getApiBase()}/api/v1/notes`;
}
"""


def write_builder_api_config(build_root: Path) -> None:
    out = build_root / "src" / "config" / "api.ts"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_API_TS, encoding="utf-8")
