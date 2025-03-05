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

import glob
import os
import shutil
import smtplib
import subprocess
import time
from io.scif.util import MemoryTools

# Imagej imports
from ij import IJ
from ij import WindowManager as wm
from ij.plugin import FolderOpener, HyperStackConverter
from imcflibs import pathtools
from imcflibs.imagej import misc

# ome imports to parse metadata
from loci.formats import ImageReader, MetadataTools

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


def list_dirs_containing_filetype(source, filetype):
    """Recur through the source dir and return all dirs
    and subdirs that contain the specified filetype

    Parameters
    ----------
    source : str
        Path to source dir
    filetype : str
        File extension to specify filetype

    Returns
    -------
    list
        List of all dirs that contain filetype
    """

    dirs_containing_filetype = []

    # walk recursively through all directories
    # list their paths and all files inside (=os.walk)
    for dirname, _, filenames in os.walk(source):
        # stop when encountering a directory that contains "filetype"
        # and store the directory path
        for filename in filenames:
            if filetype in filename:
                dirs_containing_filetype.append(dirname + "/")
                break

    return dirs_containing_filetype


def get_ome_metadata(source, imagenames):
    """Get the stage coordinates and calibration from the ome-xml for a given list of images

    Parameters
    ----------
    source : str
        Path to the images
    imagenames : list of str
        List of images filenames

    Returns
    -------
    tuple
        Contains
        dimensions : int
            Number of dimensions (2D or 3D)
        stage_coordinates_x : list
            The absolute stage x-coordinated from ome-xml metadata
        stage_coordinates_y : list
            The absolute stage y-coordinated from ome-xml metadata
        stage_coordinates_z : list
            The absolute stage z-coordinated from ome-xml metadata
        relative_coordinates_x : list
            The relative stage x-coordinates in px
        relative_coordinates_y : list
            The relative stage y-coordinates in px
        relative_coordinates_z : list
            The relative stage z-coordinates in px
        image_calibration : list
            x,y,z image calibration in unit/px
        calibration_unit : str
            Image calibration unit
        image_dimensions_czt : list
            Number of images in dimensions c,z,t
        series_names : list of str
            Names of all series contained in the files
        max_size : list of int
            Maximum size across all files in dimensions x,y,z
    """

    # open an array to store the abosolute stage coordinates from metadata
    stage_coordinates_x = []
    stage_coordinates_y = []
    stage_coordinates_z = []
    series_names = []

    for counter, image in enumerate(imagenames):
        # parse metadata
        reader = ImageReader()
        reader.setFlattenedResolutions(False)
        omeMeta = MetadataTools.createOMEXMLMetadata()
        reader.setMetadataStore(omeMeta)
        reader.setId(source + str(image))
        series_count = reader.getSeriesCount()

        # get hyperstack dimensions from the first image
        if counter == 0:
            frame_size_x = reader.getSizeX()
            frame_size_y = reader.getSizeY()
            frame_size_z = reader.getSizeZ()
            frame_size_c = reader.getSizeC()
            frame_size_t = reader.getSizeT()

            # note the dimensions
            if frame_size_z == 1:
                dimensions = 2
            if frame_size_z > 1:
                dimensions = 3

            # get the physical calibration for the first image series
            physSizeX = omeMeta.getPixelsPhysicalSizeX(0)
            physSizeY = omeMeta.getPixelsPhysicalSizeY(0)
            physSizeZ = omeMeta.getPixelsPhysicalSizeZ(0)

            # workaround to get the z-interval if physSizeZ.value() returns None.
            z_interval = 1
            if physSizeZ is not None:
                z_interval = physSizeZ.value()

            if frame_size_z > 1 and physSizeZ is None:
                print("no z calibration found, trying to recover")
                first_plane = omeMeta.getPlanePositionZ(0, 0)
                next_plane_imagenumber = frame_size_c + frame_size_t - 1
                second_plane = omeMeta.getPlanePositionZ(0, next_plane_imagenumber)
                z_interval = abs(abs(first_plane.value()) - abs(second_plane.value()))
                print("z-interval seems to be: " + str(z_interval))

            # create an image calibration
            image_calibration = [physSizeX.value(), physSizeY.value(), z_interval]
            calibration_unit = physSizeX.unit().getSymbol()
            image_dimensions_czt = [frame_size_c, frame_size_z, frame_size_t]

        reader.close()

        for series in range(series_count):
            if omeMeta.getImageName(series) == "macro image":
                continue

            if series_count > 1 and not str(image).endswith(".vsi"):
                series_names.append(omeMeta.getImageName(series))
            else:
                series_names.append(str(image))
            # get the plane position in calibrated units
            current_position_x = omeMeta.getPlanePositionX(series, 0)
            current_position_y = omeMeta.getPlanePositionY(series, 0)
            current_position_z = omeMeta.getPlanePositionZ(series, 0)

            physSizeX_max = (
                physSizeX.value()
                if physSizeX.value() >= omeMeta.getPixelsPhysicalSizeX(series).value()
                else omeMeta.getPixelsPhysicalSizeX(series).value()
            )
            physSizeY_max = (
                physSizeY.value()
                if physSizeY.value() >= omeMeta.getPixelsPhysicalSizeY(series).value()
                else omeMeta.getPixelsPhysicalSizeY(series).value()
            )
            if omeMeta.getPixelsPhysicalSizeZ(series):
                physSizeZ_max = (
                    physSizeZ.value()
                    if physSizeZ.value()
                    >= omeMeta.getPixelsPhysicalSizeZ(series).value()
                    else omeMeta.getPixelsPhysicalSizeZ(series).value()
                )

            else:
                physSizeZ_max = 1.0

            # get the absolute stage positions and store them
            pos_x = current_position_x.value()
            pos_y = current_position_y.value()

            if current_position_z is None:
                print("the z-position is missing in the ome-xml metadata.")
                pos_z = 1.0
            else:
                pos_z = current_position_z.value()

            stage_coordinates_x.append(pos_x)
            stage_coordinates_y.append(pos_y)
            stage_coordinates_z.append(pos_z)

    max_size = [physSizeX_max, physSizeY_max, physSizeZ_max]

    # calculate the store the relative stage movements in px (for the grid/collection stitcher)
    relative_coordinates_x_px = []
    relative_coordinates_y_px = []
    relative_coordinates_z_px = []

    for i in range(len(stage_coordinates_x)):
        rel_pos_x = (
            stage_coordinates_x[i] - stage_coordinates_x[0]
        ) / physSizeX.value()
        rel_pos_y = (
            stage_coordinates_y[i] - stage_coordinates_y[0]
        ) / physSizeY.value()
        rel_pos_z = (stage_coordinates_z[i] - stage_coordinates_z[0]) / z_interval

        relative_coordinates_x_px.append(rel_pos_x)
        relative_coordinates_y_px.append(rel_pos_y)
        relative_coordinates_z_px.append(rel_pos_z)

    return (
        dimensions,
        stage_coordinates_x,
        stage_coordinates_y,
        stage_coordinates_z,
        relative_coordinates_x_px,
        relative_coordinates_y_px,
        relative_coordinates_z_px,
        image_calibration,
        calibration_unit,
        image_dimensions_czt,
        series_names,
        max_size,
    )


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

    final_line = [";".join(i) for i in zip(imagenames, empty_column, coordinates_xyz)]

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


def save_current_image_as_tiff(filename, filetype, target):
    """Save the currently active image as ImageJ-Tiff

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
    savename = filename.replace(filetype, "_stitched.tif")
    savepath = target + savename
    IJ.log("now saving: " + str(savepath))
    print("now saving " + savepath)
    IJ.saveAs(imp, "Tiff", savepath)
    imp.close()

    return savepath


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


def save_current_image_as_ics1(filename, filetype, target):
    """Save the currently active image as ICS/IDS using scifio

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

    img = ImageDisplayService.getActiveDataset()
    savename = filename.replace(filetype, "_stitched.ics")
    savepath = target + savename
    IJ.log("now saving: " + str(savepath))
    print("now saving " + savepath)
    io.save(img, savepath)
    IJ.run("Close")

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
    """Use Bio-formats to open all sequential images written by the Grid/collection stitcher
    in a folder as virtual stack

    Parameters
    ----------
    source : str
        Directory to the image files
    image_dimensions_czt : list
        Number of images in dimensions c,z,t
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
    """Use IJ "import image sequence" to open all sequential images written by the Grid/collection stitcher
    in a folder as virtual stack. Bio-Formats seems to have a limit in XY size.

    Parameters
    ----------
    source : str
        Directory to the image files
    image_dimensions_czt : list
        Number of images in dimensions c,z,t
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


def get_folder_size(source):
    """Determines the size of a given directory and its subdirectories in bytes

    Parameters
    ----------
    source : str
        Directory which size should be determined

    Returns
    -------
    int
        Size of the source folder in bytes
    """

    total_size = 0
    for dirpath, _, filenames in os.walk(source):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size


def locate_latest_imaris(paths_to_check=None):
    """Find paths to latest installed Imaris or ImarisFileConverter version.

    Parameters
    ----------
    paths_to_check: list of str, optional
        A list of paths that should be used to look for the installations, by default
        `None` which will fall back to the standard installation locations of Bitplane.

    Returns
    -------
    str
        Full path to the most recent (as in "version number") ImarisFileConverter
        or Imaris installation folder with the latter one having priority.
        Will be empty if nothing is found.
    """

    if not paths_to_check:
        paths_to_check = [
            r"C:\Program Files\Bitplane\ImarisFileConverter ",
            r"C:\Program Files\Bitplane\Imaris ",
        ]

    imaris_paths = [""]

    for check in paths_to_check:
        hits = glob.glob(check + "*")
        imaris_paths += sorted(
            hits, key=lambda x: float(x.replace(check, "").replace(".", ""))
        )

    return imaris_paths[-1]


def convert_to_imaris2(convert_to_ims, path_to_image):
    """Convert a given file to Imaris5 .ims using ImarisConvert.exe directly with subprocess

    Parameters
    ----------
    convert_to_ims : Boolean
        True if the users chose file conversion
    path_to_image : str
        the full path to the input image
    """

    if convert_to_ims == True:
        path_root, file_extension = os.path.splitext(path_to_image)
        if file_extension == ".ids":
            file_extension = ".ics"
            path_to_image = path_root + file_extension

        os.chdir(locate_latest_imaris())

        command = 'ImarisConvert.exe  -i "%s" -of Imaris5 -o "%s"' % (
            path_to_image,
            path_to_image.replace(file_extension, ".ims"),
        )
        print("\n%s" % command)
        IJ.log("Converting to Imaris5 .ims...")
        subprocess.call(command, shell=True)
        IJ.log("Conversion to .ims is finished")


def send_mail(sender, recipient, filename, total_execution_time_min):
    """Send an email via smtp.unibas.ch.
    Will likely NOT work without connection to the unibas network.

    Parameters
    ----------
    sender : string
        senders email address
    recipient : string
        recipients email address
    filename : string
        the name of the file to be passed in the email
    total_execution_time_min : float
        the time it took to process the file
    """

    header = "From: imcf@unibas.ch\n"
    header += "To: %s\n"
    header += "Subject: Your stitching job finished successfully\n\n"
    text = (
        "Dear recipient,\n\n"
        "This is an automated message from the recursive stitching tool.\n"
        "Your folder %s has been successfully processed (%s min).\n\n"
        "Kind regards,\n"
        "The IMCF-team"
    )

    message = header + text

    try:
        smtpObj = smtplib.SMTP("smtp.unibas.ch")
        smtpObj.sendmail(
            sender, recipient, message % (recipient, filename, total_execution_time_min)
        )
        print("Successfully sent email")
    except smtplib.SMTPException:
        print("Error: unable to send email")


# ─── Main Code ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # start the process
    execution_start_time = time.time()

    if not filetype.startswith("."):
        filetype = "." + filetype

    # In case script is ran batch
    if os.path.isfile(source.getAbsolutePath()):
        source = os.path.dirname(source.getAbsolutePath())
    source = fix_ij_dirs(source)
    all_source_dirs = list_dirs_containing_filetype(source, filetype)

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
        folder_size_bytes = get_folder_size(source_dir)
        if free_memory_bytes / folder_size_bytes < 3.5:
            bigdata = True
            IJ.log("Not enough free RAM, switching to BigData mode (slow)")

        allimages = pathtools.listdir_matching(source_dir, filetype, sort=True)

        ome_metadata = get_ome_metadata(source_dir, allimages)

        # if filetype == "ome.tif":
        #     write_tileconfig(source_dir, ome_metadata[0], allimages, ome_metadata[1], ome_metadata[2], ome_metadata[3])
        # else:
        write_tileconfig(
            source_dir,
            ome_metadata[0],
            ome_metadata[10],
            ome_metadata[4],
            ome_metadata[5],
            ome_metadata[6],
        )

        run_GC_stitcher(source_dir, fusion_method, bigdata, quick, reg_threshold)

        if bigdata and not only_register:
            path = pathtools.join2(source_dir, "temp")
            open_sequential_gcimages_from_folder(path, ome_metadata[9])
            calibrate_current_image(ome_metadata[7], ome_metadata[8])
            path_to_image = save_current_image_as_bdv(
                allimages[0], filetype, source_dir
            )
            convert_to_imaris2(convert_to_ims, path_to_image)
            shutil.rmtree(path, ignore_errors=True)  # remove temp folder

        if bigdata and bdv and not only_register:
            calibrate_current_image(ome_metadata[7], ome_metadata[8])
            path_to_image = save_current_image_as_bdv(
                allimages[0], filetype, source_dir
            )
            convert_to_imaris2(convert_to_ims, path_to_image)

        if not bigdata and not bdv and not only_register:
            calibrate_current_image(ome_metadata[7], ome_metadata[8])
            path_to_image = save_current_image_with_BF_as_ics1(
                allimages[0], filetype, source_dir
            )
            convert_to_imaris2(convert_to_ims, path_to_image)

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

    if email_address != "":
        send_mail("imcf@unibas.ch", email_address, source, total_execution_time_min)
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
