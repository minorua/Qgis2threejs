"use strict";

onmessage = function(event)
{
	var boundingBox = event.data.boundingBox;
	var position = new Float32Array(event.data.position);
	var numPoints = position.length / 3;
	var width = 64, height = 64;

	var boxSize =
	{
		x: boundingBox.max[0] - boundingBox.min[0],
		y: boundingBox.max[1] - boundingBox.min[1],
		z: boundingBox.max[2] - boundingBox.min[2]
	};

	var dem = new Float32Array(width * height);
	dem.fill(-Infinity);

	for(var i = 0; i < numPoints; i++)
	{
		var x = position[3 * i + 0];
		var y = position[3 * i + 1];
		var z = position[3 * i + 2];

		var dx = x / boxSize.x;
		var dy = y / boxSize.y;

		var ix = parseInt(Math.min(width * dx, width - 1));
		var iy = parseInt(Math.min(height * dy, height - 1));

		var index = ix + width * iy;
		dem[index] = z;
	}

	var message =
	{
		dem:
		{
			width: width,
			height: height,
			data: dem.buffer
		}
	};

	postMessage(message, [message.dem.data]);
};
