#@ File(label="Folder with your images", style="directory", description="Input folder") src_dir
#@ File(label="Folder to save your images", style="directory", description="Output folder", required=False) out_dir
#@ String(label="Extension for the images to look for", value="nd2") filename_filter
#@ String(label="Save as file type", choices={"ICS-1","ICS-2","OME-TIFF", "ImageJ-TIF", "CellH5", "BMP"}) out_file_extension
#@ Boolean(label="Split channels ?", description="Split channels in channel specific folders ? ", value=False) split_channels

# ─── IMPORTS ────────────────────────────────────────────────────────────────────

import os
import fnmatch

from ij import IJ
from ij.plugin import StackWriter, Duplicator

# Bioformats imports
from loci.plugins import BF, LociExporter
from loci.plugins.in import ImporterOptions
from loci.plugins.out import Exporter
from loci.formats.in import MetadataOptions
from loci.formats import ImageReader
from loci.formats import MetadataTools

from imcflibs import pathtools
from imcflibs.imagej import bioformats as bf, misc

# ─── FUNCTIONS ──────────────────────────────────────────────────────────────────



# ─── MAIN CODE ──────────────────────────────────────────────────────────────────

if __name__  == "__main__":

    IJ.log("\\Clear")
    IJ.log("Script starting")

    # Retrieve list of files
    src_info = pathtools.parse_path(src_dir)

    if out_file_extension == "BMP":
        split_channels = False

    if out_dir is None:
        out_dir = pathtools.join2(src_info["full"], "out")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

    files = pathtools.listdir_matching(src_info["full"], filename_filter, fullpath=True, sort=True)

    pad_number = 0

    # # If the list of files is not empty
    if files:

        # For each file finishing with the filtered string
        for file_id, file in enumerate(sorted(files)):

            file_info = pathtools.parse_path(file)

            # Import the file with BioFormats
            misc.progressbar(file_id + 1, len(files), 1, "Processing: " + str(file_id))
            # IJ.log("\\Update3:Currently opening " + basename + "...")

            series_count, series_index = bf.get_series_info_from_ome_metadata(file)
            if not pad_number:
                pad_number = len(str(series_count))

            for series in range(series_count):
                misc.progressbar(series + 1, series_count, 2, "Opening series : ")

                imp = bf.import_image(file, series_number = series_index[series])[0]

                if "macro image" in imp.getTitle():
                    print("Skipping macro image...")
                    imp.close()
                    continue

                misc.save_image_in_format(
                    imp,
                    out_file_extension,
                    out_dir,
                    series,
                    pad_number,
                    split_channels
                )

                imp.close()

        IJ.log("\\Update3:Script finished !")