# @ String(label="Username", description="please enter your username") USERNAME
# @ String(label="Password", description="please enter your password", style="password") PASSWORD
# @ String(label="Info about file", description="Link got from OMERO, or image IDs separated by commas. If left empty, will use the file open in Fiji") OMERO_link
# @ Integer(label="Reference channel for shift calculation", value=1) ref_chnl
# @ File(label="Temp path for storage", style="directory", description="Script need to store temp image") destination
# @ Boolean(label="Delete previous kv pairs", value=False) delete_previous_kv
# @ RoiManager rm

# ─── IMPORTS ────────────────────────────────────────────────────────────────────

import math
import os
import re
import sys
from datetime import date

from collections import OrderedDict

from ij import IJ
from ij import WindowManager as wm
from ij.gui import Line, Overlay, Plot, Roi, TextRoi, WaitForUserDialog
from ij.measure import CurveFitter
from ij.plugin import (
    Concatenator,
    Duplicator,
    ImageCalculator,
    ImagesToStack,
    ZProjector,
)
from ij.plugin.frame import RoiManager
from imcflibs.imagej import bioformats as bf
from imcflibs.imagej import misc, omerotools
from java.awt import Color, Font

# java imports
from java.lang import Double, Long, String
from java.util import ArrayList
from omero.gateway.model import ImageData
from omero.model import NamedValue

# ─── FUNCTIONS ──────────────────────────────────────────────────────────────────


def coord_brightest_point(input_imp, selected_roi, best_slice):
    """Get the brightest spot coordinates in an image

    Parameters
    ----------
    input_imp : ij.ImagePlus
        Image for which to find the brightest spot
    selected_roi : ij.gui.ROI
        ROI where to find the brightest spot
    best_slice : int
        Number of the slice considered to be the best

    Returns
    -------
    dict of {int, int}
        Dictionary with the X and Y coordinates of the brightest spot
    """

    # temp_roi = Roi(round(x_loc - x_range/2), round(y_loc - y_range/2), x_range, y_range)
    input_imp.setRoi(selected_roi)
    input_imp_dup = Duplicator().run(input_imp, 1, 1, best_slice, best_slice, 1, 1)
    input_imp_dup.setCalibration(input_imp.getCalibration())
    # IJ.run(input_imp_dup, "32-bit", "stack")
    # imp_proj_avg = ZProjector.run(input_imp_dup,"avg",1,100)

    # imp_proj_avg_16bit = Duplicator().run(imp_proj_avg)
    # IJ.run(imp_proj_avg_16bit, "16-bit", "stack")
    temp_stats = input_imp_dup.getStatistics()
    IJ.run(input_imp_dup, "Subtract...", "value=" + str(round(temp_stats.max - 1)))
    IJ.run(input_imp_dup, "Find Maxima...", "prominence=1 output=[Point Selection]")
    # imp_proj_avg_16bit.show()
    max_roi = input_imp_dup.getRoi()

    bright_spots = {
        "X_coord": int(max_roi.getXBase() + selected_roi.getXBase()),
        "Y_coord": int(max_roi.getYBase() + selected_roi.getYBase()),
    }

    input_imp_dup.close()

    return bright_spots


def scan_for_best_slice(input_imp, selected_roi):
    """Find the slice and value of spot through stack

    Parameters
    ----------
    input_imp : ij.ImagePlus
        ImagePlus on which to do measurements
    selected_roi : ij.gui.Roi
        ROI where to look for the best slice

    Returns
    -------
    dict of {int, int, int}
        Different stats for the stack
    """

    best_slice = 0
    max_stack = 0
    min_stack = 65500
    # max_int    = 0

    input_imp.setRoi(selected_roi)
    input_imp_dup = Duplicator().run(input_imp, 1, 1, 1, input_imp.getNSlices(), 1, 1)
    input_imp_dup.setCalibration(input_imp.getCalibration())

    for slice in range(1, input_imp_dup.getNSlices() + 1):
        input_imp_dup.setSlice(slice)
        slice_stats = input_imp_dup.getStatistics()
        # pixel_value = input_imp.getPixel(bright_spot['X_coord'], bright_spot['Y_coord'])[0]
        if slice_stats.max > max_stack:
            # max_int    = pixel_value
            max_stack = slice_stats.max
            min_stack = slice_stats.min
            best_slice = slice

    stack_stats = {
        "max_stack": max_stack,
        "min_stack": min_stack,
        "best_slice": best_slice,
    }

    input_imp_dup.close()
    return stack_stats


def duplicate_imp_and_calibrate(
    imp, specific_chnl=None, specific_z=None, specific_t=None, roi=None
):
    """Duplicate an ImagePlus and set the calibration

    Parameters
    ----------
    imp : ij.ImagePlus
        ImagePlus to duplicate
    specific_chnl : int, optional
        Channel to duplicate if specific, otherwise take all, by default None
    specific_z : int, optional
        Z slice to duplicate if specific, otherwise take all, by default None
    specific_t : int, optional
        T frame to duplicate if specific, otherwise take all, by default None
    roi : ROI, optional
        ROI to use to duplicate, will crop the image, by default None

    Returns
    -------
    ij.ImagePlus
        Duplicated and calibrated ImagePlus
    """

    if roi:
        imp.setRoi(roi)

    if not specific_chnl:
        start_chnl = 1
        stop_chnl = imp.getNChannels()
    else:
        start_chnl = specific_chnl
        stop_chnl = specific_chnl

    if not specific_z:
        start_z = 1
        stop_z = imp.getNSlices()
    else:
        start_z = specific_z
        stop_z = specific_z

    if not specific_t:
        start_t = 1
        stop_t = imp.getNFrames()
    else:
        start_t = specific_t
        stop_t = specific_t

    imp_dup = Duplicator().run(
        imp, start_chnl, stop_chnl, start_z, stop_z, start_t, start_z
    )
    imp_dup.setCalibration(imp.getCalibration())
    return imp_dup


def reslice_based_on_roi(
    imp, ROI_size, line_start, bg_ROI=None, slice_number=None, do_y=False
):
    """Reslice an ImagePlus based on a ROI

    Parameters
    ----------
    imp : ij.ImagePlus
        ImagePlus to reslice
    ROI_size : int
        Pixel size of the ROI to draw the line
    line_start : int
        Coordinate for the line position
    bg_ROI : ij.gui.Roi
        ROI to use for background subtraction
    slice_number : int, optional
        Slice to use for the reslice, by default None
    do_y : bool, optional
        Bool to know if reslice should be X or Y, by default False

    Returns
    -------
    ij.ImagePlus
        Resliced ImagePlus
    """

    if slice_number:
        imp.setSlice(slice_number)

    if do_y:
        line_size = ROI_size if ROI_size <= imp.getHeight() else imp.getHeight()
        line_roi = Line(line_start, 0, line_start, line_size)
    else:
        line_size = ROI_size if ROI_size <= imp.getWidth() else imp.getWidth()
        line_roi = Line(0, line_start, line_size, line_start)
    imp.setRoi(line_roi)
    output = (
        str(imp.getCalibration().pixelDepth)
        + " slice_count=1"
        + (" rotate" if do_y else "")
    )
    IJ.run(
        imp,
        "Reslice [/]...",
        "output=" + output,
    )
    imp_proj = IJ.getImage()
    if do_y:
        imp_proj.setTitle("Y_Proj")
    else:
        imp_proj.setTitle("X_Proj")

    if bg_ROI:
        bg_subtraction(imp_proj, None, bg_ROI, "min")

    return imp_proj


def set_roi_color_and_position(
    roi, color, position_channel=1, position_slice=1, position_frame=1
):
    """Set the stroke color and position of a ROI

    Parameters
    ----------
    roi : ij.gui.Roi
        ROI to change
    color : java.awt.Color
        Color to use for the ROI
    position_channel : int, optional
        Channel to set the ROI on, by default 1
    position_slice : int, optional
        Slice to set the ROI on, by default 1
    position_frame : int, optional
        Frame to set the ROI on, by default 1
    """
    roi.setStrokeColor(color)
    roi.setPosition(position_channel, position_slice, position_frame)


def extract(list, index):
    """Extract all elements at position index from sublists

    Parameters
    ----------
    list : list of list
        List containing multiple list
    index : int
        Index to extract from all sublists

    Returns
    -------
    list
        List of all elements at correct position
    """
    return [item[index] for item in list]


def bg_subtraction(imp, slice_number=None, roi=None, stat_to_use="mean"):
    """Subtract the background from an image based on stats

    Parameters
    ----------
    imp : ij.ImagePlus
        ImagePlus on which to do the subtraction
    slice_number : int, optional
        Slice to use for the measurement, by default None
    roi : ij.gui.Roi, optional
        ROI to use for the measurement, by default None
    stat_to_use : str, optional
        Stat to use for the background calculation, by default "mean"
    """
    if slice_number:
        imp.setSlice(slice_number)
    if roi:
        imp.setRoi(roi)
    bg_stats = imp.getStatistics()
    IJ.run(imp, "Select None", "")
    # imp.show()

    IJ.run(
        imp,
        "Subtract...",
        "value=" + str(getattr(bg_stats, stat_to_use)) + " stack",
    )


def change_canvas_size(imp, width, height, position, do_zero=True, resize=False):
    """Change the canvas of an image

    Parameters
    ----------
    imp : ij.ImagePlus
        ImagePlus on which to change the canvas
    width : int
        New width for the canvas, in pixel
    height : int
        New height for the canvas, in pixel
    position : str
        Position to put the original image in the new canvas

    Returns
    -------
    ij.ImagePlus
        ImagePlus with modified canvas size
    """

    if resize:
        imp2 = rescale_image(imp, width, height)
    else:
        imp2 = imp

    imp2.setTitle(imp.getTitle())
    imp.changes = False
    imp.close()

    options = (
        "width="
        + str(width)
        + " "
        + "height="
        + str(height)
        + " "
        + "position="
        + position
        + (" zero" if do_zero else "")
    )

    IJ.run(imp2, "Canvas Size...", options)
    return imp2


def rescale_image(imp, width, height):
    """Rescale an image

    Parameters
    ----------
    imp : ij.ImagePlus
        ImagePlus on which to change the canvas
    width : int
        New width for the canvas, in pixel
    height : int
        New height for the canvas, in pixel

    Returns
    -------
    ij.ImagePlus
        ImagePlus with new scale
    """

    imp2 = imp.resize(int(width / 2), int(height / 2), "bilinear")

    imp2.setTitle(imp.getTitle())

    return imp2


# ─── VARIABLES ──────────────────────────────────────────────────────────────────

# OMERO server info
HOST = "omero.biozentrum.unibas.ch"
PORT = 4064
# datasetId = datasetid
groupId = "-1"

x_range = 12
y_range = 12
z_range = 12

line_thickness = 1

roi_size_cal = 15000
final_size = 550
half_final_size = final_size / 2

# ─── CODE ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    IJ.log("\\Clear")
    IJ.log("Script started")

    today = date.today()
    destination = str(destination)
    rm.reset()

    try:
        user_client = omerotools.connect(HOST, PORT, USERNAME, PASSWORD)

        image_wrappers = omerotools.parse_url(user_client, OMERO_link)
        image_wrappers.sort()
        # else:
        #     image_ids_array = []
        #     image_ids_array.append(wm.getCurrentImage())

        omero_avg_table = []
        omero_avg_columns = OrderedDict()

        # imps = BFImport(file_to_open)
        for image_index, image_wpr in enumerate(image_wrappers):
            kv_dict = ArrayList()
            kv_dict.clear()

            average_values = []

            misc.progressbar(image_index + 1, len(image_wrappers), 2, "Processing : ")

            rm = RoiManager.getInstance()
            rm.reset()

            # image_wpr = image_wrapper.toImagePlus()
            dataset_wpr = image_wpr.getDatasets(user_client)[0]
            dataset_id = dataset_wpr.getId()
            dataset_name = dataset_wpr.getName()
            project_name = dataset_wpr.getProjects(user_client)[0].getName()

            acq_metadata_dict = omerotools.get_acquisition_metadata(
                user_client, image_wpr
            )

            IJ.log("\\Update5:Fetching image from OMERO...")
            imp = image_wpr.toImagePlus(user_client)

            # Set calibration in nm
            average_values.extend([imp.getTitle()])
            cal = imp.getCalibration()
            unit_list = ["uM", "micron", "microns", "µm"]
            unit_list = [i.decode("utf-8") for i in unit_list]
            if cal.getUnit() in unit_list:
                xy_voxel = cal.pixelWidth * 1000
                cal.pixelWidth = xy_voxel
                cal.pixelHeight = xy_voxel
                z_voxel = cal.pixelDepth * 1000
                cal.pixelDepth = z_voxel
                cal.setUnit("nm")
                imp.repaintWindow()
            if cal.getUnit() in "nm":
                xy_voxel = cal.pixelWidth
                z_voxel = cal.pixelDepth

            # Awaiting ROI or quits after 5 tries
            count = 0

            omero_roi = True

            rois_wpr = image_wpr.getROIs(user_client)
            list_roi = ROIWrapper.toImageJ(rois_wpr)
            if len(list_roi):
                for roi in list_roi:
                    rm.addRoi(roi)

            while (imp.getRoi() is None) and (rm.getCount() == 0):
                omero_roi = False
                imp.show()
                WaitForUserDialog("Draw the region of interest and press OK").show()
                if count == 5:
                    sys.exit("Too many clicks without ROI")
                else:
                    count = count + 1

            if rm.getCount() == 0:
                rm.reset()
                region_roi = imp.getRoi()
                rm.addRoi(region_roi)

            imp.hide()

            avg_FWHM_X = [[] for _ in range(imp.getNChannels())]
            avg_FWHM_Y = [[] for _ in range(imp.getNChannels())]
            avg_FWHM_Z = [[] for _ in range(imp.getNChannels())]

            # omero_table = []

            omero_avg_columns["Image Name"] = String

            for region_index, region_roi in enumerate(rm.getRoisAsArray()):
                misc.progressbar(
                    region_index + 1, rm.getCount(), 3, "Processing ROI : "
                )
                concat_array = []

                if region_index == 0:
                    channel_order = range(1, imp.getNChannels() + 1)
                    channel_order.insert(0, channel_order.pop(ref_chnl - 1))

                for channel_index, channel in enumerate(channel_order):
                    misc.progressbar(
                        channel_index + 1,
                        imp.getNChannels(),
                        4,
                        "Processing channel : ",
                    )

                    # if region_index == 0:
                    #     avg_FWHM_X.append([])
                    #     avg_FWHM_Y.append([])
                    #     avg_FWHM_Z.append([])

                    # Find brightest spot
                    IJ.run(imp, "Select None", "")

                    imp_current_channel = duplicate_imp_and_calibrate(
                        imp, specific_chnl=channel
                    )

                    stack_stats = scan_for_best_slice(imp_current_channel, region_roi)

                    brightest_spot = coord_brightest_point(
                        imp_current_channel, region_roi, stack_stats["best_slice"]
                    )

                    max_z = min(imp.getNSlices(), 100)

                    if channel == ref_chnl:
                        ref_chnl_x_coord = brightest_spot["X_coord"]
                        ref_chnl_y_coord = brightest_spot["Y_coord"]
                        ref_chnl_z_coord = stack_stats["best_slice"]

                    ROI_size = round(roi_size_cal / xy_voxel)
                    # ROI_size = region_roi.getBounds().width
                    half_ROI_size = round(ROI_size / 2)

                    centered_ROI = Roi(
                        brightest_spot["X_coord"] - half_ROI_size,
                        brightest_spot["Y_coord"] - half_ROI_size,
                        ROI_size,
                        ROI_size,
                    )
                    imp_centered_ROI_current_channel = duplicate_imp_and_calibrate(
                        imp_current_channel, specific_chnl=1, roi=centered_ROI
                    )

                    ROI_size_bg = round(ROI_size / 10)
                    bg_ROI = Roi(ROI_size_bg, ROI_size_bg, ROI_size_bg, ROI_size_bg)

                    bg_subtraction(
                        imp_centered_ROI_current_channel, stack_stats["best_slice"], bg_ROI
                    )
                    imp_centered_ROI_current_channel.show()

                    x2 = int(min(brightest_spot["X_coord"], half_ROI_size))
                    y2 = int(min(brightest_spot["Y_coord"], half_ROI_size))

                    # Redimension stack
                    while (
                        stack_stats["best_slice"] + (max_z / 2)
                        > imp_centered_ROI_current_channel.getNSlices()
                    ):
                        imp_centered_ROI_current_channel.setSlice(
                            imp_centered_ROI_current_channel.getNSlices()
                        )
                        IJ.run(imp_centered_ROI_current_channel, "Add Slice", "")
                    while (
                        stack_stats["best_slice"] + (max_z / 2)
                        < imp_centered_ROI_current_channel.getNSlices()
                    ):
                        imp_centered_ROI_current_channel.setSlice(
                            imp_centered_ROI_current_channel.getNSlices()
                        )
                        IJ.run(imp_centered_ROI_current_channel, "Delete Slice", "")
                    while imp_centered_ROI_current_channel.getNSlices() > max_z:
                        imp_centered_ROI_current_channel.setSlice(1)
                        IJ.run(imp_centered_ROI_current_channel, "Delete Slice", "")
                    while imp_centered_ROI_current_channel.getNSlices() < max_z:
                        imp_centered_ROI_current_channel.setSlice(1)
                        IJ.run(imp_centered_ROI_current_channel, "Add Slice", "")

                    best_slice = max_z / 2

                    # imp_centered_ROI_current_channel.show()
                    # sys.exit()

                    # Projections
                    # X Projection
                    imp_x_proj = reslice_based_on_roi(
                        imp_centered_ROI_current_channel,
                        ROI_size,
                        y2,
                        bg_ROI,
                        best_slice,
                        False,
                    )
                    H = imp_x_proj.getHeight()

                    # Y Projection
                    # IJ.selectWindow(imp_centered_ROI_current_channel.getTitle())
                    IJ.run(imp_centered_ROI_current_channel, "Select None", "")
                    imp_centered_ROI_current_channel.setSlice(best_slice)
                    imp_y_proj = reslice_based_on_roi(
                        imp_centered_ROI_current_channel,
                        ROI_size,
                        x2,
                        bg_ROI,
                        best_slice,
                        True,
                    )

                    imp_centered_ROI_current_channel_proj = ZProjector.run(
                        imp_centered_ROI_current_channel, "max", 1, 100
                    )

                    bg_subtraction(
                        imp_centered_ROI_current_channel_proj, roi=bg_ROI, stat_to_use="min"
                    )
                    imp_centered_ROI_current_channel_proj.setTitle("Project")

                    project_width = ROI_size * 2
                    # imp_centered_ROI_current_channel_proj.show()
                    imp_centered_ROI_current_channel_proj = change_canvas_size(
                        imp_centered_ROI_current_channel_proj,
                        project_width,
                        project_width,
                        "Top-Left",
                        True,
                    )

                    imp_y_proj = change_canvas_size(
                        imp_y_proj, project_width, project_width, "Top-Right", True, True
                    )
                    imp_x_proj = change_canvas_size(
                        imp_x_proj, project_width, project_width, "Bottom-Left", True, True
                    )
                    # scale_value = half_final_size / ROI_size

                    imp_centered_ROI_current_channel.show()
                    imp_centered_ROI_current_channel_proj.show()
                    imp_x_proj.show()
                    imp_y_proj.show()

                    ic = ImageCalculator()
                    imp_montage = ic.run(
                        "Add create", imp_centered_ROI_current_channel_proj, imp_x_proj
                    )
                    imp_montage.show()

                    imp_montage_2 = ic.run("Add create", imp_montage, imp_y_proj)

                    new_size = int((project_width * half_final_size) / ROI_size)
                    imp_montage_2 = imp_montage_2.resize(new_size, new_size, "none")
                    imp_montage_2 = change_canvas_size(
                        imp_montage_2, final_size, final_size, "Top-Left", False
                    )

                    # imp_montage2 = imp_montage_2.resize(final_size, final_size, "none")

                    text_position_start = half_final_size

                    imp_montage_2.setTitle("Project")
                    imp_montage_2.show()

                    # sys.exit()

                    imp_montage.changes = False
                    imp_x_proj.changes = False
                    imp_y_proj.changes = False
                    imp_centered_ROI_current_channel_proj.changes = False
                    imp_montage.close()
                    imp_x_proj.close()
                    imp_y_proj.close()
                    imp_centered_ROI_current_channel_proj.close()

                    IJ.run(imp_montage_2, "32-bit", "")
                    IJ.run(imp_montage_2, "Square Root", "")
                    proj_stats = imp_montage_2.getStatistics()
                    imp_montage_2.setDisplayRange(proj_stats.mean, proj_stats.max)
                    imp_montage_2.getProcessor().invert()
                    imp_montage_2.updateAndDraw()
                    IJ.run(imp_montage_2, "LUTforPSFs2", "")
                    IJ.run(imp_montage_2, "8-bit", "")
                    IJ.run(imp_montage_2, "RGB Color", "")

                    # ─── FWHM AXIAL ─────────────────────────────────────────────────────────────────

                    z_profile_x = range(imp_centered_ROI_current_channel.getNSlices())
                    z_profile_y = []
                    for i in z_profile_x:
                        imp_centered_ROI_current_channel.setSlice(i + 1)
                        z_profile_y.append(
                            imp_centered_ROI_current_channel.getPixel(x2, y2)[0]
                        )

                    curve_fitter_axial = CurveFitter(z_profile_x, z_profile_y)
                    curve_fitter_axial.doFit(CurveFitter.GAUSSIAN)
                    fit_results = curve_fitter_axial.getParams()
                    rounded_fit_results = [round(num, 4) for num in fit_results]

                    # ─── PLOT ───────────────────────────────────────────────────────────────────────

                    amplitude = min(40, imp_centered_ROI_current_channel.getNSlices())
                    max_graph = 0
                    x_plot_ax_real = []
                    y_plot_ax_real = []
                    for i in range(amplitude):
                        x_plot_ax_real.append((i - amplitude / 2) * z_voxel)
                        y_plot_ax_real.append(z_profile_y[best_slice - amplitude / 2 + i])
                        if y_plot_ax_real[i] >= max_graph:
                            max_graph = y_plot_ax_real[i]

                    y_min = 66000
                    y_max = 0
                    x_plot_ax_fit = []
                    y_plot_ax_fit = []
                    for i in range(amplitude * 4):
                        x_plot_ax_fit.append((i / 4.0 - amplitude / 2.0) * z_voxel)
                        x = best_slice - amplitude / 2.0 + i / 4.0
                        y_plot_ax_fit.append(
                            fit_results[0]
                            + (fit_results[1] - fit_results[0])
                            * math.exp(
                                (-(x - fit_results[2]) * (x - fit_results[2]))
                                / (2 * fit_results[3] * fit_results[3])
                            )
                        )

                        if y_plot_ax_fit[i] >= max_graph:
                            max_graph = y_plot_ax_fit[i]
                        if y_min > y_plot_ax_fit[i]:
                            y_min = y_plot_ax_fit[i]
                        if y_max < y_plot_ax_fit[i]:
                            y_max = y_plot_ax_fit[i]

                    HM = (y_max - y_min) / 2
                    try:
                        k = (
                            -2
                            * fit_results[3]
                            * fit_results[3]
                            * math.log(
                                (HM - fit_results[0]) / (fit_results[1] - fit_results[0])
                            )
                        )
                    except (ValueError, ZeroDivisionError):
                        IJ.log(
                            "ISSUE WITH CHANNEL "
                            + str(channel)
                            + " AND ROI "
                            + str(region_index)
                            + ", WILL BE SKIPPED"
                        )
                        temp_imp = IJ.createImage(
                            "Untitled",
                            "8-bit black",
                            imp_montage_2.getWidth(),
                            imp_montage_2.getHeight(),
                            2,
                        )
                        stack_imp = ImagesToStack().run([imp_montage_2, temp_imp, temp_imp])
                        concat_array.append(stack_imp)

                        avg_FWHM_X[channel - 1].append(None)
                        avg_FWHM_Y[channel - 1].append(None)
                        avg_FWHM_Z[channel - 1].append(None)
                        continue
                    try:
                        FWHMa = 2 * z_voxel * math.sqrt(k)
                    except ValueError:
                        FWHMa = 0

                    fwhm_axial_plot = Plot(
                        "FWHM axial", "Z", "Intensity", x_plot_ax_fit, y_plot_ax_fit
                    )
                    fwhm_axial_plot.setLimits(-4000, 4000, 0, max_graph * 1.1)
                    fwhm_axial_plot.add("circles", x_plot_ax_real, y_plot_ax_real)
                    fwhm_axial_plot.addLabel(0, 0, "FWHM axial =" + str(FWHMa) + "nm")
                    fwhm_axial_imp = fwhm_axial_plot.getImagePlus()
                    fwhm_axial_imp = change_canvas_size(
                        fwhm_axial_imp, final_size, final_size, "Center", False
                    )

                    # fwhm_axial_imp.show()
                    # ─── FWHM LATERAL ───────────────────────────────────────────────────────────────

                    imp_centered_ROI_current_channel.setSlice(best_slice)
                    x = range(-8, 9)
                    y = []
                    yy = []

                    for i in range(17):
                        temp_y = 0
                        temp_yy = 0

                        for k in range(
                            int(-(math.floor(line_thickness / 2))),
                            int(-(math.floor(line_thickness / 2)) + line_thickness),
                        ):
                            temp_y = (
                                temp_y
                                + imp_centered_ROI_current_channel.getPixel(
                                    x2 - 8 + i, y2 + k
                                )[0]
                                / line_thickness
                            )
                            temp_yy = (
                                temp_yy
                                + imp_centered_ROI_current_channel.getPixel(
                                    x2 + k, y2 - 8 + i
                                )[0]
                                / line_thickness
                            )

                        y.append(temp_y)
                        yy.append(temp_yy)

                    curve_fitter_lateral_1 = CurveFitter(x, y)
                    curve_fitter_lateral_1.doFit(CurveFitter.GAUSSIAN)
                    fit_results_lateral_1 = curve_fitter_lateral_1.getParams()

                    curve_fitter_lateral_2 = CurveFitter(x, yy)
                    curve_fitter_lateral_2.doFit(CurveFitter.GAUSSIAN)
                    fit_results_lateral_2 = curve_fitter_lateral_2.getParams()

                    # ─── PLOT ───────────────────────────────────────────────────────────────────────

                    x_plot_lat_real = []
                    y_plot_lat_real = []
                    yy_plot_lat_real = []

                    y_min = 66000
                    y_max = 0
                    max_graph = 0
                    for i in range(17):
                        x_plot_lat_real.append((i - 8) * xy_voxel)
                        y_plot_lat_real.append(y[i])
                        yy_plot_lat_real.append(yy[i])

                        if max(y[i], yy[i]) >= max_graph:
                            max_graph = max(y[i], yy[i])

                    x_plot_lat_fit = []
                    y_plot_lat_fit = []
                    yy_plot_lat_fit = []

                    for i in range(65):
                        x = i / 4.0 - 8.0
                        x_plot_lat_fit.append(x * xy_voxel)
                        y_plot_lat_fit.append(
                            fit_results_lateral_1[0]
                            + (fit_results_lateral_1[1] - fit_results_lateral_1[0])
                            * math.exp(
                                (
                                    -(x - fit_results_lateral_1[2])
                                    * (x - fit_results_lateral_1[2])
                                )
                                / (2 * fit_results_lateral_1[3] * fit_results_lateral_1[3])
                            )
                        )
                        yy_plot_lat_fit.append(
                            fit_results_lateral_2[0]
                            + (fit_results_lateral_2[1] - fit_results_lateral_2[0])
                            * math.exp(
                                (
                                    -(x - fit_results_lateral_2[2])
                                    * (x - fit_results_lateral_2[2])
                                )
                                / (2 * fit_results_lateral_2[3] * fit_results_lateral_2[3])
                            )
                        )

                        if max(y_plot_lat_fit[i], yy_plot_lat_fit[i]) >= max_graph:
                            max_graph = max(y_plot_lat_fit[i], yy_plot_lat_fit[i])
                        if y_min > min(y_plot_lat_fit[i], yy_plot_lat_fit[i]):
                            y_min = min(y_plot_lat_fit[i], yy_plot_lat_fit[i])
                        if y_max < max(y_plot_lat_fit[i], yy_plot_lat_fit[i]):
                            y_max = max(y_plot_lat_fit[i], yy_plot_lat_fit[i])

                    HM = (y_max - y_min) / 2
                    k = (
                        -2
                        * fit_results_lateral_1[3]
                        * fit_results_lateral_1[3]
                        * math.log(
                            (HM - fit_results_lateral_1[0])
                            / (fit_results_lateral_1[1] - fit_results_lateral_1[0])
                        )
                    )

                    try:
                        FWHMl = 2 * xy_voxel * math.sqrt(k)
                    except ValueError:
                        FWHMl = 0

                    try:
                        ky = (
                            -2
                            * fit_results_lateral_2[3]
                            * fit_results_lateral_2[3]
                            * math.log(
                                (HM - fit_results_lateral_2[0])
                                / (fit_results_lateral_2[1] - fit_results_lateral_2[0])
                            )
                        )
                    except ZeroDivisionError:
                        ky = 0
                    try:
                        FWHMly = 2 * xy_voxel * math.sqrt(ky)
                    except ValueError:
                        FWHMly = 0

                    fwhm_lateral_plot = Plot(
                        "FWHM lateral",
                        "X (black) or Y (blue)",
                        "Intensity",
                        x_plot_lat_fit,
                        y_plot_lat_fit,
                    )
                    fwhm_lateral_plot.setLimits(
                        -8 * xy_voxel, 8 * xy_voxel, 0, max_graph * 1.1
                    )
                    fwhm_lateral_plot.setColor("blue")
                    fwhm_lateral_plot.add("line", x_plot_lat_fit, yy_plot_lat_fit)
                    fwhm_lateral_plot.add("circles", x_plot_lat_real, yy_plot_lat_real)
                    fwhm_lateral_plot.setColor("black")
                    fwhm_lateral_plot.add("circles", x_plot_lat_real, y_plot_lat_real)
                    fwhm_lateral_plot.addLabel(
                        0,
                        0,
                        "FWHM lateral X ="
                        + str(round(FWHMl, 0))
                        + "nm; FWHM lateral Y ="
                        + str(round(FWHMly, 0))
                        + "nm; Average ="
                        + str(round((FWHMl + FWHMly) / 2))
                        + "nm",
                    )
                    fwhm_lateral_imp = fwhm_lateral_plot.getImagePlus()
                    fwhm_lateral_imp = change_canvas_size(
                        fwhm_lateral_imp, final_size, final_size, "Center", False
                    )

                    imp_centered_ROI_current_channel.changes = False
                    imp_centered_ROI_current_channel.close()

                    stack_imp = ImagesToStack().run(
                        [imp_montage_2, fwhm_axial_imp, fwhm_lateral_imp]
                    )

                    # stack_imp.show()

                    # stack_position = 1 + ((channel-1) * 3)
                    stack_position = channel

                    if channel == ref_chnl:
                        text_overlay = Overlay()
                    text_font = Font("Arial", Font.PLAIN, 14)
                    date_text = TextRoi(
                        text_position_start + 20,
                        text_position_start + 20,
                        str(today),
                        text_font,
                    )
                    channel_text = TextRoi(
                        text_position_start + 20,
                        text_position_start + 40,
                        "Channel               = " + str(channel),
                        text_font,
                    )
                    roi_text = TextRoi(
                        text_position_start + 20,
                        text_position_start + 60,
                        "ROI                   = " + str(region_roi.getName()),
                    )
                    fwhml_text = TextRoi(
                        text_position_start + 20,
                        text_position_start + 80,
                        "FWHM lateral          : X = "
                        + str(int(FWHMl))
                        + "nm;  Y = "
                        + str(int(FWHMly))
                        + "nm",
                    )
                    fwhml_avg_text = TextRoi(
                        text_position_start + 20,
                        text_position_start + 100,
                        "FWHM lateral average = " + str(int((FWHMl + FWHMly) / 2)) + "nm",
                    )
                    fwhma_text = TextRoi(
                        text_position_start + 20,
                        text_position_start + 120,
                        "FWHM axial           = " + str(int(FWHMa)) + "nm",
                    )
                    if channel == ref_chnl:
                        x_shift = 0
                        y_shift = 0
                        z_shift = 0
                    else:
                        x_shift = brightest_spot["X_coord"] - ref_chnl_x_coord
                        y_shift = brightest_spot["Y_coord"] - ref_chnl_y_coord
                        z_shift = stack_stats["best_slice"] - ref_chnl_z_coord
                        shift_xy_text = TextRoi(
                            text_position_start + 20,
                            text_position_start + 140,
                            "X Shift : "
                            + str(x_shift)
                            + "pxls; Y Shift : "
                            + str(y_shift)
                            + "pxls from C"
                            + str(ref_chnl),
                        )
                        set_roi_color_and_position(
                            shift_xy_text, Color.red, position_frame=channel_index + 1
                        )
                        text_overlay.add(shift_xy_text)

                        shift_z_text = TextRoi(
                            text_position_start + 20,
                            text_position_start + 160,
                            "Z Shift : " + str(z_shift) + "plane(s) from C" + str(ref_chnl),
                        )
                        set_roi_color_and_position(
                            shift_z_text, Color.red, position_frame=channel_index + 1
                        )
                        text_overlay.add(shift_z_text)

                        kv_dict.add(
                            NamedValue(
                                "C"
                                + str(channel)
                                + "_shift_X_ROI_"
                                + str(region_roi.getName()),
                                str(brightest_spot["X_coord"] - ref_chnl_x_coord),
                            )
                        )
                        kv_dict.add(
                            NamedValue(
                                "C"
                                + str(channel)
                                + "_shift_Y_ROI_"
                                + str(region_roi.getName()),
                                str(brightest_spot["Y_coord"] - ref_chnl_y_coord),
                            )
                        )
                        kv_dict.add(
                            NamedValue(
                                "C"
                                + str(channel)
                                + "_shift_Z_ROI_"
                                + str(region_roi.getName()),
                                str(stack_stats["best_slice"] - ref_chnl_z_coord),
                            )
                        )

                    avg_FWHM_X[channel - 1].append(FWHMl)
                    avg_FWHM_Y[channel - 1].append(FWHMly)
                    avg_FWHM_Z[channel - 1].append(FWHMa)
                    # kv_dict['C' + str(channel) + '_shift_Y'] = str(brightest_spot['Y_coord'] - C1_y_coord)
                    # kv_dict['C' + str(channel) + '_shift_Z'] = str(stack_stats['best_slice'] - C1_z_coord)

                    set_roi_color_and_position(
                        date_text, Color.red, position_frame=channel_index + 1
                    )
                    set_roi_color_and_position(
                        channel_text, Color.red, position_frame=channel_index + 1
                    )
                    set_roi_color_and_position(
                        roi_text, Color.red, position_frame=channel_index + 1
                    )
                    set_roi_color_and_position(
                        fwhml_text, Color.red, position_frame=channel_index + 1
                    )
                    set_roi_color_and_position(
                        fwhml_avg_text, Color.red, position_frame=channel_index + 1
                    )
                    set_roi_color_and_position(
                        fwhma_text, Color.red, position_frame=channel_index + 1
                    )

                    text_overlay.add(date_text)
                    text_overlay.add(channel_text)
                    text_overlay.add(roi_text)
                    text_overlay.add(fwhml_text)
                    text_overlay.add(fwhml_avg_text)
                    text_overlay.add(fwhma_text)

                    # stack_imp.setOverlay(text_overlay)
                    concat_array.append(stack_imp)

                    kv_dict.add(
                        NamedValue(
                            "C"
                            + str(channel)
                            + "_FWHM_Axial_X_ROI_"
                            + str(region_roi.getName()),
                            str(int(FWHMl)),
                        )
                    )
                    kv_dict.add(
                        NamedValue(
                            "C"
                            + str(channel)
                            + "_FWHM_Axial_Y_ROI_"
                            + str(region_roi.getName()),
                            str(int(FWHMly)),
                        )
                    )
                    kv_dict.add(
                        NamedValue(
                            "C"
                            + str(channel)
                            + "_FWHM_Axial_avg_ROI_"
                            + str(region_roi.getName()),
                            str(int((FWHMl + FWHMly) / 2)),
                        )
                    )
                    kv_dict.add(
                        NamedValue(
                            "C" + str(channel) + "_FWHM_Z_ROI_" + str(region_roi.getName()),
                            str(int(FWHMa)),
                        )
                    )


                concat_imp = Concatenator.run(concat_array)
                concat_imp.setTitle(imp.getTitle() + "_maintenance")

                concat_imp.setOverlay(text_overlay)
                concat_imp.flattenStack()

                fixed_title = (
                    re.sub(r"\.([^.]*)$", r"", imp.getTitle())
                    .replace(" ", "_")
                    .replace(":", "_")
                )

                roi_name = region_roi.getName()
                roi_name = roi_name.replace(":", "_")
                out_path = os.path.join(
                    destination,
                    fixed_title + "_maintenance_ROI_" + roi_name + ".tif",
                )

                IJ.log("\\Update5:Exporting image to temp folder...")
                bf.export(concat_imp, out_path)

                if OMERO_link:
                    IJ.log("\\Update5:Uploading image to OMERO...")
                    _ = omerotools.upload_image_to_omero(
                        user_client, out_path, dataset_id
                    )
                    os.remove(out_path)
                    if not omero_roi:
                        IJ.log("\\Update5:Uploading ROI to OMERO...")
                        roivec = omerotools.save_rois_to_omero(
                            user_client, image_wpr, rm
                        )
                    concat_imp.close()
                else:
                    IJ.log("\\Update5:Image is saved : " + out_path)

            for i in range(imp.getNChannels()):
                if rm.getCount() > 1:
                    kv_dict.add(
                        NamedValue(
                            "AVERAGE_FWHM_X_All_ROIS_C" + str(i + 1),
                            str(misc.calculate_mean_and_stdv(avg_FWHM_X[i])[0]),
                        )
                    )
                    kv_dict.add(
                        NamedValue(
                            "AVERAGE_FWHM_Y_All_ROIS_C" + str(i + 1),
                            str(misc.calculate_mean_and_stdv(avg_FWHM_Y[i])[0]),
                        )
                    )
                    kv_dict.add(
                        NamedValue(
                            "AVERAGE_FWHM_Z_All_ROIS_C" + str(i + 1),
                            str(misc.calculate_mean_and_stdv(avg_FWHM_Z[i])[0]),
                        )
                    )

                average_values.extend(
                    [
                        Double(misc.calculate_mean_and_stdv(avg_FWHM_X[i])[0]),
                        Double(misc.calculate_mean_and_stdv(avg_FWHM_Y[i])[0]),
                        Double(misc.calculate_mean_and_stdv(avg_FWHM_Z[i])[0]),
                    ]
                )

                omero_avg_columns["C" + str(i) + " FWHM Axial X"] = Double
                omero_avg_columns["C" + str(i) + " FWHM Axial Y"] = Double
                omero_avg_columns["C" + str(i) + " FWHM Z"] = Double


            omero_avg_columns["Acquisition Date"] = String
            omero_avg_columns["Acquisition Date Number"] = Long
            omero_avg_columns["Microscope"] = String
            omero_avg_columns["Objective Magnification"] = String
            omero_avg_columns["Objective NA"] = String
            omero_avg_columns["Image"] = ImageData

            average_values.extend(
                [
                    acq_date,
                    acq_date_number,
                    project_name,
                    str(int(obj_mag)) + "x",
                    str(obj_na),
                    image_wpr.asImageData(),
                ]
            )

            kv_dict.add(NamedValue("ACQUISITION_DATE", acq_date))
            kv_dict.add(NamedValue("MICROSCOPE", project_name))
            kv_dict.add(NamedValue("OBJECTIVE_MAGNIFICATION", str(int(obj_mag)) + "x"))
            kv_dict.add(NamedValue("OBJECTIVE_NA", str(obj_na)))
            kv_dict.add(NamedValue("ACQUISITION_DATE_NUMBER", str(acq_date_number)))
            if delete_previous_kv:
                omerotools.delete_annotation(user_client, image_wpr)
                omerotools.delete_annotation(user_client, dataset_wpr)
            omerotools.add_keyvalue_annotation(
                user_client, image_wpr, kv_dict, "PSF Inspector"
            )

            imp.close()
            omero_avg_table.append(average_values)

            # omero_columns = create_table_columns(omero_columns)

        # upload_array_as_omero_table(ctx, gateway, map(list, zip(*omero_table)), omero_columns, image_id)
        omerotools.upload_array_as_omero_table(
            user_client,
            "PSF Inspector results",
            map(list, zip(*omero_avg_table)),
            omero_avg_columns,
            image_wpr,
        )

    finally:
        user_client.disconnect()

    IJ.log("Script finished.")
