#@ File (label="Shading model file",description="float image with normalized shading model") model_file
#@ File (label="Folder with image files to be corrected",style="directory") in_dir
#@ String (label="Image file suffix",description='e.g. "oir", "ics", "czi"') suffix
#@ File (label="Output directory",style="directory") out_dir
#@ String(visibility=MESSAGE,persist=false,label="WARNING:",value="existing files in the output location will be overwritten without confirmation!") msg_warning
#@ LogService sjlogservice

"""Apply a normalized shading model to all multi-channel stacks in a given
directory and export the result to another directory, using the ICS2 format.

WARNING: existing files in the output directory will be silently overwritten!
"""

# import sjlogging

from imcflibs.imagej.shading import process_folder


FORMAT = ".ics"

# log = sjlogging.logger.setup_scijava_logger(sjlogservice)
# sjlogging.setter.set_loglevel('INFO')

process_folder(str(in_dir), suffix, str(out_dir), str(model_file), FORMAT)
