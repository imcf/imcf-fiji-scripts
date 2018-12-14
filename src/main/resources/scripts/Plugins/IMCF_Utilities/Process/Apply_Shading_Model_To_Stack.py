#@ ImagePlus (label="Shading model") shading_model
#@ File (label="Image file to be corrected",style="file") in_file
#@ Boolean (label="Create average projection images",value=false) avg
#@ Boolean (label="Create max intensity projection images",value=false) mip
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
from ij.plugin import ImageCalculator, RGBStackMerge, ZProjector

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


def bf_export(imp, path, in_file, tag, suffix):
    """Export an image to a given path, deriving the name from the input file.

    The input filename is stripped to its pure file name, without any path or
    suffix components, then an optional tag (e.g. "-avg") and the new format
    suffix is added.
    
    Parameters
    ----------
    imp : ImagePlus
        The ImagePlus object to be exported by Bio-Formats.
    path : str or object that can be cast to a str
        The output path.
    in_file : str or object that can be cast to a str
        The input file name, may contain arbitrary path components.
    tag : str
        An optional tag to be added at the end of the new file name, can be used
        to denote information like "-avg" for an average projection image.
    suffix : str
        The new file name suffix, which also sets the file format for BF.    
    """
    out_file = os.path.join(str(path),
                            image_file_name(str(in_file)) + tag + suffix)
    log.info("Exporting to [%s]", out_file)
    IJ.run(imp, "Bio-Formats Exporter", "save=[" + out_file + "]")
    log.debug("Exporting finished.")


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
bf_export(merged_imp, out_dir, in_file, "", FORMAT)

if avg:
    log.debug("Creating average projection...")
    avg_imp = ZProjector.run(merged_imp, "avg")
    bf_export(avg_imp, out_dir, in_file, "-avg", FORMAT)
    avg_imp.close()

if mip:
    log.debug("Creating maximum intensity projection...")
    mip_imp = ZProjector.run(merged_imp, "max")
    bf_export(mip_imp, out_dir, in_file, "-max", FORMAT)
    mip_imp.close()

# merged_imp.show()
merged_imp.close()

log.debug("Done processing [%s]", os.path.basename(str(in_file)))
