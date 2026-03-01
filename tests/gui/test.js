// (C) 2023 Minoru Akagi
// SPDX-License-Identifier: MIT
// https://github.com/minorua/Qgis2threejs

function floatEquals(a, b, precision) {
	if (typeof a === "object") {
		if (a.isBox3) return floatEquals(a.min, b.min, precision) && floatEquals(a.max, b.max, precision);
		if (a.isVector3) return floatEquals(a.x, b.x, precision) && floatEquals(a.y, b.y, precision) && floatEquals(a.z, b.z, precision);
		return false;
	}

	if (precision === undefined) return Math.abs(a - b) < Number.EPSILON;

	const factor = Math.pow(10, precision);
	return Math.round(a * factor) === Math.round(b * factor);
}

function Box3ToString(box3) {
	return "Box3: (" + box3.min.toArray() + ")-(" +  box3.max.toArray()+")";
}

function assertText(testName, text, startingElemId, partialMatch) {

	var compareText = function (elem, text, partialMatch) {

		if (partialMatch) {

			if (elem.innerText.indexOf(text) !== -1) return true;

		}
		else {

			if (elem.innerText == text) return true;

		}

		return false;

	};

	var result = false;

	if (startingElemId) {

		result = compareText(document.getElementById(startingElemId), text, partialMatch);

	}

	if (!result) {

		var elems = document.querySelectorAll((startingElemId) ? "#" + startingElemId + " *" : "*");

		for (var i = 0, l = elems.length; i < l && !result; i++) {

			result = compareText(elems[i], text, partialMatch);

		}

	}

	var message = text + (result ? "" : " not") + " found";
	if (startingElemId) message += " in element '" + startingElemId + "'";

	pyObj.sendTestResult(testName, result, message + ".");

}

function assertVisibility(testName, elemId, expected) {

	var elem = document.getElementById(elemId),
		visible = (window.getComputedStyle(elem).display != "none");

	pyObj.sendTestResult(testName, (visible == expected), "element '" + elemId + "' is " + (visible) ? "visible." : "invisible.");

}

function assertBox3(testName, box1, box2, precision) {

	var msg;

	if (box2 === undefined) {

		box2 = new THREE.Box3().setFromObject(app.scene);
		msg = "a box and scene bbox";

	}
	else {

		msg = "two boxes";

	}

	var result = floatEquals(box1, box2, precision);

	if (result) {

		result = true;
		msg += " are same.";

	}
	else {

		msg += " are not same.";

	}
	msg += Box3ToString(box1) + ", " + Box3ToString(box2) + " (" + precision + ")";

	pyObj.sendTestResult(testName, result, msg);

}

function assertZRange(testName, obj, min, max, precision) {

	var box = new THREE.Box3().setFromObject(obj);
	var result = true, msg = "";

	if (min !== undefined && !floatEquals(min, box.min.z, precision)) {

		result = false;
		msg += "bottom z is different from expected. (" + box.min.z + ", exptected: " + min + ", (" + precision + "))"

	}

	if (max !== undefined && !floatEquals(max, box.max.z, precision)) {

		result = false;
		msg += "top z is different from expected. (" + box.max.z + ", exptected: " + max + ", (" + precision + "))";

	}

	pyObj.sendTestResult(testName, result, msg);

}

var markerElem, markerTimerId;

function showMarker(x, y, msec) {
	if (markerElem) {
		markerElem.style.display = "block";
	}
	else {
		markerElem = document.createElement("div");
		markerElem.id = "testmarker";
		document.getElementById("view").appendChild(markerElem);
	}

	var hw = markerElem.offsetWidth / 2;
	markerElem.style.left = (x - hw) + "px";
	markerElem.style.top = (y - hw) + "px";

	if (markerTimerId) {
		clearTimeout(markerTimerId);
		markerTimerId = 0;
	}
	if (msec !== undefined)	markerTimerId = setTimeout(hideMarker, msec);
}

function hideMarker() {
	if (markerElem) {
		markerElem.style.display = "none";
	}
}
