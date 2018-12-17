#@ ImagePlus (label="Shading model") shading_model
#@ File (label="Image file to be corrected",style="file") in_file
#@ String(label="Create projection images",choices={"None","Average","Maximum","ALL"}) proj
#@ File (label="Output directory",style="directory") out_dir
#@ String(visibility=MESSAGE,persist=false,label="WARNING:",value="existing files in the output location will be overwritten without confirmation!") msg_warning
#@ LogService log

"""Apply a normalized shading model to a multi-channel stack and export the
result to a given directory, by default using the ICS2 format.

The model needs to be opened in ImageJ before running the script.

WARNING: currently existing files will be silently overwritten!
"""

# import logging

from imcflibs.imagej.shading import correct_and_project

# import sjlogging


FORMAT = ".ics"

# log = sjlogging.logger.setup_scijava_logger(sjlogservice)
# sjlogging.setter.set_loglevel('INFO')
# log = logging.getLogger()


if __name__ in ['__main__', '__builtin__']:
    correct_and_project(str(in_file), str(out_dir), shading_model, proj, FORMAT)
