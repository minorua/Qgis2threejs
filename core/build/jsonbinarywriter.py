# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import base64
import json
import struct
import zlib


class BinaryContainer:

    def __init__(self, data: bytes, type: str, compress=True):
        """
        type: "I8", "f32", "I32"
        """
        self.data = data
        self.type = type
        self.compress = compress

    def toJSONCompatible(self, force_uncompressed=False):
        compress = self.compress and not force_uncompressed
        data = zlib.compress(self.data) if compress else self.data
        return {
            "_type": self.type,
            "compressed": compress,
            "data": base64.b64encode(data).decode("ascii")
        }

    def __repr__(self):
        return f"BinaryContainer(type={self.type}, size={len(self.data)}, compress={self.compress})"

    @classmethod
    def fromFloat(cls, value, compress=False):
        b = struct.pack("<f", float(value))
        return cls(b, "f32", compress=compress)


class JSONBinaryWriter:

    def __init__(self, data=None):
        self.data: dict = data or {}

    def toJSONCompatible(self, force_uncompressed=False):
        def convert(value):
            if isinstance(value, BinaryContainer):
                return value.toJSONCompatible(force_uncompressed)

            return traverse_nested(value, convert)

        return convert(self.data)

    def toBytes(self, force_uncompressed=False):
        offset = 0
        chunks = []

        def convert(value):
            nonlocal offset

            if isinstance(value, BinaryContainer):
                compress = value.compress and not force_uncompressed
                data = value.data
                metadata = {
                    "_type": value.type,
                    "offset": offset,
                    "size": len(data),
                    "compressed": compress
                }
                offset += len(data)
                chunks.append(data)
                return metadata

            return traverse_nested(value, convert)

        metadata = convert(self.data)
        json_bytes = json.dumps(metadata, separators=(",", ":")).encode("ascii")
        return struct.pack("<I", len(json_bytes)) + json_bytes + b"".join(chunks)

    def write(self, filepath):
        with open(filepath, "wb") as f:
            f.write(self.toBytes())


def traverse_nested(value, recurse):
    if isinstance(value, dict):
        return {k: recurse(v) for k, v in value.items()}
    if isinstance(value, list):
        return [recurse(v) for v in value]
    if isinstance(value, tuple):
        return [recurse(v) for v in value]
    return value
