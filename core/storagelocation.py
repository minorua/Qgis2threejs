# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass
import os


@dataclass
class StorageLocation:

    outputDir: str
    baseUrl: str
    filePrefix: str

    def filename(self, fileTail: str) -> str:
        return self.filePrefix + fileTail

    def path(self, fileTail: str) -> str:
        return os.path.join(self.outputDir, self.filePrefix + fileTail)

    def url(self, fileTail: str) -> str:
        return f"{self.baseUrl}{self.filePrefix}{fileTail}"
