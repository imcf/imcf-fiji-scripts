#@ String(visibility=MESSAGE,label="Save all open images as TIFF",value="",persist=false) msg_header
#@ File(label="Output Directory",style="directory") target_dir
#@ LogService log

# 2012-04-12 Niko Ehrenfeuchter
# Save all open windows as TIFF files, either as single TIF or as TIFF stack,
# depending on the content of the window (decided separately for each window).

# TODO:
#  * split code into setup() and run()
#  * let the user select a file and decide how it should be split (channel,
#    timepoints, positions, ...) and save it instead of using all open windows

from ij import WindowManager as wm
from ij.io import FileSaver
from os import path
import sys


target = str(target_dir)

wcount = wm.getWindowCount()
if wcount == 0:
	log.warn("No windows open, nothing to do.")
	sys.exit()

log.info("Number of open windows: %s" % wcount)
log.info("Selected [%s] as destination folder." % target)

# determine padding width for filenames
pad = len(str(wcount))

for wid in range(1, wcount+1):
	imp = wm.getImage(wid)
	imgid = wm.getNthImageID(wid)
	log.debug("window id: %s, imageID: %s" % (wid, wm.getNthImageID(wid)))
	
	# Construct filename
	filename = 'img_' + str(wid).zfill(pad) + '.tif'
	filepath = target + '/' + filename
	fs = FileSaver(imp)
	if imp.getImageStackSize() > 1:
		if not fs.saveAsTiffStack(filepath):
			log.error("Error saving current image, stopping.")
			sys.exit()
	else:
		if not fs.saveAsTiff(filepath):
			log.error("Error saving current image, stopping.")
			sys.exit()

log.info("Successfully saved %s files." % wcount)
