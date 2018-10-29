#@ String(visibility=MESSAGE,persist=false,label="<html><div align='center'><h2>Stitching of<br>Olympus FluoView mosaics<br><br>OIF / OIB / OIR</h2></div></html>",value="<html><img src='http://imagej.net/_images/5/5e/Tiles-Overlay.png'></html>") msg_header
#@ File(label="<html><div align='left'><h3>Supported input files</h3>&bull; [ <tt>MATL_Mosaic.log</tt> ]<br/>&bull; [ <tt>matl.omp2info</tt> ]</div></html>",description="[ MATL_Mosaic.log ] or [ matl.omp2info ] file") infile
#@ String(visibility=MESSAGE,persist=false,label="<html><br/><br/><h3>Stitching Parameters</h3></html>",value="") msg_sec_stitching
#@ Boolean(label="Run registration",description="otherwise tiles will be fused based on stage coordinages",value=True) stitch_register
#@ Float(label="Regression threshold",description="lower if some tiles are completely off (registration takes longer then) [default=0.3]",value=0.3,min=0.01,max=1.0,stepSize=0.01,style="slider") stitch_regression
#@ Float(label="Ratio Max / Average displacement",description="increase if tiles are placed approximately right, but are still a bit off [default=2.5]",value=2.5,min=1,max=10,stepSize=0.1,style="slider") stitch_maxavg_ratio
#@ Float(label="Maximum absolute displacement",description="increase if some tiles are discarded completely [default=3.5]",value=3.5,min=1,max=20,stepSize=0.1,style="slider") stitch_abs_displace
#@ String(visibility=MESSAGE,persist=false,label="<html><br/><br/><h3>Output options</h3></html>",value="") msg_sec_output
#x#@ String(label="Output format", choices={"ICS/IDS","OME-TIFF"}) out_format
#@ Integer(label="Rotate result (clock-wise)", style="slider", min=0, max=270, value=0, stepSize=90) angle
#@ Boolean(label="Show generated code",description="Print generated code to log messages for debugging") print_code
#@ String(visibility=MESSAGE,label="<html><br/><h3>Citation note</h3></html>",value="<html><br/>Stitching is based on a publication, if you're using it for your research please <br>be so kind to cite it:<br><a href=''>Preibisch et al., Bioinformatics (2009)</a></html>",persist=false) msg_citation
#@ LogService sjlogservice

import sys
from os.path import join, dirname

from java.lang.System import getProperty
from ij import IJ

import micrometa
import micrometa.fluoview

from micrometa import imagej
from micrometa.strtools import flatten

from sjlogging import __version__ as sjlogver
from sjlogging.logger import setup_scijava_logger
from sjlogging.setter import set_loglevel


def gen_mosaic_details(mosaics):
    """Generate human readable string of details about the parsed mosaics."""
    # TODO: could go into fluoview package
    failcount = len(mosaics.mosaictrees) - len(mosaics)
    msg = "Parsed %i mosaics from the FluoView project.\n\n" % len(mosaics)
    if failcount > 0:
        msg += ("\n==== WARNING ====== WARNING ====\n\n"
                "Parsing failed on %i mosaic(s). Missing files?\n "
                "\n==== WARNING ====== WARNING ====\n\n\n" % failcount)
    for mos in mosaics:
        msg += "Mosaic %i: " % mos.supplement['index']
        msg += "%i x %i tiles, " % (mos.dim['X'], mos.dim['Y'])
        msg += "%.1f%% overlap.\n" % mos.get_overlap()
    return msg


def exit(msg):
    """Convenience wrapper to log an error and exit then."""
    log.error(msg)
    sys.exit(msg)


log = setup_scijava_logger(sjlogservice)
set_loglevel('DEBUG')

out_format = "ICS/IDS"

log.info("IMCF FluoView OIF / OIB / OIR Stitcher (%s).", 'UNKNOWN')
log.debug("python-scijava-logging version: %s", sjlogver)
log.debug("micrometa package version: %s", micrometa.__version__)
log.info("Parameter / selection summary:")
log.info("> Regression threshold: %s", stitch_regression)
log.info("> Max/Avg displacement ratio: %s", stitch_maxavg_ratio)
log.info("> Max absolute displacement: %s", stitch_abs_displace)
log.info("> output format: %s", out_format)
log.info("> rotation angle: %s", angle)
# convert the Java file object to a string since we only need the path:
infile = str(infile)

if infile[-9:] == '.omp2info':
    MosaicClass = micrometa.fluoview.FluoView3kMosaic
elif infile[-4:] == '.log':
    MosaicClass = micrometa.fluoview.FluoViewMosaic
else:
    exit('Unsupported input file: %s' % infile)

log.info("Parsing project file: [%s]" % infile)
IJ.showStatus("Parsing mosaics...")
mosaics = MosaicClass(infile, runparser=False)
step = 1.0 / len(mosaics.mosaictrees)
progress = 0.0
for i, subtree in enumerate(mosaics.mosaictrees):
    IJ.showProgress(progress)
    mosaics.add_mosaic(subtree, i)
    progress += step
IJ.showProgress(progress)
IJ.showStatus("Parsed %i mosaics." % len(mosaics))

if len(mosaics) == 0:
    exit("Couldn't find any (valid) mosaics in the project file!")
log.info(gen_mosaic_details(mosaics))

opts = {
    'export_format': '".ids"',
    'split_z_slices': 'false',
    'rotation_angle': angle,
    'stitch_regression': stitch_regression,
    'stitch_maxavg_ratio': stitch_maxavg_ratio,
    'stitch_abs_displace': stitch_abs_displace,
}
if not stitch_register:
    opts['compute'] = 'false'
if out_format == 'OME-TIFF':
    opts['export_format'] = '".ome.tif"'

tplpath = join(getProperty('fiji.dir'), 'jars', 'python-imcf-libs.jar')
log.info("Using macro templates from [%s]." % tplpath)
basedir = dirname(infile)
log.info("Using [%s] as base directory." % basedir)

code = imagej.gen_stitching_macro_code(mosaics,
                                       'micrometa/ijm_templates/stitching',
                                       basedir,
                                       tplpath,
                                       opts)

if print_code:
    log.info("============= generated macro code =============")
    log.info(flatten(code))
    log.info("============= end of generated  macro code =============")

log.info('Writing stitching macro.')
imagej.write_stitching_macro(code, 'stitch_all.ijm', basedir)
log.info('Writing tile configuration files.')
imagej.write_all_tile_configs(mosaics)
log.warn('Finished preprocessing, now launching the stitcher.')
IJ.runMacro(flatten(code))

