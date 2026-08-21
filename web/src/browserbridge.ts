// (C) 2026 Minoru Akagi
// SPDX-License-Identifier: MIT

import type { PyObj, PreviewData } from "./types.ts";

// must match Qgis2threejs.gui.ipc.socketinterface
const TYPE_EVENT = "EVT";
const TYPE_COMMAND = "CMD";
const TYPE_REQUEST = "REQ";
const TYPE_RESPONSE = "RES";

// must match Qgis2threejs.gui.ipc.ipc_const
const EVT_PAGE_LOAD_STARTED = "pageloadstart";
const EVT_PAGE_LOADED = "pageloaded";
const EVT_JS_ERROR_WARNING = "js_error";
const EVT_METHOD_INVOKED = "invoke";
const EVT_QUIT = "quit";			// NOT USED

const CMD_LOAD_DATA = "data";
const CMD_RELOAD = "reload";
const CMD_DEV_TOOLS = "devtools";	// NOT USED
const CMD_GPU_INFO = "gpuinfo";		// NOT USED

const REQ_RUN_SCRIPT = "run";
const REQ_SIZE = "size";


class SendDataSignal {
	private callbacks: Array<(data: PreviewData, viaQueue: boolean) => void> = [];

	connect(callback: (data: PreviewData, viaQueue: boolean) => void) {
		this.callbacks.push(callback);
	}

	emit(data: PreviewData, viaQueue: boolean) {
		for (const cb of this.callbacks) cb(data, viaQueue);
	}
}

const sendData = new SendDataSignal();

let ws: WebSocket;
const outgoingQueue: string[] = [];

function sendMessage(type: string, method: string, params: Record<string, unknown> = {}, id?: number) {
	const msg: Record<string, unknown> = { type, method, params };
	if (id !== undefined) msg.id = id;
	const json = JSON.stringify(msg);

	if (ws && ws.readyState === WebSocket.OPEN) {
		ws.send(json);
	} else {
		outgoingQueue.push(json);
	}
}

function invokeOnPython(name: string, args: unknown[]) {
	sendMessage(TYPE_EVENT, EVT_METHOD_INVOKED, { name, args });
}

function proxyMethod(name: string) {
	return (...args: unknown[]) => invokeOnPython(name, args);
}

const pyObj: PyObj = {
	sendData,

	emitInitialized: proxyMethod("emitInitialized"),
	emitDataLoaded: proxyMethod("emitDataLoaded"),
	emitDataLoadError: proxyMethod("emitDataLoadError"),
	emitSceneLoaded: proxyMethod("emitSceneLoaded"),
	emitScriptReady: proxyMethod("emitScriptReady"),
	emitTweenStarted: proxyMethod("emitTweenStarted"),
	emitAnimationStopped: proxyMethod("emitAnimationStopped"),

	showStatusMessage: proxyMethod("showStatusMessage"),
	saveBase64: proxyMethod("saveBase64"),
	saveText: proxyMethod("saveText"),
	saveImage: proxyMethod("saveImage"),
	copyToClipboard: proxyMethod("copyToClipboard"),

	emitRequestedRenderingFinished: proxyMethod("emitRequestedRenderingFinished"),
	sendTestResult: proxyMethod("sendTestResult")
};

window.pyObj = pyObj;

function runScript(script: string) {
	try {
		return (0, eval)(script);		// indirect eval
	} catch (e) {
		console.error("Script execution failed:", e);
		return null;
	}
}

function handleMessage(raw: string) {
	let msg: { type: string; id?: number; method?: string; params?: Record<string, any> };
	try {
		msg = JSON.parse(raw);
	} catch {
		console.error("Received an invalid message:", raw);
		return;
	}

	const { type, id, method } = msg;
	const params = msg.params || {};

	switch (type) {
		case TYPE_COMMAND:
			switch (method) {
				case CMD_LOAD_DATA:
					sendData.emit(params.data, params.viaQueue);
					break;
				case CMD_RELOAD:
					location.reload();
					break;
			}
			break;

		case TYPE_REQUEST:
			if (method === REQ_RUN_SCRIPT) {
				const result = runScript(params.script);
				sendMessage(TYPE_RESPONSE, method, { result }, id);
			}
			else if (method === REQ_SIZE) {
				sendMessage(TYPE_RESPONSE, method, { width: window.innerWidth, height: window.innerHeight }, id);
			}
			break;

		case TYPE_EVENT:
			break;
	}
}

window.addEventListener("load", () => {
	sendMessage(TYPE_EVENT, EVT_PAGE_LOADED, { ok: true });
});

window.addEventListener("error", (e) => {
	sendMessage(TYPE_EVENT, EVT_JS_ERROR_WARNING, {
		isError: true,
		message: e.message,
		lineNumber: e.lineno || -1,
		sourceID: e.filename || ""
	});
});

function connect() {
	ws = new WebSocket(`ws://${location.host}/ws`);

	ws.addEventListener("open", () => {
		sendMessage(TYPE_EVENT, EVT_PAGE_LOAD_STARTED);

		while (outgoingQueue.length) {
			ws.send(outgoingQueue.shift());
		}
	});

	ws.addEventListener("message", (e) => handleMessage(e.data));

	ws.addEventListener("close", () => {
		console.warn("Connection to QGIS was closed.");
		showMessageBar("Connection to Qgis2threejs was lost. Reopen the preview from Qgis2threejs if needed.");
		document.title = "[DISCONNECTED] " + document.title;
	});

	ws.addEventListener("error", () => {
		console.error("WebSocket connection error.");
	});
}

connect();
