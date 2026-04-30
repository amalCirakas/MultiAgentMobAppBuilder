"""
After MODULE=builder Crew: overwrite notes REST wiring for fullstack+node so codegen drift
(undefined imports, duplicated /api/v1 paths) cannot break the scaffold.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

APP_TYPES_TS = """\
/** Pipeline-generated — ISO strings align with scaffold server JSON */
export interface Note {
  id: string;
  title: string;
  body?: string;
  createdAt?: string;
  updatedAt?: string;
  pendingSync?: boolean;
}
"""

APP_VALIDATION_TS = """\
export type NoteDraft = {title: string; body?: string};

/** Predicate for compose form before POST (title required server-side too). */
export function validateNoteDraft(d: Partial<NoteDraft>): boolean {
  return typeof d.title === 'string' && d.title.trim().length > 0;
}

/** Back-compat alias for MODULE=builder staged validation naming */
export type AppValidationError = {title?: string; body?: string};

export function validateApp(app: Partial<NoteDraft>): AppValidationError[] {
  const errors: AppValidationError[] = [];
  if (!app.title?.trim()) {
    errors.push({title: 'Title is required'});
  }
  return errors;
}
"""

APP_SERVICE_TS = """\
import {getApiBaseCandidates} from '../config/api';

import type {Note} from '../../_contracts/app.types';

export type NoteCreate = {title: string; body?: string};
export type NotePatch = {title?: string; body?: string};

export class OfflineApiError extends Error {
  constructor(
    message = 'Offline: start the Node API, or run adb reverse tcp:3090 tcp:3090 for a USB Android device.',
  ) {
    super(message);
    this.name = 'OfflineApiError';
  }
}

const offlineNotes: Note[] = [];
let offlineSeq = 0;
const REQUEST_TIMEOUT_MS = 1200;

function unique<T>(items: T[]): T[] {
  return [...new Set(items)];
}

function makeOfflineId(): string {
  offlineSeq += 1;
  const rand = Math.random().toString(36).slice(2, 8);
  return `offline-${Date.now()}-${offlineSeq}-${rand}`;
}

export function mergeNotesById(items: Note[]): Note[] {
  const byId = new Map<string, Note>();
  for (const item of items) {
    if (!item.id) {
      continue;
    }
    byId.set(item.id, {...byId.get(item.id), ...item});
  }
  return [...byId.values()];
}

function upsertOfflineNote(note: Note): Note {
  const idx = offlineNotes.findIndex((n) => n.id === note.id);
  if (idx >= 0) {
    offlineNotes[idx] = {...offlineNotes[idx], ...note};
    return offlineNotes[idx];
  }
  offlineNotes.push(note);
  return note;
}

function apiRoots(): string[] {
  return unique(getApiBaseCandidates().map((base) => `${base.replace(/\\/+$/, '')}/api/v1/notes`));
}

async function readError(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (j && typeof j.error === 'string') {
      return j.error;
    }
    return res.statusText || `HTTP ${res.status}`;
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

async function fetchJson<T>(path = '', init?: RequestInit): Promise<T> {
  let lastError: unknown;
  for (const root of apiRoots()) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const res = await fetch(`${root}${path}`, {...init, signal: controller.signal});
      if (!res.ok) {
        throw new Error(await readError(res));
      }
      if (res.status === 204) {
        return undefined as T;
      }
      return res.json();
    } catch (e: unknown) {
      lastError = e;
    } finally {
      clearTimeout(timeout);
    }
  }
  const msg = lastError instanceof Error ? lastError.message : String(lastError);
  throw new OfflineApiError(
    msg.includes('Network request failed') || msg.includes('Aborted')
      ? undefined
      : `API unreachable: ${msg}`,
  );
}

/** GET …/api/v1/notes — `notesApiRoot()` is exactly the collection URL; do NOT append /api/v1/notes again. */
export async function listNotes(): Promise<Note[]> {
  try {
    const remote = await fetchJson<Note[]>();
    return mergeNotesById([...remote, ...offlineNotes]);
  } catch (e: unknown) {
    if (e instanceof OfflineApiError) {
      return mergeNotesById(offlineNotes);
    }
    throw e;
  }
}

/** POST …/api/v1/notes */
export async function createRecord(note: NoteCreate): Promise<Note> {
  try {
    return await fetchJson<Note>('', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(note),
    });
  } catch (e: unknown) {
    if (!(e instanceof OfflineApiError)) {
      throw e;
    }
    const t = new Date().toISOString();
    const local: Note = {
      id: makeOfflineId(),
      title: note.title,
      body: note.body,
      createdAt: t,
      updatedAt: t,
      pendingSync: true,
    };
    return upsertOfflineNote(local);
  }
}

/** PATCH …/api/v1/notes/:id */
export async function updateRecord(id: string, patch: NotePatch): Promise<Note> {
  if (id.startsWith('offline-')) {
    const idx = offlineNotes.findIndex((n) => n.id === id);
    if (idx >= 0) {
      offlineNotes[idx] = {...offlineNotes[idx], ...patch, updatedAt: new Date().toISOString()};
      return offlineNotes[idx];
    }
  }
  return fetchJson<Note>(`/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(patch),
  });
}

/** DELETE …/api/v1/notes/:id */
export async function deleteNote(id: string): Promise<void> {
  const localIdx = offlineNotes.findIndex((n) => n.id === id);
  if (localIdx >= 0) {
    offlineNotes.splice(localIdx, 1);
    return;
  }
  await fetchJson<void>(`/${encodeURIComponent(id)}`, {method: 'DELETE'});
}

export async function queueAppSync(): Promise<void> {
  return Promise.resolve();
}
"""

APP_SCREEN_TS = """\
import React, {useEffect, useState, useCallback} from 'react';
import {
  View,
  Text,
  TextInput,
  ScrollView,
  ActivityIndicator,
  Pressable,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';

import type {Note} from '../../_contracts/app.types';
import {validateNoteDraft} from '../validation/appValidation';
import {
  listNotes,
  createRecord,
  deleteNote,
  mergeNotesById,
} from '../db/appService';

function noteKey(n: Note, index: number): string {
  return `${n.id ?? 'row'}-${index}`;
}

export default function AppScreen(): React.JSX.Element {
  const [notes, setNotes] = useState<Note[]>([]);
  const [draft, setDraft] = useState({title: '', body: ''});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    setStatus(null);
    setBusy(true);
    try {
      const list = await listNotes();
      setNotes(Array.isArray(list) ? mergeNotesById(list) : []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleSave = async (): Promise<void> => {
    setError(null);
    setStatus(null);
    if (!validateNoteDraft(draft)) {
      setError('Enter a note title.');
      return;
    }
    setBusy(true);
    try {
      const created = await createRecord({
        title: draft.title.trim(),
        body: draft.body?.trim(),
      });
      setDraft({title: '', body: ''});
      setNotes((prev) => mergeNotesById([...prev, created]));
      setStatus(
        created.pendingSync
          ? 'Saved offline. Start the Node API; for USB Android run adb reverse tcp:3090 tcp:3090.'
          : 'Saved to the Node API.',
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: string): Promise<void> => {
    setError(null);
    setStatus(null);
    setBusy(true);
    try {
      await deleteNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'left', 'right']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.shell}>
        <ScrollView keyboardShouldPersistTaps="handled" contentInsetAdjustmentBehavior="automatic">
          <Text style={styles.brand}>Notes</Text>
          <Text style={styles.sub}>Local REST · scaffold server</Text>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>New note</Text>
            <TextInput
              testID="note-title-input"
              accessibilityLabel="Note title"
              placeholder="Title"
              placeholderTextColor="#6b7580"
              value={draft.title}
              style={styles.input}
              onChangeText={(title) => setDraft({...draft, title})}
            />
            <TextInput
              testID="note-body-input"
              accessibilityLabel="Note body"
              placeholder="Body (optional)"
              placeholderTextColor="#6b7580"
              multiline
              style={[styles.input, styles.multi]}
              value={draft.body}
              onChangeText={(body) => setDraft({...draft, body})}
            />
            <Pressable
              testID="note-save"
              accessibilityLabel="Save note"
              accessibilityRole="button"
              style={({pressed}) => [styles.saveBtn, pressed && styles.saveBtnPressed]}
              onPress={() => void handleSave()}>
              <Text style={styles.saveLbl}>SAVE</Text>
            </Pressable>
          </View>

          <Text style={styles.sectionLbl}>Saved</Text>
          {notes.map((item, i) => (
            <View
              style={styles.cardItem}
              key={noteKey(item, i)}
              testID={`note-row-${noteKey(item, i)}`}>
              <View style={styles.rowTop}>
                <Text style={styles.itemTitle}>{item.title}</Text>
                <Pressable
                  testID={`note-delete-${noteKey(item, i)}`}
                  accessibilityRole="button"
                  accessibilityLabel="Delete note"
                  style={styles.delMini}
                  onPress={() => void handleDelete(item.id)}>
                  <Text style={styles.delMiniTxt}>Delete</Text>
                </Pressable>
              </View>
              {item.body ? (
                <Text style={styles.itemBody}>{item.body}</Text>
              ) : null}
              {item.pendingSync ? (
                <Text style={styles.pending}>Pending sync</Text>
              ) : null}
            </View>
          ))}
        </ScrollView>
        {busy ? (
          <View style={styles.loading}>
            <ActivityIndicator color="#62aef7" size="large" />
          </View>
        ) : null}
        {status ? (
          <View style={styles.statusBar} testID="note-status">
            <Text style={styles.statusText}>{status}</Text>
          </View>
        ) : null}
        {error ? (
          <View style={styles.errBar} testID="note-error">
            <Text style={styles.errText}>{error}</Text>
          </View>
        ) : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const BG = '#0b0f14';
const CARD = '#151c26';
const ACCENT = '#2b7bdc';
const MUTED = '#8b939e';

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: BG},
  shell: {flex: 1},
  loading: {...StyleSheet.absoluteFill, justifyContent: 'center', alignItems: 'center'},
  brand: {
    marginHorizontal: 20,
    marginTop: 12,
    fontSize: 28,
    fontWeight: '700',
    color: '#e8eef7',
  },
  sub: {
    marginHorizontal: 20,
    marginBottom: 12,
    fontSize: 14,
    color: MUTED,
  },
  card: {
    marginHorizontal: 16,
    padding: 16,
    borderRadius: 14,
    backgroundColor: CARD,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#232d3d',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.35,
    shadowRadius: 12,
    shadowOffset: {width: 0, height: 6},
    elevation: 8,
  },
  cardTitle: {color: ACCENT, fontWeight: '600', marginBottom: 10, fontSize: 15},
  input: {
    borderWidth: 1,
    borderColor: '#2a3544',
    borderRadius: 10,
    padding: 12,
    color: '#e8eef7',
    marginBottom: 10,
    backgroundColor: '#0f141c',
  },
  multi: {minHeight: 88, textAlignVertical: 'top'},
  saveBtn: {
    backgroundColor: ACCENT,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveBtnPressed: {opacity: 0.87},
  saveLbl: {color: '#fff', fontWeight: '700', letterSpacing: 0.8, fontSize: 15},
  sectionLbl: {
    marginHorizontal: 20,
    marginVertical: 8,
    color: MUTED,
    fontSize: 13,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  cardItem: {
    marginHorizontal: 16,
    marginBottom: 10,
    padding: 14,
    borderRadius: 12,
    backgroundColor: '#111822',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#243041',
  },
  rowTop: {flexDirection: 'row', justifyContent: 'space-between', gap: 8},
  itemTitle: {color: '#e8eef7', flex: 1, fontSize: 17, fontWeight: '600'},
  itemBody: {color: '#cfd6df', marginTop: 8, fontSize: 15, lineHeight: 21},
  pending: {color: '#facc15', marginTop: 8, fontSize: 12, fontWeight: '600'},
  delMini: {paddingHorizontal: 10, justifyContent: 'center'},
  delMiniTxt: {color: '#f07373', fontWeight: '600', fontSize: 13},
  statusBar: {
    padding: 12,
    backgroundColor: '#11251a',
    borderTopWidth: 1,
    borderColor: '#1f5737',
  },
  statusText: {color: '#86efac', textAlign: 'center'},
  errBar: {
    padding: 12,
    backgroundColor: '#2e1518',
    borderTopWidth: 1,
    borderColor: '#4a2430',
  },
  errText: {color: '#fca5a5', textAlign: 'center'},
});
"""

E2E_APP_TS = """\
/**
 * E2E scaffold: install Detox (`npm install --save-dev detox`) to target wired testIDs in
 * `src/screens/AppScreen.tsx`: `note-save`, `note-title-input`, `note-body-input`,
 * `note-status`, `note-error`.
 */

export {};

"""

DEV_FULLSTACK_SH = """\
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[dev-fullstack] Starting Node API on http://localhost:3090"
(
  cd "$ROOT/server"
  if [ ! -d node_modules ]; then
    npm install
  fi
  npm start
) &
API_PID=$!

cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "[dev-fullstack] API pid: $API_PID"
echo "[dev-fullstack] In another terminal run:"
echo "  cd $ROOT && npm start"
echo "  # USB Android physical device only:"
echo "  adb reverse tcp:3090 tcp:3090"
echo "  cd $ROOT && npx react-native run-android"
wait "$API_PID"
"""


def _manifest_allows_wire(build_root: Path) -> bool:
    mf = build_root / "build-manifest.json"
    if not mf.is_file():
        return False
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    stack = data.get("stack")
    backend = data.get("backend_runtime")
    return stack == "fullstack" and backend == "node"


def wire_fullstack_notes_stack(build_root: Path) -> bool:
    """Return True when scaffolded notes files were written."""
    if not _manifest_allows_wire(build_root):
        return False

    root = Path(build_root)
    ctr = root / "_contracts" / "app.types.ts"
    val = root / "src" / "validation" / "appValidation.ts"
    svc = root / "src" / "db" / "appService.ts"
    scr = root / "src" / "screens" / "AppScreen.tsx"

    ctr.parent.mkdir(parents=True, exist_ok=True)
    val.parent.mkdir(parents=True, exist_ok=True)
    svc.parent.mkdir(parents=True, exist_ok=True)
    scr.parent.mkdir(parents=True, exist_ok=True)

    ctr.write_text(APP_TYPES_TS.strip() + "\n", encoding="utf-8")
    val.write_text(APP_VALIDATION_TS.strip() + "\n", encoding="utf-8")
    svc.write_text(APP_SERVICE_TS.strip() + "\n", encoding="utf-8")
    scr.write_text(APP_SCREEN_TS.strip() + "\n", encoding="utf-8")

    e2e = root / "e2e" / "app.e2e.ts"
    if e2e.parent.is_dir():
        e2e.write_text(E2E_APP_TS.strip() + "\n", encoding="utf-8")

    scripts = root / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    dev_script = scripts / "dev-fullstack.sh"
    dev_script.write_text(DEV_FULLSTACK_SH.strip() + "\n", encoding="utf-8")
    dev_script.chmod(0o755)

    print(
        f"[NOTES-WIRE] Wrote scaffold-aligned Notes REST + UI to {build_root}",
        flush=True,
    )
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python3 notes_stack_wire.py BUILD_ROOT", file=sys.stderr)
        return 1
    ok = wire_fullstack_notes_stack(Path(sys.argv[1]).resolve())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
