# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from collections.abc import Callable

# types
Vector3 = tuple[float, float, float]
Triangle = tuple[Vector3, Vector3, Vector3]
Face = tuple[int, int, int]

TransformFunc = Callable[[float, float, float], Vector3]
ZFunc = Callable[[float, float], float]
