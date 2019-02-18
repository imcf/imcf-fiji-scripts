"""Split '.tif' files in a dir by channels and z-slices and resave them."""

# pylint: disable-msg=C0103
# pylint: disable-msg=E0401
# pylint: disable-msg=line-too-long

#@ String(visibility=MESSAGE,persist=false,label="Split by Channels and Slices",value="") msg_header
#@ File(label="Input Directory",style="directory") src_dir
#@ Integer(label="Skip number of slices at top",value=0) skip_top
#@ Integer(label="Skip number of slices at bottom",value=0) skip_bottom
#@ LogService sjlogservice

import os

from imcflibs.imagej.split import split_by_c_and_z

# type checks and explicit pylint disabling for scijava parameters
src_dir = str(src_dir)  # pylint: disable-msg=E0601
skip_top = int(skip_top)   # pylint: disable-msg=E0601
skip_bottom = int(skip_bottom)   # pylint: disable-msg=E0601
log = sjlogservice  # pylint: disable-msg=E0602


for infile in os.listdir(src_dir):
    log.info("Processing directory [%s]" % src_dir)
    if infile.endswith('.tif'):
        split_by_c_and_z(log, src_dir, infile, skip_top, skip_bottom)
    else:
        log.info("Skipping [%s]" % infile)
