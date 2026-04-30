"""
Minimal runnable backends under BUILD_ROOT when stack is backend or fullstack.

Node scaffold includes GET /health and /api/v1/notes REST (deterministic MVP) with CORS and express.json().
"""

from __future__ import annotations

from pathlib import Path


NODE_INDEX_JS = """\
import express from 'express';
import {randomUUID} from 'crypto';

const app = express();
const port = Number(process.env.PORT || 3090);

/** @typedef {{ id: string; title: string; body: string; createdAt: string; updatedAt: string }} Note */

/** @type {Map<string, Note>} */
const notes = new Map();

function cors(req, res, next) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PATCH,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') {
    res.sendStatus(204);
    return;
  }
  next();
}

function nowIso() {
  return new Date().toISOString();
}

app.use(cors);
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'nodejs' });
});

app.get('/api/v1/notes', (_req, res) => {
  res.json([...notes.values()].sort((a, b) => a.updatedAt.localeCompare(b.updatedAt)));
});

app.post('/api/v1/notes', (req, res) => {
  const title = typeof req.body?.title === 'string' ? req.body.title.trim() : '';
  if (!title) {
    res.status(400).json({ error: 'title is required' });
    return;
  }
  const body = typeof req.body?.body === 'string' ? req.body.body : '';
  const id = randomUUID();
  const t = nowIso();
  const note = { id, title, body, createdAt: t, updatedAt: t };
  notes.set(id, note);
  res.status(201).json(note);
});

app.get('/api/v1/notes/:id', (req, res) => {
  const n = notes.get(req.params.id);
  if (!n) {
    res.status(404).json({ error: 'not found' });
    return;
  }
  res.json(n);
});

app.patch('/api/v1/notes/:id', (req, res) => {
  const n = notes.get(req.params.id);
  if (!n) {
    res.status(404).json({ error: 'not found' });
    return;
  }
  if (typeof req.body?.title === 'string') {
    n.title = req.body.title.trim();
  }
  if (typeof req.body?.body === 'string') {
    n.body = req.body.body;
  }
  n.updatedAt = nowIso();
  res.json(n);
});

app.delete('/api/v1/notes/:id', (req, res) => {
  const ok = notes.delete(req.params.id);
  res.status(ok ? 204 : 404).send();
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Server listening on http://localhost:${port}`);
  console.log(`Notes REST: GET/POST PATCH DELETE /api/v1/notes`);
});
"""


NODE_SERVER_README = """\
# Node server scaffold

Deterministic MVP: **`GET /health`**, **`/api/v1/notes`** (JSON CRUD), **`express.json`**, permissive dev CORS, in‑memory storage (lost on restart).

- **RN client**: **`GET`** lists collection at **`notesApiRoot()`** (see generated `src/config/api.ts`) — that string is already **`http://<host>:3090/api/v1/notes`**; do **not** append **`/api/v1/notes`** again in `fetch` URLs.

```bash
cd server && npm install && npm start
```

- Default port **3090** (override **`PORT`**).
- **Android emulator**: app uses **`http://10.0.2.2:3090`**; **physical device** typically needs **`adb reverse tcp:3090 tcp:3090`** and may require editing **`src/config/api.ts`**.

## Routes (compact)

| Method | Path | Body |
|--------|------|------|
| GET | `/health` | |
| GET | `/api/v1/notes` | |
| POST | `/api/v1/notes` | `{ "title": string, "body"?: string }` |
| GET | `/api/v1/notes/:id` | |
| PATCH | `/api/v1/notes/:id` | `{ "title"?: string, "body"?: string }` |
| DELETE | `/api/v1/notes/:id` | |
"""


def scaffold_node_server(build_root: Path, *, notes_api: bool = True) -> Path:
    """Express under server/ with GET /health and optionally full notes REST."""
    server = build_root / "server"
    server.mkdir(parents=True, exist_ok=True)
    src = server / "src"
    src.mkdir(parents=True, exist_ok=True)
    pkg = notes_api
    (server / "package.json").write_text(
        "\n".join(
            [
                "{",
                '  "name": "generated-app-server",',
                '  "version": "1.0.0",',
                '  "private": true,',
                '  "type": "module",',
                '  "scripts": {',
                '    "start": "node src/index.js"',
                "  },",
                '  "dependencies": {',
                '    "express": "^4.21.0"',
                "  }",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    idx = NODE_INDEX_JS if pkg else (
        """\
import express from 'express';

const app = express();
const port = Number(process.env.PORT || 3090);

app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') {
    res.sendStatus(204);
    return;
  }
  next();
});

app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'nodejs' });
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Server listening on http://localhost:${port}`);
});
"""
    )
    (src / "index.js").write_text(idx, encoding="utf-8")
    readme_txt = NODE_SERVER_README if pkg else (
        "# Node server scaffold\n\n"
        "```bash\n"
        "cd server && npm install && npm start\n"
        "```\n\n"
        "`GET /health` returns `{ \"status\": \"ok\" }` on port **3090** by default (`PORT` overrides).\n"
    )
    (server / "README.md").write_text(readme_txt, encoding="utf-8")
    return server


def scaffold_java_spring_boot(build_root: Path) -> Path:
    """Minimal Maven Spring Boot app under backend-java/. Uses Java 17+."""
    backend = build_root / "backend-java"
    backend.mkdir(parents=True, exist_ok=True)
    java_pkg = backend / "src" / "main" / "java" / "com" / "generatedapp"
    resources = backend / "src" / "main" / "resources"
    java_pkg.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)

    group = "com.generatedapp"
    artifact = "app-server"

    (backend / "pom.xml").write_text(
        '\n'.join(
            [
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
                "<project xmlns=\"http://maven.apache.org/POM/4.0.0\"",
                "         xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"",
                '         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">',
                "  <modelVersion>4.0.0</modelVersion>",
                "  <parent>",
                '    <groupId>org.springframework.boot</groupId>',
                '    <artifactId>spring-boot-starter-parent</artifactId>',
                "    <version>3.2.5</version>",
                "    <relativePath/>",
                "  </parent>",
                f"  <groupId>{group}</groupId>",
                f"  <artifactId>{artifact}</artifactId>",
                "  <version>0.0.1-SNAPSHOT</version>",
                "  <name>generated-app-backend</name>",
                "  <properties>",
                "    <java.version>17</java.version>",
                "  </properties>",
                "  <dependencies>",
                "    <dependency>",
                '      <groupId>org.springframework.boot</groupId>',
                '      <artifactId>spring-boot-starter-web</artifactId>',
                "    </dependency>",
                "  </dependencies>",
                "  <build>",
                "    <plugins>",
                "      <plugin>",
                '        <groupId>org.springframework.boot</groupId>',
                '        <artifactId>spring-boot-maven-plugin</artifactId>',
                "      </plugin>",
                "    </plugins>",
                "  </build>",
                "</project>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (resources / "application.properties").write_text(
        "server.port=8080\n",
        encoding="utf-8",
    )

    main_class = """
package com.generatedapp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@SpringBootApplication
@RestController
public class Application {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        return ResponseEntity.ok(Map.of("status", "ok", "service", "java"));
    }
}
""".lstrip()

    (java_pkg / "Application.java").write_text(main_class, encoding="utf-8")

    (backend / "README.md").write_text(
        "# Spring Boot scaffold (Java)\n\n"
        "Requirements: JDK 17+ and Maven (`mvn` on PATH).\n\n"
        "```bash\n"
        "cd backend-java\n"
        "mvn -q spring-boot:run\n"
        "```\n\n"
        "`GET http://localhost:8080/health`\n",
        encoding="utf-8",
    )
    return backend
