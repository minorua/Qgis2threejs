from qgis import utils
from qgis.PyQt.QtWidgets import QMessageBox

def run_script(iface):
    wnd = utils.plugins["Qgis2threejs"].liveExporter

    msg = ""
    for n, o in [("taskQueue", wnd.controller.taskManager.taskQueue),
                 ("isTaskRunning", wnd.controller.taskManager.isTaskRunning),
                 ("sendQueue", wnd.webPage.sendQueue),
                 ("isDataLoading", wnd.webPage.sendQueue.isDataLoading)]:
       msg += f"{n}: {o}\n"

    QMessageBox.information(None, "Qgis2threejs Status", msg)
