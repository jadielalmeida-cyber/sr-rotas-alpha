#!/usr/bin/env python3
"""Coletor externo do Radar do Sr. Rotas (contrato V2)."""

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser


USER_AGENT = "SrRotasRadarCollector/0.1"
API_PREFIX = "/api/v1/radar"
API_ROUTES = {"events": "/ingest", "pois": "/collector/pois"}
MAX_BODY = 2_000_000
MAX_SOURCE = 5_000_000
RESERVED_SOURCES = {"ticketmaster", "manual", "admin", "internal"}
EVENT_TYPES = {
    "event", "music", "sports", "theatre", "fair_convention", "family",
    "airport", "bus_terminal", "mall", "cultural", "mobility_hub",
}
SCHEMA_CATEGORIES = {
    "MusicEvent": "music", "SportsEvent": "sports", "TheaterEvent": "theatre",
    "ChildrensEvent": "family", "ExhibitionEvent": "fair_convention",
    "DanceEvent": "cultural", "ScreeningEvent": "cultural",
}
SCHEMA_STATUSES = {"EventScheduled": "active", "EventCancelled": "cancelled"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect())


def json_bytes(data):
    return json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def web_url(value, field="source_url"):
    value = required_text(value, field, 1200)
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{field}: URL HTTP(S) absoluta sem credencial")
    if any(char.isspace() for char in value) or "@" in parsed.netloc:
        raise ValueError(f"{field}: URL inválida")
    return value


def required_text(value, field, maximum):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f"{field}: texto obrigatório de até {maximum} caracteres")
    return value.strip()


def slug(value, field, maximum=100):
    if not isinstance(value, str) or not re.fullmatch(rf"[a-z0-9][a-z0-9_-]{{1,{maximum - 1}}}", value):
        raise ValueError(f"{field}: identificador minúsculo de 2 a {maximum} caracteres")
    return value


def number(value, field, low, high):
    if isinstance(value, bool):
        raise ValueError(f"{field}: número obrigatório")
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field}: número obrigatório") from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{field}: deve estar entre {low} e {high}")
    return result


def date_time(value, field):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ):
        raise ValueError(f"{field}: informe data e hora ISO 8601 com fuso explícito")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}: data ou fuso inválido") from None


def read_http(request, limit):
    with OPENER.open(request, timeout=30) as response:
        body = response.read(limit + 1)
    if len(body) > limit:
        raise ValueError("resposta excede o tamanho permitido")
    return body


def read_source(location):
    if not location.startswith(("https://", "http://")):
        path = Path(location)
        with path.open("rb") as handle:
            raw = handle.read(MAX_SOURCE + 1)
        if len(raw) > MAX_SOURCE:
            raise ValueError("arquivo de origem excede 5 MB")
        return raw.decode("utf-8-sig")

    parsed = urlsplit(web_url(location, "fonte"))
    if parsed.scheme != "https":
        raise ValueError("a origem remota deve usar HTTPS")
    headers = {"User-Agent": USER_AGENT}
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    policy = RobotFileParser()
    try:
        raw = read_http(Request(robots_url, headers=headers), MAX_SOURCE)
    except HTTPError as error:
        if error.code not in {404, 410}:
            raise ValueError(f"robots.txt indisponível (HTTP {error.code})") from None
    else:
        policy.parse(raw.decode("utf-8", errors="replace").splitlines())
        if not policy.can_fetch(USER_AGENT, location):
            raise ValueError("a origem bloqueia este coletor no robots.txt")
    return read_http(Request(location, headers=headers), MAX_SOURCE).decode("utf-8-sig")


class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.script = None
        self.documents = []
        self.issues = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and (dict(attrs).get("type") or "").lower() == "application/ld+json":
            self.script = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            try:
                self.documents.append(json.loads("".join(self.script)))
            except json.JSONDecodeError:
                self.issues.append({"kind": "events", "reason": "bloco JSON-LD inválido"})
            self.script = None


def schema_types(value):
    items = value if isinstance(value, list) else [value]
    return [item.rsplit("/", 1)[-1].rsplit(":", 1)[-1] for item in items if isinstance(item, str)]


def event_nodes(data):
    if isinstance(data, list):
        for child in data:
            yield from event_nodes(child)
    elif isinstance(data, dict):
        if any(kind == "Event" or kind.endswith("Event") for kind in schema_types(data.get("@type"))):
            yield data
        else:
            for field in ("@graph", "mainEntity", "itemListElement", "item"):
                yield from event_nodes(data.get(field))


def schema_event(node, page_url):
    location = node.get("location")
    location = location if isinstance(location, dict) else {}
    geo = location.get("geo")
    geo = geo if isinstance(geo, dict) else {}
    address = location.get("address")
    address = address if isinstance(address, dict) else {"streetAddress": address}
    identifier = node.get("identifier") or node.get("@id")
    if isinstance(identifier, dict):
        identifier = identifier.get("value")

    raw_url = node.get("url")
    if isinstance(raw_url, str) and raw_url.strip():
        event_url = urljoin(page_url or "", raw_url.strip())
    elif isinstance(node.get("@id"), str) and node["@id"].startswith(("http://", "https://")):
        event_url = node["@id"]
    else:
        event_url = None

    if not identifier and event_url and event_url != page_url:
        identifier = "url-" + hashlib.sha256(event_url.encode()).hexdigest()[:32]

    categories = schema_types(node.get("@type"))
    status_types = schema_types(node.get("eventStatus"))
    status = "active" if not status_types else SCHEMA_STATUSES.get(status_types[0])
    if status is None:
        raise ValueError("eventStatus: confirmar a nova ocorrência ou status na fonte")

    return {
        "external_id": identifier, "name": node.get("name"),
        "event_type": next((SCHEMA_CATEGORIES[t] for t in categories if t in SCHEMA_CATEGORIES), "event"),
        "source_url": event_url or page_url, "status": status,
        "starts_at": node.get("startDate"), "expected_end_at": node.get("endDate"),
        "venue_name": location.get("name"), "address": address.get("streetAddress"),
        "city": address.get("addressLocality"), "state": address.get("addressRegion"),
        "country_code": address.get("addressCountry"),
        "lat": geo.get("latitude"), "lng": geo.get("longitude"),
    }


def normalized_row(kind, raw, source):
    if not isinstance(raw, dict):
        raise ValueError("registro precisa ser um objeto")
    declared_source = raw.get("source")
    if declared_source and declared_source != source:
        raise ValueError("source do registro difere da fonte selecionada")
    row = {
        "source": source,
        "lat": number(raw.get("lat"), "lat", -90, 90),
        "lng": number(raw.get("lng"), "lng", -180, 180),
        "source_url": web_url(raw.get("source_url")),
    }
    for field, limit in (("address", 500), ("city", 120), ("state", 80)):
        if raw.get(field) not in (None, ""):
            row[field] = required_text(raw[field], field, limit)

    if kind == "pois":
        row.update(
            source_external_id=slug(raw.get("source_external_id"), "source_external_id"),
            canonical_name=required_text(raw.get("canonical_name"), "canonical_name", 240),
            poi_type=slug(raw.get("poi_type"), "poi_type"),
        )
        if raw.get("source_confidence") not in (None, ""):
            row["source_confidence"] = number(raw["source_confidence"], "source_confidence", 0, 1)
        return row

    external_id = required_text(raw.get("external_id"), "external_id", 160)
    if any(ord(char) < 32 for char in external_id):
        raise ValueError("external_id: contém caracteres de controle")
    event_type = raw.get("event_type", "event")
    status = raw.get("status", "active")
    if event_type not in EVENT_TYPES or status not in {"active", "cancelled"}:
        raise ValueError("event_type ou status fora do contrato")
    row.update(external_id=external_id, name=required_text(raw.get("name"), "name", 240),
               event_type=event_type, status=status)
    times = {}
    for field in ("starts_at", "expected_end_at", "egress_start_at", "egress_end_at", "last_verified_at"):
        if field == "starts_at" or raw.get(field) not in (None, ""):
            times[field] = date_time(raw.get(field), field)
            row[field] = times[field].isoformat()
    for start, end in (("starts_at", "expected_end_at"), ("egress_start_at", "egress_end_at")):
        if start in times and end in times and times[end] < times[start]:
            raise ValueError(f"{end}: anterior a {start}")
    if raw.get("venue_name"):
        row["venue_name"] = required_text(raw["venue_name"], "venue_name", 240)
    if raw.get("country_code"):
        code = required_text(raw["country_code"], "country_code", 2)
        if not re.fullmatch("[A-Za-z]{2}", code):
            raise ValueError("country_code: informe código ISO de duas letras")
        row["country_code"] = code.upper()
    if raw.get("confidence") is not None:
        row["confidence"] = number(raw["confidence"], "confidence", 0, 1)
    if raw.get("end_time_source") is not None:
        if raw["end_time_source"] not in {"source", "estimated"}:
            raise ValueError("end_time_source inválido")
        row["end_time_source"] = raw["end_time_source"]
    return row


def validate_rows(kind, raw_rows, source, issues, convert):
    groups = defaultdict(list)
    identity_field = "external_id" if kind == "events" else "source_external_id"
    for position, raw in enumerate(raw_rows, start=1):
        try:
            row = normalized_row(kind, convert(raw), source)
            groups[row[identity_field]].append((position, row))
        except (ValueError, TypeError) as error:
            issues.append({"kind": kind, "position": position, "reason": str(error)})

    result = []
    duplicates = 0
    for identity, group in groups.items():
        first = group[0][1]
        if any(row != first for _, row in group[1:]):
            issues.append({"kind": kind, "id": identity, "positions": [pos for pos, _ in group],
                           "reason": "mesmo ID com registros diferentes"})
        else:
            result.append(first)
            duplicates += len(group) - 1
    return result, duplicates


def build(args):
    source = slug(args.source, "source", 80)
    if source in RESERVED_SOURCES:
        raise ValueError("fonte reservada aos fluxos internos do Radar")
    issues = []
    rows_by_kind = {}
    duplicates = 0
    if args.events_html:
        parser = JsonLdParser()
        parser.feed(read_source(args.events_html))
        parser.close()
        issues.extend(parser.issues)
        nodes = list(event_nodes(parser.documents))
        if not nodes:
            issues.append({"kind": "events", "reason": "nenhum evento JSON-LD encontrado"})
        page_url = args.page_url or (args.events_html if args.events_html.startswith("https://") else None)
        if page_url:
            web_url(page_url, "page-url")
        rows_by_kind["events"], duplicates = validate_rows(
            "events", nodes, source, issues, lambda node: schema_event(node, page_url)
        )
    if args.events_json:
        data = json.loads(read_source(args.events_json))
        events = data.get("events") if isinstance(data, dict) else data
        if not isinstance(events, list):
            raise ValueError("JSON de eventos deve ser uma lista ou objeto com events")
        rows_by_kind["events"], duplicates = validate_rows("events", events, source, issues, lambda row: row)
    if args.pois_csv:
        reader = csv.DictReader(io.StringIO(read_source(args.pois_csv), newline=""))
        required = {"source_external_id", "canonical_name", "poi_type", "lat", "lng", "source_url"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV de locais sem uma ou mais colunas obrigatórias")
        rows_by_kind["pois"], poi_duplicates = validate_rows("pois", reader, source, issues, lambda row: row)
        duplicates += poi_duplicates
    if not rows_by_kind:
        raise ValueError("informe ao menos uma entrada de eventos ou locais")

    run = "radar-" + uuid.uuid4().hex
    batches = {}
    for kind, rows in rows_by_kind.items():
        batch_size = args.event_batch_size if kind == "events" else 50
        for offset in range(0, len(rows), batch_size):
            index = offset // batch_size + 1
            name = f"{kind}-{index:03}"
            batches[name + ".json"] = {"run_id": f"{run}-{name}", "dry_run": True,
                                      kind: rows[offset:offset + batch_size]}
    report = {"source": source, "accepted_locally": {kind: len(rows) for kind, rows in rows_by_kind.items()},
              "duplicates_removed": duplicates, "review": issues, "batches": list(batches)}
    args.out.mkdir(parents=True, exist_ok=False)
    for name, data in {**batches, "report.json": report}.items():
        (args.out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if issues or not batches else 0


def api_request(path, payload=None):
    base = web_url(os.environ.get("SR_ROTAS_BASE_URL", ""), "SR_ROTAS_BASE_URL")
    parts = urlsplit(base)
    local = parts.hostname in {"127.0.0.1", "localhost", "::1"}
    if (parts.scheme != "https" and not local) or parts.path not in {"", "/"} or parts.query or parts.fragment:
        raise ValueError("SR_ROTAS_BASE_URL deve ser a origem HTTPS do Radar")
    key = os.environ.get("SR_ROTAS_COLLECTOR_KEY", "")
    if not re.fullmatch(r"srrk_[0-9a-f]{8}_[A-Za-z0-9_-]{43,}", key):
        raise ValueError("configure SR_ROTAS_COLLECTOR_KEY com a chave individual do coletor")
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": USER_AGENT}
    data = None
    if payload is not None:
        data = json_bytes(payload)
        if len(data) > MAX_BODY:
            raise ValueError("lote acima de 2 MB")
        headers["Content-Type"] = "application/json"
    request = Request(base.rstrip("/") + API_PREFIX + path, headers=headers, data=data)
    try:
        return json.loads(read_http(request, MAX_BODY))
    except HTTPError as error:
        retry = error.headers.get("Retry-After")
        retry_hint = f" (Retry-After: {retry})" if retry and retry.isdigit() else ""
        error_hint = ""
        with error:
            try:
                detail = json.loads(error.read(8192))
                code = detail.get("error") if isinstance(detail, dict) else None
                if isinstance(code, str) and re.fullmatch(r"[a-z][a-z0-9_]{1,79}", code):
                    error_hint = f" {code}"
            except (ValueError, OSError):
                pass
        raise ValueError(f"Radar retornou HTTP {error.code}{error_hint}{retry_hint}; preserve o arquivo para retry") from None


def send(args):
    payload = json.loads(args.batch.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) not in (
        {"run_id", "dry_run", "events"}, {"run_id", "dry_run", "pois"}
    ):
        raise ValueError("informe um arquivo de lote gerado pelo comando build")
    kind = "events" if "events" in payload else "pois"
    run_id = payload["run_id"]
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{8,93}", run_id):
        raise ValueError("run_id inválido")
    rows = payload[kind]
    if not isinstance(rows, list) or not 1 <= len(rows) <= (500 if kind == "events" else 50):
        raise ValueError("quantidade inválida no lote")
    if args.submit:
        payload["run_id"] += "-submit"
    payload["dry_run"] = not args.submit
    print(f"run_id={payload['run_id']} dry_run={str(payload['dry_run']).lower()}", file=sys.stderr, flush=True)
    result = api_request(API_ROUTES[kind], payload)
    if (not isinstance(result, dict) or result.get("ok") is not True
            or result.get("run_id") != payload["run_id"]
            or result.get("dry_run") is not payload["dry_run"]
            or not isinstance(result.get("items"), list)
            or any(not isinstance(item, dict) for item in result["items"])):
        raise ValueError("resposta do Radar fora do formato esperado")
    summary = Counter(item.get("status") for item in result["items"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    audit = result.get("http_audit") or {}
    return 2 if result.get("rejected") or summary["rejected"] or audit.get("status") == "unconfirmed" else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build", help="normaliza fontes e gera lotes e relatório")
    build_parser.add_argument("--source", required=True, help="slug autorizado na credencial do Radar")
    event_input = build_parser.add_mutually_exclusive_group()
    event_input.add_argument("--events-html", help="arquivo HTML ou URL HTTPS autorizada com JSON-LD")
    event_input.add_argument("--events-json", help="arquivo ou feed HTTPS com lista de eventos mapeados")
    build_parser.add_argument("--page-url", help="URL de origem de um HTML salvo localmente")
    build_parser.add_argument("--pois-csv", help="arquivo ou feed CSV de locais")
    build_parser.add_argument("--event-batch-size", type=int, default=200)
    build_parser.add_argument("--out", type=Path, required=True, help="nova pasta para lotes e relatório")

    commands.add_parser("ping", help="confere credencial, escopos e limites do Radar")
    send_parser = commands.add_parser("send", help="valida um lote no Radar em dry-run por padrão")
    send_parser.add_argument("batch", type=Path)
    send_parser.add_argument("--submit", action="store_true", help="envia o lote para revisão humana")
    args = parser.parse_args()

    try:
        if args.command == "build":
            if not 1 <= args.event_batch_size <= 500:
                raise ValueError("--event-batch-size deve estar entre 1 e 500")
            return build(args)
        if args.command == "send":
            return send(args)
        result = api_request("/collector/ping")
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise ValueError("o Radar não confirmou a credencial")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, csv.Error) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
