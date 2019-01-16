#@ String(visibility=MESSAGE,persist=false,label="<html><div align='center'><h2>Pre-processing of<br>Olympus FluoView mosaics<br><br>OIF / OIB / OIR</h2></div></html>",value="<html><img src='http://imagej.net/_images/5/5e/Tiles-Overlay.png'></html>") msg_header
#@ File(label="<html><div align='left'><h3>Supported input files</h3>&bull; [ <tt>MATL_Mosaic.log</tt> ]<br/>&bull; [ <tt>matl.omp2info</tt> ]</div></html>",description="[ MATL_Mosaic.log ] or [ matl.omp2info ] file") infile
#@ File(label="Shading correction model",description="single slice, single channel TIFF file",style="extensions:tif/tiff") model_file
#@ File(label="Output directory",description="location for results and intermediate processing files, use 'NONE' for input dir",style="directory", value="NONE", persist=false) out_dir
#@ Boolean(label="Show generated code",description="Print generated code to log messages for debugging") print_code

#@ String(visibility=MESSAGE,label="<html><br/><h3>Citation note</h3></html>",value="<html><br/>Stitching is based on a publication, if you're using it for your research please <br>be so kind to cite it:<br><a href=''>Preibisch et al., Bioinformatics (2009)</a></html>",persist=false) msg_citation
#@ LogService sjlogservice

# pylint: disable-msg=C0103
# pylint: disable-msg=E0401

import io  # required due to namespace / import issues (otherwise olefile fails)
import sys
from os.path import dirname, join

import imcflibs
import micrometa
from ij import IJ
from imcflibs.imagej import shading
from java.lang.System import getProperty
from micrometa import fluoview, imagej
from sjlogging import __version__ as sjlogver
from sjlogging.logger import setup_scijava_logger
from sjlogging.setter import set_loglevel


stitch_register = False


def exit(msg):
    """Convenience wrapper to log an error and exit then."""
    log.error(msg)
    sys.exit(msg)


log = setup_scijava_logger(sjlogservice)
set_loglevel('DEBUG')

out_format = "ICS/IDS"

log.warn("IMCF FluoView OIF / OIB / OIR Stitcher (%s).", 'UNKNOWN')
log.debug("python-scijava-logging version: %s", sjlogver)
log.debug("micrometa package version: %s", micrometa.__version__)
log.debug("imcflibs package version: %s", imcflibs.__version__)
# convert the Java file object to a string since we only need the path:
infile = str(infile)
indir = dirname(infile)

if infile[-9:] == '.omp2info':
    MosaicClass = fluoview.FluoView3kMosaic
elif infile[-4:] == '.log':
    MosaicClass = fluoview.FluoViewMosaic
else:
    exit('Unsupported input file: %s' % infile)

log.info("Parsing project file: [%s]" % infile)
IJ.showStatus("Parsing mosaics...")

mosaics = MosaicClass(infile, runparser=False)
step = 1.0 / len(mosaics.mosaictrees)
progress = 0.0
for i, subtree in enumerate(mosaics.mosaictrees):
    IJ.showProgress(progress)
    try:
        mosaics.add_mosaic(subtree, i)
    except (ValueError, IOError) as err:
        log.warn('Skipping mosaic %s: %s', i, err)
    except RuntimeError as err:
        log.warn('Error parsing mosaic %s, SKIPPING: %s', i, err)
    progress += step
IJ.showProgress(progress)
IJ.showStatus("Parsed %i mosaics." % len(mosaics))

if len(mosaics) == 0:
    exit("Couldn't find any (valid) mosaics in the project file!")
log.info(mosaics.summarize())

outdir = str(out_dir)
if outdir == "-" or outdir == "NONE":
    outdir = indir
    log.info("No output directory given, using input directory [%s]." % outdir)
else:
    log.info("Using output directory [%s] for results and temp files." % outdir)

log.info("Pre-processing stacks: shading correction and projections...")
shading.process_folder(indir, 'oir', outdir, str(model_file), '.ics')

log.info('Writing tile configuration files.')
imagej.write_all_tile_configs(mosaics, outdir, '.ics')
imagej.write_all_tile_configs(mosaics, outdir, '-avg.ics', force_2d=True)
imagej.write_all_tile_configs(mosaics, outdir, '-max.ics', force_2d=True)


stitcher_options = {
    'export_format': '".ids"',
    'split_z_slices': 'false',
    'rotation_angle': 0,
    'stitch_regression': 0.3,
    'stitch_maxavg_ratio': 2.5,
    'stitch_abs_displace': 3.5,
}
if not stitch_register:
    stitcher_options['compute'] = 'false'
if out_format == 'OME-TIFF':
    stitcher_options['export_format'] = '".ome.tif"'

template_path = join(getProperty('fiji.dir'), 'jars', 'python-micrometa.jar')
log.info("Using macro templates from [%s]." % template_path)
log.info("Using [%s] as base directory." % indir)

code = imagej.gen_stitching_macro(
    name=mosaics.infile['dname'],
    path=outdir,
    tplpfx='templates/imagej-macro/stitching',
    tplpath=template_path,
    opts=stitcher_options
)

if print_code:
    log.info("============= generated macro code =============")
    log.info(imcflibs.strtools.flatten(code))
    log.info("============= end of generated  macro code =============")

log.info('Writing stitching macro.')
imagej.write_stitching_macro(code, 'stitch_all.ijm', indir)
log.warn('Finished preprocessing, now launching the stitcher.')
IJ.runMacro(imcflibs.strtools.flatten(code))
