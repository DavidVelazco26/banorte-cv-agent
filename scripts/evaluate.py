"""Evaluacion de humo del agente Banorte sin interrumpir ante errores HTTP.

Uso:
    python scripts/evaluate.py http://127.0.0.1:8000 local-test
    python scripts/evaluate.py http://127.0.0.1:8000 local-test --only no_aws_cert
    python scripts/evaluate.py http://127.0.0.1:8000 local-test --start-from no_aws_cert --delay-seconds 30 --stop-on-error

"""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "data" / "eval_cases.json"


def _http_detail(body: bytes) -> str:
    try:
        value = json.loads(body.decode("utf-8", errors="replace"))
        if isinstance(value, dict):
            detail = value.get("detail", "")
            if isinstance(detail, str):
                return detail[:200]
            error = value.get("error", {})
            if isinstance(error, dict):
                return str(error.get("code") or error.get("type") or "Error del proveedor")[:200]
    except (ValueError, UnicodeDecodeError):
        pass
    return "Sin detalle disponible"


def evaluate(base_url: str, key: str, only: str | None = None, start_from: str | None = None,
             delay_seconds: float = 0.0, stop_on_error: bool = False):
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    ids = [c["id"] for c in cases]
    if only:
        if only not in ids:
            raise SystemExit(f"Caso desconocido: {only}. Casos: {', '.join(ids)}")
        cases = [c for c in cases if c["id"] == only]
    elif start_from:
        if start_from not in ids:
            raise SystemExit(f"Caso desconocido: {start_from}. Casos: {', '.join(ids)}")
        cases = cases[ids.index(start_from):]

    counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}
    successful_timings = []
    for index, case in enumerate(cases):
        body = json.dumps({"model": "cv-agent-v1", "input": case["question"], "stream": False},
                          ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if key and key != "local-test":
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(base_url.rstrip("/") + "/v1/responses", data=body,
                                     headers=headers, method="POST")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = json.load(response)
            elapsed = (time.perf_counter() - started) * 1000
            successful_timings.append(elapsed)
            answer = "\n".join(
                item.get("text", "")
                for output in payload.get("output", [])
                if output.get("type") == "message"
                for item in output.get("content", [])
                if item.get("type") == "output_text"
            ).casefold()
            passed = all(word.casefold() in answer for word in case["must_contain"])
            status = "PASS" if passed else "FAIL"
            counts[status] += 1
            print(f"{status} | {case['id']} | {elapsed:.0f}ms | {answer[:120].replace(chr(10), ' ')}", flush=True)
        except urllib.error.HTTPError as exc:
            counts["ERROR"] += 1
            detail = _http_detail(exc.read())
            print(f"ERROR | {case['id']} | HTTP {exc.code} | {detail}", flush=True)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError) as exc:
            counts["ERROR"] += 1
            print(f"ERROR | {case['id']} | {type(exc).__name__}: {str(exc)[:160]}", flush=True)

        if stop_on_error and counts["ERROR"]:
            print("Evaluación detenida tras un error: revisar registros del servidor.", flush=True)
            break
        if delay_seconds and index < len(cases) - 1:
            print(f"Pausa entre casos: {delay_seconds:g} segundos", flush=True)
            time.sleep(delay_seconds)

    average = (sum(successful_timings) / len(successful_timings)) if successful_timings else 0.0
    executed = sum(counts.values())
    print(f"\nResultado: {counts['PASS']} PASS / {counts['FAIL']} FAIL / {counts['ERROR']} ERROR "
          f"de {executed} ejecutados ({len(cases)} seleccionados). Latencia promedio de respuestas HTTP exitosas: {average:.0f} ms")
    if counts["ERROR"]:
        print("Los errores HTTP se deben diagnosticar con los registros de Uvicorn en Terminal 1.")
    if counts["FAIL"]:
        print("FAIL significa que faltaron palabras clave; no equivale necesariamente a una respuesta incorrecta.")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test de respuestas del agente Banorte")
    parser.add_argument("base_url", help="Ejemplo: http://127.0.0.1:8000")
    parser.add_argument("key", help="Clave del agente o 'local-test' si auth esta desactivada en localhost")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--only", help="Ejecuta solo un caso por ID")
    group.add_argument("--start-from", help="Empieza desde un ID (incluido) y continua")
    parser.add_argument("--delay-seconds", type=float, default=0, help="Pausa entre preguntas, por ejemplo 30")
    parser.add_argument("--stop-on-error", action="store_true", help="No continuar después de un error HTTP")
    args = parser.parse_args()
    if args.delay_seconds < 0:
        parser.error("--delay-seconds debe ser >= 0")
    evaluate(args.base_url, args.key, only=args.only, start_from=args.start_from,
             delay_seconds=args.delay_seconds, stop_on_error=args.stop_on_error)