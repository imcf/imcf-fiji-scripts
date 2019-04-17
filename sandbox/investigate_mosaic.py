#@ LogService logservice

import io  # pylint: disable-msg=unused-import

from os.path import basename, dirname, join

import imcflibs
import micrometa
import ij

log = imcflibs.imagej.sjlog.scijava_logger(logservice)

log.info("micrometa version: %s", micrometa.__version__)
log.info("imcflibs version: %s", imcflibs.__version__)

infile = '/data/sample_data/fluoview/minimal_1mosaic_15pct/MATL_Mosaic.log'
mosaics = imcflibs.imagej.stitching.process_fluoview_project(infile)

print dir(mosaics[0].subvol[0])