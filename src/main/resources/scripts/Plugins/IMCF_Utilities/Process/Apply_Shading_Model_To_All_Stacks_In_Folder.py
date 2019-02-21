"""Apply a normalized shading model to all multi-channel stacks in a given
directory and export the result to another directory, using the ICS2 format.

WARNING: existing files in the output directory will be silently overwritten!
"""

# pylint: disable-msg=invalid-name
# pylint: disable-msg=line-too-long

#@ File (label="Shading model file",description="float image with normalized shading model") model_file
#@ File (label="Folder with image files to be corrected",style="directory") in_dir
#@ String (label="Image file suffix",description='e.g. "oir", "ics", "czi"') suffix
#@ File (label="Output directory",style="directory") out_dir
#@ String(visibility=MESSAGE,persist=false,label="WARNING:",value="existing files in the output location will be overwritten without confirmation!") msg_warning
#@ LogService sjlogservice

import imcflibs  # pylint: disable-msg=import-error
from imcflibs.imagej.shading import process_folder  # pylint: disable-msg=import-error


# type checks / default values and explicit pylint disabling for scijava params
in_dir = str(in_dir)  # pylint: disable-msg=used-before-assignment
suffix = str(suffix)  # pylint: disable-msg=used-before-assignment
out_dir = str(out_dir)  # pylint: disable-msg=used-before-assignment
model_file = str(model_file)  # pylint: disable-msg=used-before-assignment
logservice = sjlogservice  # pylint: disable-msg=undefined-variable

FORMAT = ".ics"

log = imcflibs.imagej.sjlog.scijava_logger(logservice)
log.info("Processing '%s' files in [%s]...", suffix, in_dir)

process_folder(in_dir, suffix, out_dir, model_file, FORMAT)
