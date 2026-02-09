from qgis import utils
from qgis.PyQt.QtWidgets import QMessageBox

def run_script(iface):
    wnd = utils.plugins["Qgis2threejs"].liveExporter

    msg = ""
    for n, o in [("taskQueue", wnd.controller.taskManager.taskQueue),
                 ("sendQueue", wnd.controller.sendQueue),
                 ("isTaskRunning", wnd.controller.taskManager.isTaskRunning),
                 ("isDataLoading", wnd.controller.isDataLoading)]:
       msg += f"{n}: {o}\n"

    QMessageBox.information(None, "Qgis2threejs Status", msg)
