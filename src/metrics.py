"""
metrics.py — Sistema de métricas de rendimiento para Anti-Agent.

Almacena las últimas 50 inferencias con identificación de modelo,
para calcular promedios y percentiles reales (TTFT p50/p95, tokens/s).
Thread-safe mediante Lock.
"""
import time
import statistics
import subprocess
from collections import deque
from threading import Lock
import psutil

# ─── Estado Global ────────────────────────────────────────────────────────────

_lock = Lock()

# Historial de las últimas 50 inferencias (circular, thread-safe)
_history: deque = deque(maxlen=50)

# Contadores de parseo de plugins (acumulativos)
_parse_success: int = 0
_parse_failure: int = 0

# Cache de recursos del sistema (se refresca bajo demanda)
_resource_cache: dict = {
    "ram_total_mb": None,
    "ram_used_mb": None,
    "vram_total_mb": None,
    "vram_used_mb": None,
    "last_update": None,
}


# ─── Registro de Inferencias ──────────────────────────────────────────────────

def record_inference(model: str, ttft_ms: float, tokens_generated: int, duration_seconds: float):
    """
    Registra una inferencia completa en el historial circular.

    Args:
        model:            Nombre del modelo que generó la respuesta.
        ttft_ms:          Time to First Token en milisegundos.
        tokens_generated: Tokens de completado generados.
        duration_seconds: Duración total de la inferencia en segundos.
    """
    tps = round(tokens_generated / duration_seconds, 2) if duration_seconds > 0 else None
    entry = {
        "ts": time.time(),
        "model": model,
        "ttft_ms": round(ttft_ms, 2),
        "tokens_generated": tokens_generated,
        "tokens_per_sec": tps,
        "duration_s": round(duration_seconds, 3),
    }
    with _lock:
        _history.append(entry)


# ─── Compatibilidad backward con agent.py ────────────────────────────────────

def record_ttft(start_timestamp: float):
    """
    Actualiza el TTFT de la última entrada en el historial.
    Se llama desde agent.py cuando llega la primera respuesta del LLM.
    """
    ttft = (time.time() - start_timestamp) * 1000
    with _lock:
        if _history:
            _history[-1]["ttft_ms"] = round(ttft, 2)
        else:
            # Primera llamada sin record_inference previo: crear entrada parcial
            _history.append({
                "ts": start_timestamp,
                "model": "unknown",
                "ttft_ms": round(ttft, 2),
                "tokens_generated": 0,
                "tokens_per_sec": None,
                "duration_s": 0,
            })


def record_token_generation(num_tokens: int, duration_seconds: float):
    """
    Actualiza tokens/s en la última entrada del historial.
    Se llama desde agent.py con los datos de usage del LLM.
    """
    with _lock:
        if _history:
            _history[-1]["tokens_generated"] = num_tokens
            if duration_seconds > 0:
                _history[-1]["tokens_per_sec"] = round(num_tokens / duration_seconds, 2)


def set_current_model(model: str):
    """
    Registra el modelo activo en la última entrada del historial.
    Llamar desde agent.py antes de record_ttft para garantizar identificación correcta.
    """
    with _lock:
        if _history:
            _history[-1]["model"] = model


# ─── Parseo de Plugins ────────────────────────────────────────────────────────

def record_parse_success(success: bool):
    """Incrementa el contador de parseo exitoso o fallido."""
    global _parse_success, _parse_failure
    with _lock:
        if success:
            _parse_success += 1
        else:
            _parse_failure += 1


# ─── Recursos del Sistema ─────────────────────────────────────────────────────

def _update_ram():
    mem = psutil.virtual_memory()
    _resource_cache["ram_total_mb"] = mem.total // (1024 * 1024)
    _resource_cache["ram_used_mb"] = (mem.total - mem.available) // (1024 * 1024)


def _update_vram():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        )
        total, used = out.strip().split(",")
        _resource_cache["vram_total_mb"] = int(total.strip())
        _resource_cache["vram_used_mb"] = int(used.strip())
    except Exception:
        _resource_cache["vram_total_mb"] = None
        _resource_cache["vram_used_mb"] = None


def update_resource_usage():
    """Refresca RAM y VRAM. Llamar antes de exponer métricas al cliente."""
    with _lock:
        _update_ram()
        _update_vram()
        _resource_cache["last_update"] = time.time()


# ─── Estadísticas Agregadas ───────────────────────────────────────────────────

def _percentile(data: list, p: int) -> float:
    """Calcula el percentil p de una lista. Retorna 0.0 si lista vacía."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = max(0, int(len(sorted_data) * p / 100) - 1)
    return round(sorted_data[idx], 2)


def get_metrics() -> dict:
    """
    Retorna el estado completo de métricas:
    - Última inferencia
    - Estadísticas agregadas por modelo (avg, p50, p95 de TTFT y tokens/s)
    - Conteo del historial (últimas 50 muestras)
    - Recursos del sistema (RAM / VRAM)
    - Tasa de éxito de parseo de plugins
    """
    with _lock:
        history_snapshot = list(_history)
        parse_ok = _parse_success
        parse_fail = _parse_failure
        resources = dict(_resource_cache)

    # Agrupar por modelo para estadísticas precisas
    by_model: dict = {}
    for entry in history_snapshot:
        model = entry.get("model", "unknown")
        by_model.setdefault(model, {"ttft": [], "tps": []})
        if entry.get("ttft_ms") is not None:
            by_model[model]["ttft"].append(entry["ttft_ms"])
        if entry.get("tokens_per_sec") is not None:
            by_model[model]["tps"].append(entry["tokens_per_sec"])

    model_stats = {}
    for model, data in by_model.items():
        ttft_list = data["ttft"]
        tps_list = data["tps"]
        model_stats[model] = {
            "samples": len(ttft_list),
            "ttft_avg_ms": round(statistics.mean(ttft_list), 2) if ttft_list else None,
            "ttft_p50_ms": _percentile(ttft_list, 50),
            "ttft_p95_ms": _percentile(ttft_list, 95),
            "tps_avg": round(statistics.mean(tps_list), 2) if tps_list else None,
            "tps_p50": _percentile(tps_list, 50),
            "tps_p95": _percentile(tps_list, 95),
        }

    last = history_snapshot[-1] if history_snapshot else {}
    parse_total = parse_ok + parse_fail

    return {
        "last_inference": last,
        "by_model": model_stats,
        "history_count": len(history_snapshot),
        "parse_success": parse_ok,
        "parse_failure": parse_fail,
        "parse_success_rate": round(parse_ok / parse_total, 4) if parse_total > 0 else None,
        **resources,
    }
