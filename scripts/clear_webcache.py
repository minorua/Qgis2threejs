""" This is a ScriptRunner script to clear QWebView's memory caches """

from PyQt5.QtWebKit import QWebSettings

def run_script(iface):
  QWebSettings.clearMemoryCaches()
