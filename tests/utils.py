# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-14

import json
import jsonschema
import os
import shutil

from Qgis2threejs.utils.basic import pluginDir
from Qgis2threejs.utils.logging import logger

MY_TEST_TEMPDIR = "E:/dev/qgis2threejs_test"


def testDir(*subdirs):
    return pluginDir("tests", *subdirs)


def dataPath(*subdirs):
    dataDir = testDir("data")
    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def expectedDataPath(*subdirs):
    if os.path.exists(MY_TEST_TEMPDIR):
        dataDir = MY_TEST_TEMPDIR + "/expected"
    else:
        dataDir = testDir("expected")
        logger.warning("Expected data not exist.")      # TODO

    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def outputPath(*subdirs):
    if os.path.exists(MY_TEST_TEMPDIR):
        dataDir = MY_TEST_TEMPDIR + "/output"
    else:
        dataDir = testDir("output")

    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def initOutputDir(*subdirs):
    """initialize output directory"""
    out_dir = outputPath(*subdirs)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)


def assertMessagesAppearInOrder(logs, expected):
    """check if expected messages appear in logs in order"""
    it = iter(logs)
    for msg in expected:
        for log in it:
            if msg in log:
                break
        else:
            raise Exception(f'"{msg}" not found in logs in order.')


# Run `npm run setup-test` to generate JSON schemas from web/src/types.ts.
SCHEMA = None
SCHEMA_FILENAME = ""
VERBOSE = False
def assertValidData(data, type_name=None, convert_tuples=False, schema_filename="app.json"):
    global SCHEMA, SCHEMA_FILENAME
    if SCHEMA is None or SCHEMA_FILENAME != schema_filename:
        SCHEMA_FILENAME = schema_filename
        with open(pluginDir("web", "src", "schema", schema_filename), "r") as f:
            SCHEMA = json.load(f)

    if type_name:
        schema = {
            "$ref": f"#/definitions/{type_name}",
            "definitions": SCHEMA["definitions"],
        }
    else:
        schema = SCHEMA

    if VERBOSE:
        logger.debug("Validating: " + str(data))

    if convert_tuples:
        data = tuples_to_lists(data)

    try:
        jsonschema.validate(data, schema)

        data_type = data.get("type")
        label = f"{data_type} data" if data_type else "data without a type"
        logger.debug(f'[VALIDATION] {label} matches the {type_name or ""} schema.')

    except jsonschema.ValidationError as e:
        logger.error(str(e))
        raise e


def tuples_to_lists(obj):
    if isinstance(obj, dict):
        return {k: tuples_to_lists(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [tuples_to_lists(v) for v in obj]
    return obj


def contains_instance(obj, cls):
    if isinstance(obj, cls):
        return True

    if isinstance(obj, dict):
        return any(contains_instance(v, cls) for v in obj.values())

    if isinstance(obj, (list, tuple)):
        return any(contains_instance(v, cls) for v in obj)

    return False
