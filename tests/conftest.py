import os
import pytest

@pytest.fixture(scope='session', autouse=True)
def set_qgis_environment():
    print("Setting QGIS environment variables for tests...")
    os.environ['QGIS_PREFIX_PATH'] = '/path/to/qgis'
    os.environ['PATH'] += os.pathsep + '/path/to/qgis/bin'
    os.environ['PYTHONPATH'] += os.pathsep + '/path/to/qgis/python'
    yield
    del os.environ['QGIS_PREFIX_PATH']
    del os.environ['PATH']
    del os.environ['PYTHONPATH']


@pytest.fixture(scope="session", autouse=True)
def qgis_app():
    """Initialize QGIS application for testing."""

    from qgis.core import QgsApplication
    print("Initializing QGIS Application for tests...")
    with open("D:/test.log", "a") as f:
        f.write("Initializing QGIS Application for tests...\n")
    app = QgsApplication([], False)
    app.initQgis()
    yield app
    app.exitQgis()
