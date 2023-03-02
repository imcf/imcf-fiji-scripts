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
        for f in fnmatch.filter(filenames,'*' + filteringString):
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

def get_series_count_from_ome_metadata(path_to_file):
    """Get the number of series from a file

    Parameters
    ----------
    path_to_file : str
        Path to the file

    Returns
    -------
    int
        Number of series for the file
    """
    reader = ImageReader()
    reader.setFlattenedResolutions(False)
    omeMeta = MetadataTools.createOMEXMLMetadata()
    reader.setMetadataStore(omeMeta)
    reader.setId(path_to_file)
    series_count = reader.getSeriesCount()
    reader.close()

    return series_count

def open_single_series_with_BF(path_to_file, series_number):
    """Open a single serie for a file using Bio-Formats

    Parameters
    ----------
    path_to_file : str
        Path to the file
    series_number : int
        Number of the serie to open

    Returns
    -------
    ImagePlus
        ImagePlus of the serie
    """
    options = ImporterOptions()
    options.setColorMode(ImporterOptions.COLOR_MODE_COMPOSITE)
    options.setSeriesOn(series_number, True) # python starts at 0
    # options.setSpecifyRanges(True)
    # options.setCBegin(series_number-1, channel_number-1) # python starts at 0
    # options.setCEnd(series_number-1, channel_number-1)
    # options.setCStep(series_number-1, 1)
    options.setId(path_to_file)
    imps = BF.openImagePlus(options) # is an array of imp with one entry

    return imps[0]

def save_as(imageplus, extension, out_dir, series, pad_number, split_channels):
    """Function to save an image

    Parameters
    ----------
    imageplus : ImagePlus
        ImagePlus to save
    extension : str
        Extension to use for the output
    out_dir : str
        Path for the output
    series : int
        Series to open
    pad_number : int
        Number of 0 to use for padding
    split_channels : bool
        Bool to split or not the channels
    """

    out_ext = {}
    out_ext["ImageJ-TIF"] = ".tif"
    out_ext["ICS-1"] = ".ids"
    out_ext["ICS-2"] = ".ics"
    out_ext["OME-TIFF"] = ".ome.tif"
    out_ext["CellH5"] = ".ch5"
    out_ext["BMP"] = ".bmp"

    imp_to_use = []
    dir_to_save = []

    if split_channels:
        for channel in range(1, imageplus.getNChannels() + 1):
            imp_to_use.append(
                Duplicator().run(
                    imageplus,
                    channel, channel,
                    1, imageplus.getNSlices(),
                    1, imageplus.getNFrames()
                )
            )
            dir_to_save.append(
                os.path.join(
                    out_dir,
                    "C" + str(channel)
                )
            )
    else:
        imp_to_use.append(imageplus)
        dir_to_save.append(out_dir)

    for index, current_imp in enumerate(imp_to_use):

        basename = imageplus.getShortTitle()

        out_path = os.path.join(
                dir_to_save[index],
                basename + "_series_"
                + str(series).zfill(pad_number)
            )

        if extension == "ImageJ-TIF":

            check_folder(dir_to_save[index])
            IJ.saveAs(
                current_imp,
                "Tiff",
                out_path + ".tif"
            )

        elif extension == "BMP":
            out_folder = os.path.join(out_dir, basename + os.path.sep)
            check_folder(out_folder)
            StackWriter.save(current_imp, out_folder, "format=bmp")

        else:
            BFExport(
                current_imp,
                out_path + out_ext[extension]
            )

        current_imp.close()

def check_folder(path):

    if not os.path.exists(path):
        os.makedirs(path)

# ─── MAIN CODE ──────────────────────────────────────────────────────────────────

IJ.log("\\Clear")
IJ.log("Script starting")

# Retrieve list of files
src_dir = str(src_dir)

if out_file_extension == "BMP":
    split_channels = False

temp_out_dir = os.path.join(src_dir, "out")
if out_dir is None:
    out_dir = temp_out_dir
    if not os.path.exists(temp_out_dir):
        os.makedirs(out_dir)


out_dir = str(out_dir)
files = getFileList(src_dir, filename_filter)

pad_number = 0

# # If the list of files is not empty
if files:

    # For each file finishing with the filtered string
    for file_id, file in enumerate(sorted(files)):

        # Get info for the files
        folder   = os.path.dirname(file)
        basename = os.path.basename(file)
        basename = os.path.splitext(basename)[0]

        # Import the file with BioFormats
        progress_bar(file_id + 1, len(files), 1, "Processing: " + str(file_id))
        # IJ.log("\\Update3:Currently opening " + basename + "...")

        series_count = get_series_count_from_ome_metadata(file)
        if not pad_number:
            pad_number = len(str(series_count))

        for series in range(series_count):
            progress_bar(series + 1, series_count, 2, "Opening series : ")

            imp = open_single_series_with_BF(file, series)

            if "macro image" in imp.getTitle():
                print("Skipping macro image...")
                imp.close()
                continue

            save_as(
                imp,
                out_file_extension,
                out_dir,
                series,
                pad_number,
                split_channels
            )

            imp.close()

    IJ.log("\\Update3:Script finished !")