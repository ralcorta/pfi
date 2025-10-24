"""
app.py — Sensor multi-tenant (VXLAN/UDP 4789) + API de control (FastAPI)

- Data-plane:
    * Escucha UDP:4789 (AWS Traffic Mirroring con VXLAN).
    * Decapsula, identifica tenant por VNI, sessioniza por flow y ventana temporal.
    * Llama al hook 'model_infer()' y persiste detecciones en DynamoDB.

- Control-plane (FastAPI):
    * /healthz, /stats
    * /detections/{tenant_id}?start_ts=&end_ts=&limit=&cursor=

Requisitos:
    pip install fastapi uvicorn boto3 pydantic scapy

ECS/Fargate:
    - NLB (UDP 4789) -> este contenedor
    - ALB (HTTP 8080) -> este contenedor
"""

import os
import json
import time
import asyncio
import socket
import contextlib
from collections import defaultdict, deque
from typing import Any, Dict, Optional, Tuple
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from scapy.all import Ether, IP, TCP, UDP  # noqa
from scapy.layers.vxlan import VXLAN

# -----------------------
# Config
# -----------------------
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DDB_TABLE = os.getenv("DDB_TABLE", "detections")
VXLAN_PORT = int(os.getenv("VXLAN_PORT", "4789"))
HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))
WORKERS = int(os.getenv("WORKERS", "4"))
QUEUE_MAX = int(os.getenv("QUEUE_MAX", "20000"))

# temporalidad
WINDOW_SECONDS = float(os.getenv("WINDOW_SECONDS", "3.0"))
MAX_PKTS_PER_WINDOW = int(os.getenv("MAX_PKTS_PER_WINDOW", "256"))

# -----------------------
# Estado runtime
# -----------------------
packet_q: asyncio.Queue[Tuple[bytes, int]] = asyncio.Queue(maxsize=QUEUE_MAX)
shutdown = asyncio.Event()
stats = {
    "rx_packets": 0,
    "rx_errors": 0,
    "enqueued": 0,
    "dropped_full_queue": 0,
    "handled_packets": 0,
    "flushed_windows": 0,
}

# Ventanas por flow: key -> deque[(ts, size)]
FlowKey = Tuple[str, str, str, str, int, int]  # (tenant, src, dst, proto, spt, dpt) o 'NONIP'
windows: Dict[FlowKey, deque] = defaultdict(deque)
last_seen: Dict[FlowKey, float] = {}
win_lock = asyncio.Lock()  # proteger estructuras si hay múltiples workers

# -----------------------
# DynamoDB
# -----------------------
dynamo = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamo.Table(DDB_TABLE)


def to_native(obj: Any) -> Any:
    if isinstance(obj, list):
        return [to_native(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        # elegí int si sabés que es entero
        return float(obj)
    return obj


# -----------------------
# Utilidades multi-tenant / flow / features
# -----------------------
def tenant_id_from_vni(vni: int) -> str:
    """
    Asigna tenant a partir del VNI de VXLAN. En producción podés resolver
    desde una tabla/config. Acá usamos un mapping simple.
    """
    return f"TENANT#{vni}"


def flow_key(eth: Ether, tenant: str) -> FlowKey:
    if IP not in eth:
        return (tenant, "NONIP", "NONIP", "NONIP", 0, 0)
    ip = eth[IP]
    proto = "TCP" if TCP in eth else ("UDP" if UDP in eth else f"P{ip.proto}")
    spt = eth[TCP].sport if TCP in eth else (eth[UDP].sport if UDP in eth else 0)
    dpt = eth[TCP].dport if TCP in eth else (eth[UDP].dport if UDP in eth else 0)
    return (tenant, ip.src, ip.dst, proto, spt, dpt)


def extract_features_from_window(win: deque):
    """
    EJEMPLO mínimo. Reemplazá por tu extracción real (inter-arrival, bursts, entropía, flags, etc.)
    """
    n = len(win)
    if n == 0:
        return None
    t0, _ = win[0]
    tN, _ = win[-1]
    duration = max(1e-6, tN - t0)
    bytes_total = sum(sz for _, sz in win)
    pps = n / duration
    bps = bytes_total / duration
    return {
        "pkts": n,
        "bytes": bytes_total,
        "pps": pps,
        "bps": bps,
        "duration": duration,
    }


def should_flush(win: deque, now: float) -> bool:
    """Cierra ventana si pasó el tiempo o se alcanzó el máximo de paquetes."""
    if not win:
        return False
    if (now - win[0][0]) >= WINDOW_SECONDS:
        return True
    if len(win) >= MAX_PKTS_PER_WINDOW:
        return True
    return False


# -----------------------
# Hook de inferencia del modelo (reemplazá por tu implementación real)
# -----------------------
async def model_infer(tenant: str, fkey: FlowKey, features: Dict[str, float]) -> Dict[str, float]:
    """
    Reemplazá este hook con la llamada real a tu modelo:
      - Local (TensorFlow/PyTorch)
      - o remoto (SageMaker InvokeEndpoint con batching)
    Debe devolver {"score": float, "verdict": "malicious"|"benign"|...}
    """
    # EJEMPLO simplísimo: si bps > umbral, marcamos sospechoso
    score = min(1.0, features["bps"] / 1e6)  # normalización de ejemplo
    verdict = "malicious" if score > 0.5 else "benign"
    await asyncio.sleep(0)  # ceder control en event loop
    return {"score": float(score), "verdict": verdict}


async def persist_detection(
    tenant: str, fkey: FlowKey, features: Dict[str, float], infer: Dict[str, float], ts_ms: int
):
    """
    Guarda resultado en DynamoDB. Esquema sugerido:
      PK = TENANT#...
      SK = FLOW#<five-tuple>#TS#<epoch_ms>
    """
    (tenant_id, src, dst, proto, spt, dpt) = fkey
    assert tenant_id == tenant

    item = {
        "PK": tenant,
        "SK": f"FLOW#{src}-{dst}-{proto}-{spt}-{dpt}#TS#{ts_ms}",
        "srcIp": src,
        "dstIp": dst,
        "proto": proto,
        "srcPort": int(spt),
        "dstPort": int(dpt),
        "ts": ts_ms,
        "features": {k: float(v) for k, v in features.items()},
        "verdict": infer["verdict"],
        "score": float(infer["score"]),
    }
    # Podés agregar más atributos (deviceId, vpcId, etc.)
    table.put_item(Item=item)


# -----------------------
# Data-plane: recepción UDP + workers + janitor
# -----------------------
async def udp_server():
    """Recibe datagramas UDP:4789, decapsula VXLAN y encola (inner_frame, vni)."""
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", VXLAN_PORT))
    sock.setblocking(False)

    try:
        while not shutdown.is_set():
            try:
                data, _ = await loop.sock_recvfrom(sock, 65535)
            except (asyncio.CancelledError, OSError):
                break

            stats["rx_packets"] += 1
            try:
                vx = VXLAN(data)
                inner = bytes(vx.payload)  # Ethernet interno
                vni = int(vx.vni)
                try:
                    packet_q.put_nowait((inner, vni))
                    stats["enqueued"] += 1
                except asyncio.QueueFull:
                    stats["dropped_full_queue"] += 1
            except Exception:
                stats["rx_errors"] += 1
    finally:
        sock.close()


async def process_frame(inner: bytes, vni: int):
    """Actualiza ventana del flow, decide flush y dispara inferencia + persistencia si corresponde."""
    tenant = tenant_id_from_vni(vni)
    eth = Ether(inner)
    fkey = flow_key(eth, tenant)
    now = time.time()

    async with win_lock:
        windows[fkey].append((now, len(inner)))
        last_seen[fkey] = now
        if should_flush(windows[fkey], now):
            win = windows[fkey]
            feats = extract_features_from_window(win)
            windows[fkey].clear()
            stats["flushed_windows"] += 1

    if feats:
        ts_ms = int(now * 1000)
        infer = await model_infer(tenant, fkey, feats)
        await persist_detection(tenant, fkey, feats, infer, ts_ms)


async def worker(idx: int):
    """Consume la cola y procesa frames en paralelo."""
    while not shutdown.is_set():
        inner, vni = await packet_q.get()
        try:
            await process_frame(inner, vni)
            stats["handled_packets"] += 1
        finally:
            packet_q.task_done()


async def janitor():
    """Cierra ventanas inactivas (timeout) para no dejar flows pegados en memoria."""
    while not shutdown.is_set():
        await asyncio.sleep(1.0)
        now = time.time()
        stale = []
        async with win_lock:
            for fkey, ts in list(last_seen.items()):
                if (now - ts) > WINDOW_SECONDS:
                    stale.append(fkey)
            for fkey in stale:
                win = windows.get(fkey)
                if win:
                    feats = extract_features_from_window(win)
                    windows.pop(fkey, None)
                    last_seen.pop(fkey, None)
                else:
                    feats = None
        # hacer infer fuera del lock
        if stale:
            for fkey in stale:
                if feats:
                    tenant = fkey[0]
                    ts_ms = int(now * 1000)
                    infer = await model_infer(tenant, fkey, feats)
                    await persist_detection(tenant, fkey, feats, infer, ts_ms)


# -----------------------
# Control-plane: FastAPI
# -----------------------
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.udp_task = asyncio.create_task(udp_server())
    app.state.worker_tasks = [asyncio.create_task(worker(i)) for i in range(WORKERS)]
    app.state.janitor_task = asyncio.create_task(janitor())
    yield
    # Shutdown
    shutdown.set()
    with contextlib.suppress(Exception):
        if hasattr(app.state, "udp_task"):
            app.state.udp_task.cancel()
            await app.state.udp_task
        if hasattr(app.state, "worker_tasks"):
            for t in app.state.worker_tasks:
                t.cancel()
            await asyncio.gather(*app.state.worker_tasks, return_exceptions=True)
        if hasattr(app.state, "janitor_task"):
            app.state.janitor_task.cancel()
            await app.state.janitor_task

app = FastAPI(title="Ransomware Sensor Control-Plane", version="1.0.0", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "udp_port": VXLAN_PORT,
        "http_port": HTTP_PORT,
        "queue_size": packet_q.qsize(),
        "stats": stats,
        "window_params": {
            "WINDOW_SECONDS": WINDOW_SECONDS,
            "MAX_PKTS_PER_WINDOW": MAX_PKTS_PER_WINDOW,
        },
    }


@app.get("/stats")
def get_stats():
    return {
        "queue_size": packet_q.qsize(),
        "stats": stats,
        "active_flows": len(windows),
    }


@app.get("/detections/{tenant_id}")
def list_detections(
    tenant_id: str,
    start_ts: int = Query(..., description="Epoch ms desde"),
    end_ts: int = Query(..., description="Epoch ms hasta"),
    limit: int = Query(50, ge=1, le=1000),
    cursor: Optional[str] = Query(None, description="JSON de LastEvaluatedKey"),
):
    """
    Tabla con PK: TENANT#<id>, SK: FLOW#<five-tuple>#TS#<epoch_ms>
    """
    pk = f"{tenant_id}"
    sk_from = f"FLOW#"
    # entre dos tiempos: usamos begins_with + filtro por TS si no modelaste un rango directo.
    # Alternativa: SK como 'TS#<epoch>#FLOW#...' para rango eficiente por tiempo.
    eks: Optional[Dict[str, Any]] = json.loads(cursor) if cursor else None

    try:
        # Strategy: Query por PK y pagear; filtrar TS con FilterExpression (menos eficiente).
        # En producción, considerá modelar SK para rangos por tiempo o usar un GSI por TS.
        resp = table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk_from),
            Limit=limit,
            ExclusiveStartKey=eks,
            ProjectionExpression="#pk, #sk, verdict, score, srcIp, dstIp, proto, ts",
            ExpressionAttributeNames={"#pk": "PK", "#sk": "SK"},
            ReturnConsumedCapacity="TOTAL",
        )
        items = [
            it for it in resp.get("Items", [])
            if start_ts <= int(it.get("ts", 0)) <= end_ts
        ]
    except table.meta.client.exceptions.ProvisionedThroughputExceededException:
        raise HTTPException(status_code=429, detail="DynamoDB throttling, probá de nuevo")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    items = to_native(items)
    next_cursor = json.dumps(resp["LastEvaluatedKey"]) if "LastEvaluatedKey" in resp else None
    return {
        "items": items,
        "next_cursor": next_cursor,
        "count": len(items),
        "consumed_capacity": to_native(resp.get("ConsumedCapacity")),
    }
