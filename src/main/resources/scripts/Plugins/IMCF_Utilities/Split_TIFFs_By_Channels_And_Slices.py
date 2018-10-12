#@ String(visibility=MESSAGE,persist=false,label="Split by Channels and Slices",value="") msg_header
#@ File(label="Input Directory",style="directory") src_dir
#@ Integer(label="Skip number of slices at top",value=0) skip_top
#@ Integer(label="Skip number of slices at bottom",value=0) skip_bottom
#@ LogService log

from ij import IJ, ImagePlus
from ij.io import FileSaver
from ij.plugin import ChannelSplitter

import os


def split_by_c_and_z(dname, imgf, skip_top, skip_bottom):
    log.info("Processing file [%s]" % imgf)
    imp = IJ.openImage(dname + "/" + imgf)
    fname = os.path.splitext(imgf)
    channels = ChannelSplitter().split(imp)
    for channel in channels:
        ch_name = channel.getTitle().split("-")[0]
        tgt_dir = os.path.join(dname, fname[0] + "-" + ch_name)
        if not os.path.isdir(tgt_dir):
            os.mkdir(tgt_dir)
        stack = channel.getStack()
        for z in range(1+skip_top, stack.getSize()+1-skip_bottom):
            ip = stack.getProcessor(z)
            fout = "%s/%s-z%s%s" % (tgt_dir, fname[0], z, fname[1])
            # fout = dname + "/" + ch_name + "/" + fname[0] + "-z" + z + fname[1]
            log.info("Writing channel %s, slice %s: %s" % (ch_name, z, fout))
            FileSaver(ImagePlus(fname[0], ip)).saveAsTiff(fout)

src_dir = str(src_dir)
for file in os.listdir(src_dir):
    log.info("Processing directory [%s]" % src_dir)
    if file.endswith('.tif'):
        split_by_c_and_z(src_dir, file, skip_top, skip_bottom)
    else:
        log.info("Skipping [%s]" % file)
