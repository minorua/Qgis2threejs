#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
/***************************************************************************
 gdal2threejs.py
        begin                : 2013-12-20
        copyright            : (C) 2013 by Minoru Akagi
        email                : akaginch@gmail.com
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import sys
import struct
import base64

try:
  from osgeo import gdal
except ImportError:
  import gdal

def gdal2threejs(demfile, texfile, outfile="data.js", title="no title"):
  ds = gdal.Open(demfile, gdal.GA_ReadOnly)
  if ds is None:
    return "Cannot open dem file: " + demfile

  geotransform = ds.GetGeoTransform()
  if not geotransform is None:
    pass

  width = ds.RasterXSize
  height = ds.RasterYSize
  extent_width = geotransform[1] * (width - 1)
  extent_height = abs(geotransform[5] * (height - 1))
  #TODO
  #if degrees:
  #else:
  scale = 1.5
  multiplier = 100 * scale / extent_width

  values = []
  fs = "f" * width

  band = ds.GetRasterBand(1)
  for py in range(height):
    scanline = band.ReadRaster(0, py, width, 1, width, 1, gdal.GDT_Float32)
    values += map(lambda x: x * multiplier, struct.unpack(fs, scanline))

  with open(texfile, "rb") as f:
    subtype = os.path.splitext(texfile)[1][1:].lower().replace("jpg", "jpeg")
    tex = "data:image/%s;base64," % subtype
    tex += base64.b64encode(f.read())

  with open(outfile, "w") as f:
    f.write('document.title = "%s";\n' % title)
    f.write('var dem = {width:%d,height:%d,extent:{width:%f,height:%f},data:[%s]};\n' % (width, height, extent_width, extent_height, ",".join(map(formatValue, values))))
    f.write('var tex = "%s";\n' % tex)

  return 0

def formatValue(val, dap=6):
  if int(val) == val:
    return "%d" % val
  return ("%%.%df" % dap) % val

if __name__=="__main__":
  argv = sys.argv
  gdal2threejs(argv[1], argv[2], argv[3])
