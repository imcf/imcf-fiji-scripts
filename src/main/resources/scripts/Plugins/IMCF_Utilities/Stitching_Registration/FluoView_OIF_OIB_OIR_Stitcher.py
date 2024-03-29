"""Wrapper script to stitch Olympus OIF / OIB / OIR mosaics."""

# pylint: disable-msg=C0103
# pylint: disable-msg=E0401
# pylint: disable-msg=line-too-long

#@ String(visibility=MESSAGE,persist=false,label="<html><div align='center'><h2>Stitching of<br>Olympus FluoView mosaics<br><br>OIF / OIB / OIR</h2></div></html>",value="<html><img src='http://imagej.net/_images/5/5e/Tiles-Overlay.png'></html>") msg_header
#@ File(label="<html><div align='left'><h3>Supported input files</h3>&bull; [ <tt>MATL_Mosaic.log</tt> ]<br/>&bull; [ <tt>matl.omp2info</tt> ]</div></html>",description="[ MATL_Mosaic.log ] or [ matl.omp2info ] file") infile
#@ String(visibility=MESSAGE,persist=false,label="<html><br/><br/><h3>Stitching Parameters</h3></html>",value="") msg_sec_stitching
#@ Boolean(label="Run registration",description="otherwise tiles will be fused based on stage coordinages",value=True) stitch_register
#@ Float(label="Regression threshold",description="lower if some tiles are completely off (registration will then take longer) [default=0.3]",value=0.3,min=0.01,max=1.0,stepSize=0.01,style="slider") stitch_regression
#@ Float(label="Ratio Max / Average displacement",description="increase if tiles are placed approximately right, but are still a bit off [default=2.5]",value=2.5,min=1,max=10,stepSize=0.1,style="slider") stitch_maxavg_ratio
#@ Float(label="Maximum absolute displacement",description="increase if some tiles are discarded completely [default=3.5]",value=3.5,min=1,max=20,stepSize=0.1,style="slider") stitch_abs_displace
#@ String(visibility=MESSAGE,persist=false,label="<html><br/><br/><h3>Output options</h3></html>",value="") msg_sec_output
#@ File(label="Output directory",description="location for results and intermediate processing files, type 'NONE' or '-' to use input dir",style="directory", value="NONE", persist=false) out_dir
#@ Integer(label="Rotate result (clock-wise)", style="slider", min=0, max=270, value=0, stepSize=90) angle
#@ String(visibility=MESSAGE,label="<html><br/><h3>Citation note</h3></html>",value="<html><br/>Stitching is based on a publication, if you're using it for your research please <br>be so kind to cite it:<br><a href=''>Preibisch et al., Bioinformatics (2009)</a></html>",persist=false) msg_citation
#@ LogService sjlogservice


# explicitly import the 'io' module: this is required due to namespace / import
# issues - otherwise the 'io' import later on done in the 'olefile' module will
# fail as 'io' is by then already populated with the corresponding Java class:
import io  # pylint: disable-msg=unused-import

import sys
from os.path import basename, dirname, join

import imcflibs
from imcflibs.imagej.misc import show_status, show_progress

import micrometa
import ij

from java.lang.System import getProperty


def error_exit(msg):
    """Convenience wrapper to log an error and exit then."""
    log.error(msg)
    sys.exit(msg)


# type checks and explicit pylint disabling for scijava parameters
infile = str(infile)  # pylint: disable-msg=E0601
stitch_register = bool(stitch_register)  # pylint: disable-msg=E0601
stitch_regression = float(stitch_regression)  # pylint: disable-msg=E0601
stitch_maxavg_ratio = float(stitch_maxavg_ratio)  # pylint: disable-msg=E0601
stitch_abs_displace = float(stitch_abs_displace)  # pylint: disable-msg=E0601
out_dir = str(out_dir)  # pylint: disable-msg=E0601,E0602
angle = int(angle)   # pylint: disable-msg=E0601
logservice = sjlogservice  # pylint: disable-msg=E0602


log = imcflibs.imagej.sjlog.scijava_logger(logservice)

log.warn("%s, version: %s" % (basename(__file__), '${project.version}'))
log.info("micrometa version: %s", micrometa.__version__)
log.info("imcflibs version: %s", imcflibs.__version__)

log.info("Parameter / selection summary:")
log.info("> Regression threshold: %s", stitch_regression)
log.info("> Max/Avg displacement ratio: %s", stitch_maxavg_ratio)
log.info("> Max absolute displacement: %s", stitch_abs_displace)
log.info("> rotation angle: %s", angle)

indir = dirname(infile)

if infile[-9:] == '.omp2info':
    MosaicClass = micrometa.fluoview.FluoView3kMosaic
elif infile[-4:] == '.log':
    MosaicClass = micrometa.fluoview.FluoViewMosaic
else:
    error_exit('Unsupported input file: %s' % infile)

log.info("Parsing project file: [%s]" % infile)
ij.IJ.showStatus("Parsing mosaics...")

mosaics = MosaicClass(infile, runparser=False)
total = len(mosaics.mosaictrees)
ij.IJ.showProgress(0.0)
show_status("Parsed %s / %s mosaics" % (0, total))
for i, subtree in enumerate(mosaics.mosaictrees):
    log.info("Parsing mosaic %s...", i+1)
    try:
        mosaics.add_mosaic(subtree, i)
    except (ValueError, IOError) as err:
        log.warn('Skipping mosaic %s: %s', i, err)
    except RuntimeError as err:
        log.warn('Error parsing mosaic %s, SKIPPING: %s', i, err)
    show_progress(i, total)
    show_status("Parsed %s / %s mosaics" % (i+1, total))
show_progress(total, total)
show_status("Parsed %i mosaics." % total)

if not mosaics:
    error_exit("Couldn't find any (valid) mosaics in the project file!")
log.info(mosaics.summarize())

if out_dir in ["-", "NONE"]:
    out_dir = indir
    log.info("No output directory given, using input directory [%s]." % out_dir)
else:
    log.info("Using directory [%s] for results and temp files." % out_dir)

log.info('Writing tile configuration files.')
write_tile_configs = micrometa.imagej.write_all_tile_configs
write_tile_configs(mosaics, out_dir)

stitcher_options = {
    'export_format': '".ids"',
    'split_z_slices': 'false',
    'rotation_angle': angle,
    'stitch_regression': stitch_regression,
    'stitch_maxavg_ratio': stitch_maxavg_ratio,
    'stitch_abs_displace': stitch_abs_displace,
}
if not stitch_register:
    stitcher_options['compute'] = 'false'

template_path = join(getProperty('fiji.dir'), 'jars', 'python-micrometa.jar')
log.info("Using macro templates from [%s]." % template_path)
log.info("Using [%s] as base directory." % indir)

code = micrometa.imagej.gen_stitching_macro(
    name=mosaics.infile['dname'],
    path=out_dir,
    tplpfx='templates/imagej-macro/stitching',
    tplpath=template_path,
    opts=stitcher_options
)

log.debug("============= generated macro code =============")
log.debug(imcflibs.strtools.flatten(code))
log.debug("============= end of generated  macro code =============")

log.info('Writing stitching macro.')
micrometa.imagej.write_stitching_macro(code, 'stitch_all.ijm', indir)
log.warn('Finished preprocessing, now launching the stitcher.')
ij.IJ.runMacro(imcflibs.strtools.flatten(code))
