#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
/***************************************************************************
 gdal2threejs.py
        begin                : 2013-12-20
        copyright            : (C) 2013 Minoru Akagi
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

class Raster:
  def __init__(self, filename=""):
    self.ds = None
    self.filename = filename
    self.width = self.height = 0
    if filename:
      self.open(filename)

  def open(self, filename):
    filename_utf8 = filename.encode("UTF-8") if isinstance(filename, unicode) else filename
    self.ds = ds = gdal.Open(filename_utf8, gdal.GA_ReadOnly)
    if ds is None:
      return "Cannot open dem file: " + filename
    self.width = ds.RasterXSize
    self.height = ds.RasterYSize
    self.geotransform = ds.GetGeoTransform()
    if not self.geotransform is None:
      pass

  def close(self):
    self.ds = None

  def read(self, multiplier=1):
    if self.ds is None:
      return None
    values = []
    fs = "f" * self.width
    band = self.ds.GetRasterBand(1)
    for py in range(self.height):
      line = struct.unpack(fs, band.ReadRaster(0, py, self.width, 1, self.width, 1, gdal.GDT_Float32))
      if multiplier == 1:
        values += line
      else:
        values += map(lambda x: x * multiplier, line)
    return values

def base64image(filename):
  with open(filename, "rb") as f:
    subtype = os.path.splitext(filename)[1][1:].lower().replace("jpg", "jpeg")
    if subtype == "tif":
      subtype = "tiff"
    tex = "data:image/%s;base64," % subtype
    tex += base64.b64encode(f.read())
  return tex

def gdal2threejs(demfile, texfile, outfile="data.js", title="no title", suffix=""):

  dem = Raster(demfile)
  extent_width = dem.geotransform[1] * (dem.width - 1)
  extent_height = abs(dem.geotransform[5] * (dem.height - 1))
  #TODO
  #if degrees:
  #else:
  scale = 1.5
  multiplier = 100 * scale / extent_width
  values = dem.read(multiplier)

  tex = base64image(texfile)

  var = "var " if suffix == "" else ""
  with open(outfile, "w") as f:
    f.write('document.title = "%s";\n' % title)
    plane = "{width:%f,height:%f,offsetX:0,offsetY:0}" % (100, 100 * extent_height / extent_width)
    f.write('%sdem%s = {width:%d,height:%d,plane:%s,data:[%s]};\n' % (var, suffix, dem.width, dem.height, plane, ",".join(map(formatValue, values))))
    f.write('%stex%s = "%s";\n' % (var, suffix, tex))

  return 0

def formatValue(val, fmt="%.6f"):
  try:
    int(val)      # to filter invalid value (e.g. nan, inf. supposed type of val is float)
    return (fmt % val).rstrip("0").rstrip(".")
  except:
    return "-0"   # return -0 so that we can distinguish between 0 and error

if __name__=="__main__":
  argv = sys.argv
  gdal2threejs(argv[1], argv[2], argv[3])
