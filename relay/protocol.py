"""Shared TCP framing helpers for the GauSS-MI relay."""

from __future__ import annotations

import json
import socket
import struct
from typing import Any, Dict, Optional, Tuple


_U32 = struct.Struct("!I")


def _recv_exact(sock: socket.socket, size: int) -> Optional[bytes]:
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_frame(sock: socket.socket, meta: Dict[str, Any], payload: bytes = b"") -> None:
    meta_bytes = json.dumps(meta, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sock.sendall(_U32.pack(len(meta_bytes)))
    sock.sendall(meta_bytes)
    sock.sendall(_U32.pack(len(payload)))
    if payload:
        sock.sendall(payload)


def recv_frame(sock: socket.socket) -> Optional[Tuple[Dict[str, Any], bytes]]:
    meta_len_bytes = _recv_exact(sock, _U32.size)
    if meta_len_bytes is None:
        return None
    (meta_len,) = _U32.unpack(meta_len_bytes)
    meta_bytes = _recv_exact(sock, meta_len)
    if meta_bytes is None:
        return None
    payload_len_bytes = _recv_exact(sock, _U32.size)
    if payload_len_bytes is None:
        return None
    (payload_len,) = _U32.unpack(payload_len_bytes)
    payload = _recv_exact(sock, payload_len)
    if payload is None:
        return None
    return json.loads(meta_bytes.decode("utf-8")), payload
