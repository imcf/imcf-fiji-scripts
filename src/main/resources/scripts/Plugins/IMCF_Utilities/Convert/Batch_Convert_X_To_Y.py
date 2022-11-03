#@ File(label="Folder with your images", style="directory", description="Input folder") src_dir
#@ File(label="Folder to save your images", style="directory", description="Output folder") out_dir
#@ String(label="Extension for the images to look for", value="nd2") filename_filter
#@ String(label="Save as file type", choices={"ICS-1","ICS-2","OME-TIFF1","OME-TIFF2", "ImageJ-TIF", "CellH5", "BMP"}) out_file_extension

# ─── IMPORTS ────────────────────────────────────────────────────────────────────

import os
import shutil

from ij import IJ
from ij.plugin import StackWriter

# Bioformats imports
from loci.plugins import BF, LociExporter
from loci.plugins.in import ImporterOptions
from loci.plugins.out import Exporter

from java.lang import Exception

# ─── FUNCTIONS ──────────────────────────────────────────────────────────────────

def getFileList(directory, filteringString):
    """Get a list of files with the extension

    Parameters
    ----------
    directory : str
        Path of the files to look at
    filteringString : str
        Extension to look for

    Returns
    -------
    list
        List of files with the extension in the folder
    """

    files = []
    for (dirpath, dirnames, filenames) in os.walk(directory):
        # if out_dir in dirnames: # Ignore destination directory
            # dirnames.remove(OUT_SUBDIR)
        for f in filenames:
            if filteringString in f:
                files.append(os.path.join(dirpath, f))
    return (files)

def BFImport(indivFile):
    """Import using BioFormats

    Parameters
    ----------
    indivFile : str
        Path of the file to open

    Returns
    -------
    imps : ImagePlus
        Image opened via BF
    """
    options = ImporterOptions()
    options.setId(str(indivFile))
    options.setColorMode(ImporterOptions.COLOR_MODE_GRAYSCALE)
    return BF.openImagePlus(options)

def BFExport(imp, savepath):
    """Export using BioFormats

    Parameters
    ----------
    imp : ImagePlus
        ImagePlus of the file to save
    savepath : str
        Path where to save the image

    """
    paramstring = "outfile=[" + savepath + "] windowless=true compression=Uncompressed saveROI=false"


    print('Savepath: ', savepath)
    plugin     = LociExporter()
    plugin.arg = paramstring
    exporter   = Exporter(plugin, imp)
    exporter.run()

def progress_bar(progress, total, line_number, prefix=''):
    """Progress bar for the IJ log window

    Parameters
    ----------
    progress : int
        Current step of the loop
    total : int
        Total number of steps for the loop
    line_number : int
        Number of the line to be updated
    prefix : str, optional
        Text to use before the progress bar, by default ''
    """

    size = 30
    x    = int(size*progress/total)
    IJ.log("\\Update%i:%s\t[%s%s] %i/%i\r" % (line_number, prefix, "#"*x, "."*(size-x), progress, total))


# ─── MAIN CODE ──────────────────────────────────────────────────────────────────

IJ.log("\\Clear")
IJ.log("Script starting")

# Retrieve list of files
src_dir = str(src_dir)
out_dir = str(out_dir)
files = getFileList(src_dir, filename_filter)

out_ext = {}
out_ext["ImageJ-TIF"] = ".tif"
out_ext["ICS-1"] = ".ids"
out_ext["ICS-2"] = ".ics"
out_ext["OME-TIFF1"] = ".ome.tif"
out_ext["OME-TIFF2"] = ".tif"
out_ext["CellH5"] = ".ch5"
out_ext["BMP"] = ".bmp"

errors = False
error_subfolder = os.path.join(src_dir, "Error")

# # If the list of files is not empty
if files:

    # For each file finishing with the filtered string
    for file_id, file in enumerate(sorted(files)):

        # Get info for the files
        folder   = os.path.dirname(file)
        basename = os.path.basename(file)
        basename = os.path.splitext(basename)[0]

        # Import the file with BioFormats
        progress_bar(file_id + 1, len(files), 2, "Processing: " + str(file_id))
        IJ.log("\\Update3:Currently opening " + basename + "...")

        try:
            imps = BFImport(str(file))
        except Exception:
            errors = True
            if not os.path.exists(error_subfolder):
                os.makedirs(error_subfolder)
            os.rename(file, os.path.join(error_subfolder, os.path.basename(file)))
            continue

        for imp in imps:
            if out_file_extension == "ImageJ-TIF":
                IJ.saveAs(imp, "Tiff", os.path.join(out_dir, basename + ".tif"))
            elif out_file_extension == "BMP":
                out_folder = os.path.join(out_dir, basename + os.path.sep)

                if not os.path.exists(out_folder):
                    os.makedirs(out_folder)

                StackWriter.save(imp, out_folder, "format=bmp")

            else:
                BFExport(imp, os.path.join(out_dir, basename + out_ext[out_file_extension]))

            imp.close()

    IJ.log("\\Update3:Script finished !")
    if errors:
        IJ.log("\\Update4:Some files failed to convert and were moved to " + error_subfolder )