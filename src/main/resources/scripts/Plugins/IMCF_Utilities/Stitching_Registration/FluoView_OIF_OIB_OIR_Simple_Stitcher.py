#@ String(visibility=MESSAGE,persist=false,label="<html><div align='center'><h2>Basic stitching of<br>Olympus FluoView mosaics<br><br>OIF / OIB / OIR</h2></div></html>",value="<html><img src='http://imagej.net/_images/5/5e/Tiles-Overlay.png'></html>") msg_header
#@ File(label="<html><div align='left'><h3>Supported input files</h3>&bull; [ <tt>MATL_Mosaic.log</tt> ]<br/>&bull; [ <tt>matl.omp2info</tt> ]</div></html>",description="[ MATL_Mosaic.log ] or [ matl.omp2info ] file") infile
#@ File(label="Shading correction model",description="single slice, single channel, 32-bit float TIFF file",style="extensions:tif/tiff") model_file
#@ File(label="Output directory",description="location for results and intermediate processing files, type 'NONE' or '-' to use input dir",style="directory", value="NONE", persist=false) out_dir
#@ String(label="Operation mode",choices={"FULL - preprocess + fuse","PREPROCESS ONLY - no fusion"}) mode

#@ String(visibility=MESSAGE,label="<html><br/><h3>Citation note</h3></html>",value="<html><br/>Stitching is based on a publication, if you're using it for your research please <br>be so kind to cite it:<br><a href=''>Preibisch et al., Bioinformatics (2009)</a></html>",persist=false) msg_citation
#@ LogService sjlogservice

# pylint: disable-msg=C0103
# pylint: disable-msg=E0401

import io  # required due to namespace / import issues (otherwise olefile fails)
import sys
from os.path import basename, dirname, join

import imcflibs
from imcflibs.imagej.misc import show_status, show_progress

import micrometa
import sjlogging
import ij

from java.lang.System import getProperty


def error_exit(msg):
    """Convenience wrapper to log an error and exit then."""
    log.error(msg)
    sys.exit(msg)


log = sjlogging.setup_logger(sjlogservice)
LOG_LEVEL = "INFO"
if imcflibs.imagej.prefs.debug_mode():
    log.warn("Enabling debug logging.")
    LOG_LEVEL = "DEBUG"
sjlogging.set_loglevel(LOG_LEVEL)

log.warn("%s, version: %s" % (basename(__file__), '${project.version}'))
log.info("python-scijava-logging version: %s", sjlogging.__version__)
log.info("micrometa version: %s", micrometa.__version__)
log.info("imcflibs version: %s", imcflibs.__version__)

# convert the Java file object to a string since we only need the path:
infile = str(infile)
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
show_status(log, "Parsed %s / %s mosaics" % (0, total))
for i, subtree in enumerate(mosaics.mosaictrees):
    log.info("Parsing mosaic %s...", i+1)
    try:
        mosaics.add_mosaic(subtree, i)
    except (ValueError, IOError) as err:
        log.warn('Skipping mosaic %s: %s', i, err)
    except RuntimeError as err:
        log.warn('Error parsing mosaic %s, SKIPPING: %s', i, err)
    show_progress(log, i, total)
    show_status(log, "Parsed %s / %s mosaics" % (i+1, total))
show_progress(log, total, total)
show_status(log, "Parsed %i mosaics." % total)

if not mosaics:
    error_exit("Couldn't find any (valid) mosaics in the project file!")
log.info(mosaics.summarize())

out_dir = str(out_dir)
if out_dir in ["-", "NONE"]:
    out_dir = indir
    log.info("No output directory given, using input directory [%s]." % out_dir)
else:
    log.info("Using directory [%s] for results and temp files." % out_dir)

log.info("Pre-processing stacks: shading correction and projections...")
imcflibs.imagej.shading.process_folder(
    indir,
    'oir',
    out_dir,
    str(model_file),
    '.ics'
)

log.info('Writing tile configuration files.')
write_tile_configs = micrometa.imagej.write_all_tile_configs
write_tile_configs(mosaics, out_dir, '.ics')
write_tile_configs(mosaics, out_dir, '-avg.ics', force_2d=True)
write_tile_configs(mosaics, out_dir, '-max.ics', force_2d=True)


stitcher_options = {
    'export_format': '".ids"',
    'split_z_slices': 'false',
    'rotation_angle': 0,
    'stitch_regression': 0.3,
    'stitch_maxavg_ratio': 2.5,
    'stitch_abs_displace': 3.5,
    'compute': 'false',
}

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
if mode[:4] == 'FULL':
    log.info('Finished preprocessing, now launching the stitcher.')
    ij.IJ.runMacro(imcflibs.strtools.flatten(code))
else:
    log.warn('PREPROCESSING mode selected, NOT running the stitcher now!')
