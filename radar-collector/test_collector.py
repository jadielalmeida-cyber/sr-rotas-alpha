import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from unittest.mock import patch

import collector


ROOT = Path(__file__).resolve().parent


class CollectorTest(unittest.TestCase):
    def cli(self, *args, env=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "collector.py"), *map(str, args)],
            cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=10,
        )

    def test_pipeline_gera_lotes_a_partir_de_html_e_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "out"
            run = self.cli("build", "--source", "teste_sp", "--events-html", "fixtures/agenda.html",
                           "--pois-csv", "fixtures/locais.csv", "--event-batch-size", 1, "--out", out)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads((out / "report.json").read_text())
            self.assertEqual(report["accepted_locally"], {"events": 2, "pois": 1})
            batches = [json.loads((out / name).read_text()) for name in report["batches"]]
            self.assertEqual(len({batch["run_id"] for batch in batches}), 3)
            self.assertTrue(all(batch["dry_run"] for batch in batches))
            self.assertEqual(batches[0]["events"][0]["event_type"], "music")
            self.assertEqual(batches[0]["events"][0]["starts_at"], "2030-11-16T20:00:00-03:00")
            self.assertNotIn("expected_end_at", batches[1]["events"][0])
            self.assertEqual(batches[2]["pois"][0]["poi_type"], "arena")
            self.assertNotIn("starts_at", batches[2]["pois"][0])

    def test_registros_sem_evidencia_e_conflitos_ficam_para_revisao(self):
        event = {
            "external_id": "evento-001", "name": "Teste", "starts_at": "2030-11-16T20:00:00-03:00",
            "lat": -23.5, "lng": -46.6, "source_url": "https://example.org/evento-001",
        }
        issues = []
        rows, duplicates = collector.validate_rows("events", [
            event, event,
            dict(event, external_id="evento-002"), dict(event, external_id="evento-002", name="Outro"),
            dict(event, external_id="evento-003", lat=None),
            dict(event, external_id="evento-004", starts_at="2030-11-16T20:00:00"),
        ], "teste_sp", issues, lambda row: row)
        self.assertEqual([row["external_id"] for row in rows], ["evento-001"])
        self.assertEqual(duplicates, 1)
        self.assertEqual(len(issues), 3)

    def test_url_remota_bloqueada_encerra_antes_de_buscar_a_pagina(self):
        with patch.object(collector, "read_http", return_value=b"User-agent: *\nDisallow: /") as fetch:
            with self.assertRaisesRegex(ValueError, "bloqueia"):
                collector.read_source("https://example.org/agenda")
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(fetch.call_args.args[0].full_url, "https://example.org/robots.txt")

    def test_robots_inacessivel_nao_permite_busca(self):
        unavailable = HTTPError("https://example.org/robots.txt", 503, "Unavailable", {}, io.BytesIO())
        with patch.object(collector, "read_http", side_effect=unavailable) as fetch:
            with self.assertRaisesRegex(ValueError, "indisponível"):
                collector.read_source("https://example.org/agenda")
        self.assertEqual(fetch.call_count, 1)

    def test_ping_dry_run_e_reenvio_idempotente_com_http_local(self):
        calls = []
        key = "srrk_1234abcd_" + "x" * 43

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.respond({"ok": True, "allowed_sources": ["teste_sp"]})

            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                calls.append((self.path, body))
                rejected = self.path.endswith("/pois")
                payload = json.loads(body)
                self.respond({"ok": True, "run_id": payload["run_id"], "dry_run": payload["dry_run"],
                              "items": [{"status": "rejected" if rejected else "accepted"}]})

            def respond(self, body):
                self.assert_authorization()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def assert_authorization(self):
                if self.headers["Authorization"] != "Bearer " + key:
                    raise AssertionError("credencial individual ausente")

            def log_message(self, *_):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server, tempfile.TemporaryDirectory() as temp:
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                env = dict(os.environ, SR_ROTAS_BASE_URL=f"http://127.0.0.1:{server.server_port}",
                           SR_ROTAS_COLLECTOR_KEY=key)
                out = Path(temp) / "out"
                built = self.cli("build", "--source", "teste_sp", "--events-html", "fixtures/agenda.html",
                                 "--pois-csv", "fixtures/locais.csv", "--out", out)
                self.assertEqual(built.returncode, 0, built.stderr)
                self.assertEqual(self.cli("ping", env=env).returncode, 0)
                events = out / "events-001.json"
                self.assertEqual(self.cli("send", events, env=env).returncode, 0)
                self.assertEqual(self.cli("send", events, "--submit", env=env).returncode, 0)
                self.assertEqual(self.cli("send", events, "--submit", env=env).returncode, 0)
                self.assertEqual(self.cli("send", out / "pois-001.json", env=env).returncode, 2)
                self.assertEqual(calls[0][0], "/api/v1/radar/ingest")
                self.assertEqual(calls[3][0], "/api/v1/radar/collector/pois")
                self.assertTrue(json.loads(calls[0][1])["dry_run"])
                self.assertFalse(json.loads(calls[1][1])["dry_run"])
                self.assertNotEqual(json.loads(calls[0][1])["run_id"], json.loads(calls[1][1])["run_id"])
                self.assertEqual(calls[1], calls[2])
            finally:
                server.shutdown()
                worker.join()


if __name__ == "__main__":
    unittest.main()
