# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from collections.abc import Callable
from typing import TypeAlias

Vector3: TypeAlias = tuple[float, float, float]
Triangle: TypeAlias = tuple[Vector3, Vector3, Vector3]
Face: TypeAlias = tuple[int, int, int]

TransformFunc: TypeAlias = Callable[[float, float, float], Vector3]
ZFunc: TypeAlias = Callable[[float, float], float]
