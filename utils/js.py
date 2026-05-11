# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import base64
import re

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice

QGIS_AVAILABLE = False
try:
    from qgis.core import NULL
    QGIS_AVAILABLE = True
except ImportError:
    pass

from .logging import logger


def js_bool(o):
    return "true" if o else "false"


def css_color(c):
    if isinstance(c, list):
        if len(c) == 4 and c[3] != 255:
            return "rgba({},{},{},{:.2f})".format(*c[:3], c[3] / 255)

        return "rgb({},{},{})".format(*c[:3])

    return str(c).replace("0x", "#") if c else "#000000"


def hex_color(c, prefix="#"):
    if isinstance(c, list):
        return "{}{:02x}{:02x}{:02x}".format(prefix, *c[:3])

    if not c and prefix == "#":
        return "#000000"

    return prefix + str(c or 0).replace("0x", "").replace("#", "")


def int_color(c):
    if isinstance(c, list):
        return c[0] * 256 * 256 + c[1] * 256 + c[2]

    if isinstance(c, str):
        return int(c.replace("#", "0x") or "0", 16)

    return 0


def pyobj2js(obj, escape=False, quoteHex=True):
    """Convert a Python object to a JavaScript literal representation.

    Args:
        obj: dict/list/str/bool/number/bytes/qgis.core.NULL etc.
        escape: Whether to escape strings and wrap them in double quotes.
        quoteHex: Whether to quote strings in '0x...' hex format.

    Returns:
        str or number: a JS literal representation.
    """
    if isinstance(obj, dict):
        items = ["{0}:{1}".format(k, pyobj2js(v, escape, quoteHex)) for k, v in obj.items()]
        return "{" + ",".join(items) + "}"
    elif isinstance(obj, list):
        items = [str(pyobj2js(v, escape, quoteHex)) for v in obj]
        return "[" + ",".join(items) + "]"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, str):
        if escape:
            return '"' + obj.replace("\\", "\\\\").replace('"', '\\"') + '"'
        if not quoteHex and re.match("0x[0-9A-Fa-f]+$", obj):
            return obj
        return '"' + obj + '"'
    elif isinstance(obj, bytes):
        return pyobj2js(obj.decode("UTF-8"), escape, quoteHex)
    elif isinstance(obj, (int, float)):
        return obj
    elif QGIS_AVAILABLE and obj == NULL:   # qgis.core.NULL
        return "null"
    return '"' + str(obj) + '"'


def abchex(number):
    """Converts the number to hex and maps 0-9 to a-j and a-f to k-p.

    Args:
        number: Integer value.

    Returns:
        str: Converted string.
    """
    h = ""
    for c in "{:x}".format(number):
        i = ord(c)
        if i >= 97:   # a - f => k - p
            h += chr(i + 10)
        else:         # 0 - 9 => a - j
            h += chr(i + 49)
    return h


def image2dataUri(image, fmt="PNG"):
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, fmt.upper())
    return f"data:image/{fmt.lower()};base64," + ba.toBase64().data().decode("ascii")


def base64file(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except:
        logger.warning(f"Cannot read file: {file_path}")
        return ""


def imageFile2dataUri(file_path):
    imgType = os.path.splitext(file_path)[1].lower()[1:].replace("jpg", "jpeg")
    return f"data:image/{imgType};base64," + base64file(file_path)
