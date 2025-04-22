# @File(label="source directory", style="directory") source
# @String(label="file type") filetype
# @Boolean(label="quick stitch by stage coordinates", value="False") quick
# @Boolean(label="save as BigDataViewer hdf5 instead", value="False") bdv
# @Double(label="Regression threshold", value=0.25) reg_threshold
# @Boolean(label="conserve RAM but be slower", description="tick this if your previous attempt failed with <Out of memory> error", value="False") bigdata
# @Boolean (label="convert stitched & fused image to Imaris5", description="convert the fused image to *.ims", value=True) convert_to_ims
# @String (label="Send info email to: ", description="empty = skip", required="False") email_address
# @Boolean(label="Only output TileConfiguration.registered txt file ?", value=False) only_register
# @DatasetIOService io
# @ImageDisplayService ImageDisplayService


# pylint: disable-msg=line-too-long
# pylint: disable-msg=import-error

# ─── Imports ──────────────────────────────────────────────────────────────────

import os
import shutil
import time
from io.scif.util import MemoryTools

# Imagej imports
from ij import IJ
from ij import WindowManager as wm
from ij.plugin import FolderOpener, HyperStackConverter
from imcflibs import pathtools
from imcflibs.imagej import bioformats as bf
from imcflibs.imagej import misc

# requirements:
# BigStitcher
# faim-imagej-imaris-tools-0.0.1.jar (https://maven.scijava.org/service/local/repositories/releases/content/org/scijava/faim-imagej-imaris-tools/0.0.1/faim-imagej-imaris-tools-0.0.1.jar)

# ─── Functions ────────────────────────────────────────────────────────────────


def fix_ij_dirs(path):
    """Use forward slashes in directory paths

    Parameters
    ----------
    path : string
        a directory path obtained from dialogue or script parameter

    Returns
    -------
    string
        a more robust path with forward slashes as separators
    """

    fixed_path = str(path).replace("\\", "/")
    fixed_path = fixed_path + "/"

    return fixed_path


def write_tileconfig(
    source, dimensions, imagenames, x_coordinates, y_coordinates, z_coordinates
):
    """Write a TileConfiguration.txt for the Grid/collection stitcher

    Parameters
    ----------
    source : str
        Directory in which the TileConfiguration.txt will be written
    dimensions : int
        Number of dimensions (2D or 3D)
    imagenames : list
        List of images filenames
    x_coordinates : list
        The relative stage x-coordinates in px
    y_coordinates : list
        The relative stage y-coordinates in px
    z_coordinates : list
        The relative stage z-coordinates in px
    """

    image_filenames = [os.path.basename(i) for i in imagenames]

    outCSV = str(source) + "TileConfiguration.txt"

    row_1 = "# Define the number of dimensions we are working on"
    row_2 = "dim = " + str(dimensions)
    row_3 = " "
    row_4 = "# Define the image coordinate"

    a = x_coordinates
    b = y_coordinates
    c = z_coordinates

    if dimensions == 2:
        coordinates_xyz = [" (" + str(m) + "," + str(n) + ")" for m, n in zip(a, b)]

    if dimensions == 3:
        coordinates_xyz = [
            " (" + str(m) + "," + str(n) + "," + str(o) + ")"
            for m, n, o in zip(a, b, c)
        ]

    empty_column = list(str(" ") * len(imagenames))

    final_line = [";".join(i) for i in zip(image_filenames, empty_column, coordinates_xyz)]

    with open(outCSV, "wb") as f:
        f.write(row_1 + "\n")
        f.write(row_2 + "\n")
        f.write(row_3 + "\n")
        f.write(row_4 + "\n")
        f.write("\n".join(final_line))
    f.close()


def run_GC_stitcher(source, fusion_method, bigdata, quick, reg_threshold):
    """Run the Grid/Collection stitching using a TileConfiguration.txt

    Parameters
    ----------
    source : str
        Directory to the TileConfiguration.txt and the imagefiles
    fusion_method : str
        Fusion method to use
    """

    if bigdata is True:
        temp = source + "temp"
        if not os.path.exists(temp):
            os.mkdir(temp)
        mode = (
            "use_virtual_input_images "
            + "computation_parameters=[Save computation time (but use more RAM)] "
            + "image_output=[Write to disk] output_directory=["
            + temp
            + "]"
        )
    else:
        mode = (
            "computation_parameters=[Save computation time (but use more RAM)] "
            + "image_output=[Fuse and display]"
        )

    params = (
        "type=[Positions from file] order=[Defined by TileConfiguration] "
        + "directory=["
        + source
        + "] "
        + "layout_file=TileConfiguration.txt"
        + " fusion_method=["
        + fusion_method
        + "] "
        + "regression_threshold="
        + str(reg_threshold)
        + " "
        + "max/avg_displacement_threshold=2.50 "
        + "absolute_displacement_threshold=3.50 "
        + ("" if quick else "compute_overlap subpixel_accuracy ")
        + str(mode),
    )

    print(params)

    IJ.run("Grid/Collection stitching", str(params))


def calibrate_current_image(xyz_calibration, unit):
    """Calibrate the currently active image

    Parameters
    ----------
    xyz_calibration : list
        x,y,z image calibration in unit/px
    unit : str
        Image calibration unit
    """

    imp = wm.getCurrentImage()
    imp.getCalibration().pixelWidth = xyz_calibration[0]
    imp.getCalibration().pixelHeight = xyz_calibration[1]
    imp.getCalibration().pixelDepth = xyz_calibration[2]
    imp.getCalibration().setUnit(unit)


def save_current_image_as_bdv(filename, filetype, target):
    """Save the currently active image as BigDataViewer hdf5/xml

    Parameters
    ----------
    filename : str
        Filename of the image
    filetype : str
        The original filetype of the image
    target : str
        Directory where the image will be saved

    Returns
    -------
    str
        Path to save the data
    """

    imp = wm.getCurrentImage()
    savename = filename.replace(filetype, "_stitched.xml")
    savepath = target + savename
    IJ.log("now saving: " + str(savepath))
    print("now saving " + savepath)
    IJ.run(
        "Export Current Image as XML/HDF5",
        "  use_deflate_compression export_path=[" + savepath + "]",
    )
    imp.close()

    return savepath


def save_current_image_with_BF_as_ics1(filename, filetype, target):
    """Save the currently active image as ICS1 using BF

    Parameters
    ----------
    filename : str
        Filename of the image
    filetype : str
        The original filetype of the image
    target : str
        Directory where the image will be saved

    Returns
    -------
    str
        Path to save the data
    """

    imp = wm.getCurrentImage()
    savename = filename.replace(filetype, "_stitched.ids")
    savepath = os.path.join(target, savename)
    IJ.log("now saving: " + str(savepath))
    print("now saving " + savepath)
    IJ.run(imp, "Bio-Formats Exporter", "save=[" + savepath + "]")
    imp.close()

    return savepath


def open_sequential_gcimages_withBF(source, image_dimensions_czt):
    """Open sequential grid/collection stitcher images as a virtual stack.

    This function imports a sequence of images created by the Grid/Collection
    stitcher plugin that follow the naming convention "img_t{t}_z{z}_c{c}".
    It determines the range of indices for each dimension (channel, z-stack,
    time) and creates a virtual stack that spans all images in the specified
    directory.

    Parameters
    ----------
    source : str
        Directory path containing the image files following the Grid/Collection
        stitcher naming format
    image_dimensions_czt : list of int
        Number of images in each dimension [channels, z-planes, timepoints]
        Example: [3, 10, 1] for a 3-channel z-stack with a single timepoint

    Notes
    -----
    - The function creates a virtual stack, which means images are loaded
      on-demand to reduce memory usage
    - It uses the Bio-Formats Importer plugin with specific parameters to
      properly handle multi-dimensional data
    - Image indices start at 1, not 0
    """

    c_end = str(image_dimensions_czt[0])
    c_start = "0" * (len(c_end) - 1) + "1"

    z_end = str(image_dimensions_czt[1])
    z_start = "0" * (len(z_end) - 1) + "1"

    t_end = str(image_dimensions_czt[2])
    t_start = "0" * (len(t_end) - 1) + "1"

    first_image_path = source + "/img_t" + t_start + "_z" + z_start + "_c" + c_start
    IJ.run(
        "Bio-Formats Importer",
        "open=["
        + first_image_path
        + "] color_mode=Default concatenate_series open_all_series "
        + "rois_import=[ROI manager] view=Hyperstack "
        + "stack_order=XYCZT use_virtual_stack "
        + "name="
        + source
        + "/img_t<"
        + t_start
        + "-"
        + t_end
        + ">_z<"
        + z_start
        + "-"
        + z_end
        + ">_c<"
        + c_start
        + "-"
        + c_end
        + ">",
    )


def open_sequential_gcimages_from_folder(source, image_dimensions_czt):
    """Open sequential images produced by Grid/Collection stitcher.

    This function uses ImageJ's FolderOpener to open all sequential images from a
    directory as a virtual stack. The function is specifically designed for images
    generated by the Grid/Collection stitcher. It automatically calculates
    Z-dimensions based on the total number of images and the provided C and T
    dimensions, then converts the stack to a proper hyperstack that is displayed
    to the user.

    Bio-Formats sometimes has limitations with very large XY dimensions, making this
    approach necessary for large stitched datasets.

    Parameters
    ----------
    source : str
        Directory path containing the sequential image files
    image_dimensions_czt : list of int
        Number of images in dimensions [c,z,t] where:
        - c: number of channels
        - z: number of z-slices (may be overridden based on actual files)
        - t: number of timepoints

    Returns
    -------
    None
        The function displays the hyperstack but does not return it

    Notes
    -----
    Z-dimension is automatically recalculated based on the total number of images
    found and the provided C and T dimensions, as the Grid/Collection stitcher may
    add Z-planes during processing.
    """

    c_end = image_dimensions_czt[0]
    t_end = image_dimensions_czt[2]

    imp = FolderOpener.open(str(source), "virtual")
    total_images_in_stack = imp.getNSlices()
    z_total = (
        total_images_in_stack / (c_end * t_end)
    )  # needs to be inferred rather than taken from raw image metadata as the G/C-stitcher might have added z-planes
    imp2 = HyperStackConverter.toHyperStack(
        imp, c_end, z_total, t_end, "default", "Color"
    )  # xyczt (default), stays virtual
    imp2.show()


# ─── Main Code ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # start the process
    execution_start_time = time.time()

    if not filetype.startswith("."):
        filetype = "." + filetype

    # In case script is ran batch
    source_info = pathtools.parse_path(source)
    source = source_info["path"]
    # source = fix_ij_dirs(source)
    all_source_dirs = pathtools.find_dirs_containing_filetype(source, filetype)

    if only_register:
        fusion_method = "Do not fuse images (only write TileConfiguration)"
        IJ.log(
            "The output will only be the txt file containing registered positions for the tiles."
        )
        IJ.log("As such, no HDF5 resaving or Imaris conversion will be happening.")
    else:
        fusion_method = "Linear Blending"

    for source_dir in all_source_dirs:
        IJ.log("Now working on " + source_dir)
        print("bigdata= ", str(bigdata))
        free_memory_bytes = MemoryTools().totalAvailableMemory()
        folder_size_bytes = pathtools.folder_size(source_dir)
        if free_memory_bytes / folder_size_bytes < 3.5:
            bigdata = True
            IJ.log("Not enough free RAM, switching to BigData mode (slow)")

        allimages = pathtools.listdir_matching(
            source_dir, filetype, fullpath=True, sort=True
        )

        ome_stage_metadata = bf.get_stage_coords(allimages)

        # if filetype == "ome.tif":
        #     write_tileconfig(source_dir, ome_metadata[0], allimages, ome_metadata[1], ome_metadata[2], ome_metadata[3])
        # else:
        write_tileconfig(
            source_dir,
            ome_stage_metadata.dimensions,
            ome_stage_metadata.series_names,
            ome_stage_metadata.relative_coordinates_x,
            ome_stage_metadata.relative_coordinates_y,
            ome_stage_metadata.relative_coordinates_z,
        )

        run_GC_stitcher(source_dir, fusion_method, bigdata, quick, reg_threshold)

        calibrate_current_image(
            ome_stage_metadata.image_calibration,
            ome_stage_metadata.calibration_unit,
        )

        if bigdata and not only_register:
            if not bdv:
                path = pathtools.join2(source_dir, "temp")
                open_sequential_gcimages_from_folder(
                    path, ome_stage_metadata.image_dimensions_czt
                )
                calibrate_current_image(
                    ome_stage_metadata.image_calibration,
                    ome_stage_metadata.calibration_unit,
                )
                path_to_image = save_current_image_as_bdv(
                    allimages[0], filetype, source_dir
                )
                misc.convert_to_imaris(convert_to_ims, path_to_image)
                shutil.rmtree(path, ignore_errors=True)  # remove temp folder
            else:
                path_to_image = save_current_image_as_bdv(
                    allimages[0], filetype, source_dir
                )
                misc.convert_to_imaris(convert_to_ims, path_to_image)

        if not bigdata and not bdv and not only_register:
            path_to_image = save_current_image_with_BF_as_ics1(
                allimages[0], filetype, source_dir
            )

        if convert_to_ims:
            misc.run_imarisconvert(path_to_image)

        # run the garbage collector to clear the memory
        # Seems to not work in a function and needs to be started several times with waits in between :(
        IJ.log("collecting garbage...")
        IJ.run("Collect Garbage", "")
        time.sleep(60.0)
        IJ.run("Collect Garbage", "")
        time.sleep(60.0)
        IJ.run("Collect Garbage", "")
        time.sleep(60.0)

    total_execution_time_min = misc.elapsed_time_since(execution_start_time)

    if email_address:
        misc.send_notification_email(
            "Stitching script", email_address, source, total_execution_time_min
        )
    else:
        print("Email address field is empty, no email was sent")

    # update the log
    IJ.log("##### summary #####")
    IJ.log("number of folders stitched: " + str(len(all_source_dirs)))
    IJ.log("quick stitch by stage coordinates: " + str(quick))
    IJ.log("save as BigDataViewer hdf5 instead: " + str(bdv))
    IJ.log("conserve RAM= " + str(bigdata))
    IJ.log("total time in [HH:MM:SS:ss]: " + str(total_execution_time_min))
    IJ.log("All done")
    IJ.selectWindow("Log")
    IJ.saveAs("Text", os.path.join(source, "stitch_log"))
