# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later


class DataManager:
    """ manages a list of unique items """

    def __init__(self):
        self._list = []

    def count(self):
        return len(self._list)

    def _index(self, data):
        if data in self._list:
            return self._list.index(data)

        index = len(self._list)
        self._list.append(data)
        return index
