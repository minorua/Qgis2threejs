# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import base64
import json
import struct
import zlib


class BinaryContainer:

    def __init__(self, data: bytes, type: str, compress=True):
        self._data = data
        self.type = type
        self.compress = compress

    def data(self):
        return zlib.compress(self._data) if self.compress else self._data

    def toBase64(self):
        return base64.b64encode(self.data()).decode("ascii")

    def toJSONCompatible(self):
        return {
            "__type__": self.type,
            "compressed": self.compress,
            "data": self.toBase64()
        }

    def __repr__(self):
        return f"BinaryContainer(type={self.type}, compress={self.compress}, size={len(self.data())})"

    @classmethod
    def fromFloat(cls, value, compress=False):
        b = struct.pack("<f", float(value))
        return cls(b, "f32", compress=compress)


class JSONBinaryWriter:

    def __init__(self, data=None):
        self.data: dict = data or {}

    def toJSONCompatible(self):
        def convert(value):
            if isinstance(value, BinaryContainer):
                return value.toJSONCompatible()

            return traverse_nested(value, convert)

        return convert(self.data)

    def write(self, filepath):
        offset = 0
        chunks = []

        def convert(value):
            nonlocal offset

            if isinstance(value, BinaryContainer):
                data = value.data()
                metadata = {
                    "__type__": value.type,
                    "offset": offset,
                    "size": len(data),
                    "compressed": value.compress
                }
                offset += len(data)
                chunks.append(data)
                return metadata

            return traverse_nested(value, convert)

        metadata = convert(self.data)
        json_bytes = json.dumps(metadata, separators=(",", ":")).encode("ascii")

        with open(filepath, "wb") as f:
            f.write(struct.pack("<I", len(json_bytes)))
            f.write(json_bytes)

            for chunk in chunks:
                f.write(chunk)


def traverse_nested(value, recurse):
    if isinstance(value, dict):
        return {k: recurse(v) for k, v in value.items()}
    if isinstance(value, list):
        return [recurse(v) for v in value]
    if isinstance(value, tuple):
        return [recurse(v) for v in value]
    return value
