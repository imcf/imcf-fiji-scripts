"""Simplified wrapper script to stitch Olympus OIF / OIB / OIR mosaics."""

# pylint: disable-msg=invalid-name
# pylint: disable-msg=import-error
# pylint: disable-msg=line-too-long

#@ String(visibility=MESSAGE,persist=false,label="<html><div align='center'><h2>Basic stitching of<br>Olympus FluoView mosaics<br><br>OIF / OIB / OIR</h2></div></html>",value="<html><img src='http://imagej.net/_images/5/5e/Tiles-Overlay.png'></html>") msg_header
#@ File(label="<html><div align='left'><h3>Supported input files</h3>&bull; [ <tt>MATL_Mosaic.log</tt> ]<br/>&bull; [ <tt>matl.omp2info</tt> ]</div></html>",description="[ MATL_Mosaic.log ] or [ matl.omp2info ] file") infile
#@ File(label="Shading correction model",description="single slice, single channel, 32-bit float TIFF file",style="extensions:tif/tiff") model_file
#@ File(label="Output directory",description="location for results and intermediate processing files, specify 'NONE' or '-' to use input dir",style="directory", value="NONE", persist=false) out_dir
#@ String(label="Operation mode",choices={"FULL - preprocess + fuse","PREPROCESS ONLY - no fusion"}) mode

#@ String(visibility=MESSAGE,label="<html><br/><h3>Citation note</h3></html>",value="<html><br/>Stitching is based on a publication, if you're using it for your research please <br>be so kind to cite it:<br><a href=''>Preibisch et al., Bioinformatics (2009)</a></html>",persist=false) msg_citation
#@ LogService sjlogservice


# explicitly import the 'io' module: this is required due to namespace / import
# issues - otherwise the 'io' import later on done in the 'olefile' module will
# fail as 'io' is by then already populated with the corresponding Java class:
import io  # pylint: disable-msg=unused-import

import sys
from os.path import basename, dirname, join

import imcflibs
import micrometa
import ij

from java.lang.System import getProperty


# type checks / default values and explicit pylint disabling for scijava params
infile = str(infile)  # pylint: disable-msg=E0601
model_file = str(model_file)  # pylint: disable-msg=E0601
stitch_register = False
stitch_regression = 0.3
stitch_maxavg_ratio = 2.5
stitch_abs_displace = 3.5
out_dir = str(out_dir)  # pylint: disable-msg=E0601,E0602
angle = 0
mode = str(mode)  # pylint: disable-msg=E0601
logservice = sjlogservice  # pylint: disable-msg=E0602


log = imcflibs.imagej.sjlog.scijava_logger(logservice)

log.warn("%s, version: %s" % (basename(__file__), '${project.version}'))
log.info("micrometa version: %s", micrometa.__version__)
log.info("imcflibs version: %s", imcflibs.__version__)

indir = dirname(infile)
out_dir = imcflibs.pathtools.derive_out_dir(indir, out_dir)

mosaics = imcflibs.imagej.stitching.process_fluoview_project(infile)

imcflibs.imagej.shading.process_folder(
    indir,
    'oir',
    out_dir,
    model_file,
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
    'rotation_angle': angle,
    'stitch_regression': stitch_regression,
    'stitch_maxavg_ratio': stitch_maxavg_ratio,
    'stitch_abs_displace': stitch_abs_displace,
}
if not stitch_register:
    stitcher_options['compute'] = 'false'


code = imcflibs.imagej.stitching.gen_macro(
    mosaics,
    out_dir,
    join(indir, 'stitch_all.ijm'),
    stitcher_options
)

if mode[:4] == 'FULL':
    log.info('Finished preprocessing, now launching the stitcher.')
    ij.IJ.runMacro(imcflibs.strtools.flatten(code))
else:
    log.warn('PREPROCESSING mode selected, NOT running the stitcher now!')
