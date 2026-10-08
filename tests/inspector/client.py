# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

"""Client for inspector.py (runs it as a subprocess, reads its stdout, sends scripts to its stdin)."""
import base64
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field

from qgis.PyQt.QtGui import QImage

from ..cli.utils import logger

DIR = os.path.dirname(os.path.abspath(__file__))
CONSOLE_RE = re.compile(r"^\[console\] (INFO|WARNING|ERROR) (.*?):(\d+) (.*)$")

IGNORE_WARNINGS = []


@dataclass
class ErrorCheckResult:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors


class InspectorClient:

    def __init__(self, filepath, timeout=60, size=None):
        # logger.debug("os.environ: " + str(os.environ))

        if sys.platform == "win32":
            cmd = [os.path.join(DIR, "inspector.bat")]
            sysroot = os.environ.get("SystemRoot", r"C:\Windows")
            path = os.pathsep.join([os.path.join(sysroot, "System32"), sysroot])
        else:
            cmd = [sys.executable or "python3", os.path.join(DIR, "inspector.py")]
            path = "/usr/bin:/bin"
        cmd += [filepath, "--timeout", str(timeout)]
        if size:
            cmd += ["--size", f"{size.width()}x{size.height()}"]

        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, encoding="utf-8", bufsize=1)
        self._lines = []                # all stdout lines
        self._results = queue.Queue()
        self._loaded = threading.Event()
        self._auto_exit_cancelled = threading.Event()
        self._lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self._proc.stdout:
            line = line.rstrip("\r\n")
            logger.info("[INSOUT]" + line)
            with self._lock:
                self._lines.append(line)

            if line.startswith("[result] "):
                self._results.put(line[9:])

            elif line.startswith("[pageload] "):
                self._loaded.set()

            elif line == "[cancel-auto-exit]":
                self._auto_exit_cancelled.set()

    def waitForLoad(self, timeout=30):
        return self._loaded.wait(timeout)

    def runScript(self, code, timeout=30):
        code = " ".join(code.splitlines())      # one line = one script
        self._proc.stdin.write(code + "\n")
        self._proc.stdin.flush()
        return json.loads(self._results.get(timeout=timeout))

    def waitForSceneLoadFinished(self, timeout=30):
        end = time.time() + timeout
        while not self.runScript("__qgis2threejs.app.sceneLoaded"):
            if time.time() > end:
                raise TimeoutError("Timed out waiting for scene load.")
            time.sleep(1)

    def renderScene(self):
        self.runScript("__qgis2threejs.app.render();")
        time.sleep(1)

    def capture(self):
        result = self.runScript("__capture__")
        if not isinstance(result, dict) or "png" not in result:
            raise RuntimeError(f"Failed to capture page: {result}")

        image = QImage.fromData(base64.b64decode(result["png"]), "PNG")
        if image.isNull():
            raise RuntimeError("Failed to decode captured page image.")

        logger.debug("Page captured.")
        return image

    def captureToFile(self, filename):
        image = self.capture()
        if not image.save(filename):
            raise OSError(f"Failed to save captured image to: {filename}")

        logger.info(f"Image saved to: {filename}")

    def waitIfAutoExitCancelled(self):
        if self._auto_exit_cancelled.is_set():
            self._proc.wait()

    def logs(self):
        with self._lock:
            return list(self._lines)

    def hasLog(self, text):
        return any(text in line for line in self.logs())

    def checkResult(self):
        result = ErrorCheckResult()
        for line in self.logs():
            m = CONSOLE_RE.match(line)
            if not m:
                continue
            level, msg = m.group(1), m.group(4)
            if level == "ERROR":
                result.errors.append(msg)
            elif level == "WARNING" and not any(i in msg for i in IGNORE_WARNINGS):
                result.warnings.append(msg)
        return result

    def close(self):
        if self._proc.poll() is not None:
            return

        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._proc.pid)], capture_output=True)
        else:
            self._proc.kill()
        self._proc.wait()
