#@ ImagePlus (label="Shading model") shading_model
#@ File (label="Image file to be corrected",style="file") in_file
#@ File (label="Output directory",style="directory") out_dir
#@ String(visibility=MESSAGE,persist=false,label="WARNING:",value="existing files in the output location will be overwritten without confirmation!") msg_warning

#@ LogService sjlogservice

"""Apply a normalized shading model to a multi-channel stack and export the
result to a given directory, by default using the ICS2 format.

The model needs to be opened in ImageJ before running the script.

WARNING: currently existing files will be silently overwritten!
"""


import os

from loci.plugins import BF
from loci.plugins.in import ImporterOptions

from ij import IJ
from ij.plugin import ImageCalculator, RGBStackMerge

import sjlogging


FORMAT = ".ics"


def image_file_name(orig_name):
    """Return the file name component without suffix.

    Pseudo-smart function to strip away the path and suffix of a given file
    name, with special treatment for the composite suffix ".ome.tif(f)" which
    will be fully stripped as well.
    """
    base = os.path.splitext(os.path.basename(orig_name))[0]
    if base.lower().endswith('.ome'):
        base = base[:-4]
    return base


log = sjlogging.logger.setup_scijava_logger(sjlogservice)
sjlogging.setter.set_loglevel('DEBUG')

options = ImporterOptions()
options.setColorMode(ImporterOptions.COLOR_MODE_COLORIZED)
options.setSplitChannels(True)
options.setId(str(in_file))
log.info("Reading [%s]", str(in_file))
orig_imps = BF.openImagePlus(options)

ic = ImageCalculator()
for channel_imp in orig_imps:
    log.debug("Processing channel...")
    ic.run("Divide stack", channel_imp, shading_model)

merger = RGBStackMerge()
merged_imp = merger.mergeChannels(orig_imps, False)
# merged_imp.show()

out_file = os.path.join(str(out_dir), image_file_name(str(in_file)) + FORMAT)
log.info("Exporting to [%s]", out_file)
IJ.run(merged_imp, "Bio-Formats Exporter", "save=[" + out_file + "]")
log.info("Exporting finished.")
merged_imp.close()
