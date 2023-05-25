# @ File(label="Folder with your images", style="directory", description="Folder with the images") src_dir
# @ String(label="Extension for the images to look for", value="vsi") filename_filter
# @ String(label="Name of the plate") plate_name

# ─── IMPORTS ────────────────────────────────────────────────────────────────────

import glob
import os
import re
import string

from ome.xml.model import OME, Plate, Well, WellSample, UUID
from ome.xml.model.primitives import NonNegativeInteger

from ome.specification import XMLWriter


from ij import IJ
from loci.formats import ImageReader, MetadataTools

from imcflibs import pathtools

from java.lang import Integer
from java.io import File
from java.util import UUID as juuid

# Bioformats imports

# ─── FUNCTIONS ──────────────────────────────────────────────────────────────────


def list_all_filenames(source, filetype):
    """Get a sorted list of all files of specified filetype in a given directory

    Parameters
    ----------
    source : str
        Path to source dir
    filetype : str
        File extension to specify filetype

    Returns
    -------
    List
        List of all files of the given type in the source dir
    """

    # os.chdir(str(source))
    return sorted_alphanumeric(
        glob.glob(os.path.join(source, "*" + filetype))
    )  # sorted by name


def get_ome_reader_from_image(path_to_image):
    """get the whole OME_metadata from a given image using Bio-Formats

    Parameters
    ----------
    path_to_image : str
        full path to the input image

    Returns
    -------
    array
        the physical px size as float for x,y,z
    """

    reader = ImageReader()
    ome_meta = MetadataTools.createOMEXMLMetadata()
    reader.setMetadataStore(ome_meta)
    reader.setId(str(path_to_image))

    return reader


def get_metadata_from_image(path_to_image):
    """get image info from a given image using Bio-Formats

    Parameters
    ----------
    path_to_image : str
        full path to the input image

    Returns
    -------
    TODO
    """

    reader = ImageReader()
    ome_meta = MetadataTools.createOMEXMLMetadata()
    reader.setMetadataStore(ome_meta)
    reader.setId(str(path_to_image))

    phys_size_x = ome_meta.getPixelsPhysicalSizeX(0)
    phys_size_y = ome_meta.getPixelsPhysicalSizeY(0)
    # phys_size_z = ome_meta.getPixelsPhysicalSizeZ(0)
    pixel_size_x = ome_meta.getPixelsSizeX(0)
    pixel_size_y = ome_meta.getPixelsSizeY(0)
    pixel_size_z = ome_meta.getPixelsSizeZ(0)
    channel_count = ome_meta.getPixelsSizeC(0)
    timepoints_count = ome_meta.getPixelsSizeT(0)
    dimension_order = ome_meta.getPixelsDimensionOrder(0)
    pixel_type = ome_meta.getPixelsType(0)

    image_calibration = {
        "unit_width": phys_size_x.value(),
        "unit_height": phys_size_y.value(),
        # "unit_depth": phys_size_z.value(),
        "pixel_width": pixel_size_x.getNumberValue(),
        "pixel_height": pixel_size_y.getNumberValue(),
        "slice_count": pixel_size_z.getNumberValue(),
        "channel_count": channel_count.getNumberValue(),
        "timepoints_count": timepoints_count.getNumberValue(),
        "dimension_order": dimension_order,
        "pixel_type": pixel_type,
    }

    reader.close()

    return image_calibration


def sorted_alphanumeric(data):
    """Sort a list alphanumerically

    Parameters
    ----------
    data : list
        List containing all the files to sort

    Returns
    -------
    list
        List with filenames sorted
    """

    def convert(text):
        return int(text) if text.isdigit() else text.lower()

    def alphanum_key(key):
        return [convert(c) for c in re.split("([0-9]+)", key)]

    return sorted(data, key=alphanum_key)


def pad_number(index, pad_length=2):
    return str(index).zfill(pad_length)


# def get_files_information(files, ome):
#     well_dict = {}
#     image_dict = {}

#     for file_index, file in enumerate(files):
#         padded_index = pad_number(file_index, len(str(len(files))))

#         file_name = pathtools.parse_path(file)["basename"]
#         well_name = file_name[4 : file_name.find("_")]

#         image_info = get_metadata_from_image(file)
#         ome_meta = get_ome_metadata_from_image(file)

#         image = Image()
#         image.setID("Image:%s" % padded_index)

#         pixels = Pixels()
#         pixels.setID("Pixels:%s" % padded_index)
#         pixels.setSizeX(ome_meta.getPixelsSizeX(0).getNumberValue())
#         pixels.setSizeY(ome_meta.getPixelsSizeY(0).getNumberValue())
#         pixels.setSizeZ(ome_meta.getPixelsSizeZ(0).getNumberValue())
#         pixels.setSizeC(ome_meta.getPixelsSizeC(0).getNumberValue())
#         pixels.setSizeT(ome_meta.getPixelsSizeT(0).getNumberValue())
#         pixels.setDimensionOrder(ome_meta.getPixelsDimensionOrder(0).getNumberValue())
#         pixels.setType(ome_meta.getPixelsType(0).getNumberValue())

#         for channel_index, current_channel in enumerate(image_info["channel_count"]):
#             channel = Channel()
#             channel.setID("Channel:%s:0" % channel_index)
#             channel.setAcquisitionMode(
#                 AcquisitionMode().fromString(
#                     image_info["channel_" + str(channel_index) + "_acquisition_mode"]
#                 )
#             )

#         well = Well()
#         well.setID("Well:0:%s" % file_index)
#         well.setRow(string.ascii_lowercase.index(well_name[0].lower()))
#         well.setColumn(well_name[1:])

#         well_sample = WellSample()
#         well_sample.setID("WellSample:0:%s:0" % padded_index)
#         well_sample.setIndex(pad_number(file_index, len(str(len(files) + 1))))
#         well_dict["ImageRef"].append("Image:%s" % padded_index)

#         image_dict["ID"].append("Image:%s" % padded_index)

#         image_dict["PixelsID"].append("Pixels:%s" % padded_index)
#         image_dict[""]


#         return well_dict, image_dict


def progressbar(progress, total, line_number, prefix=""):
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
    x = int(size * progress / total)
    IJ.log(
        "\\Update%i:%s[%s%s] %i/%i\r"
        % (line_number, prefix, "#" * x, "." * (size - x), progress, total)
    )


# ─── VARIABLES ──────────────────────────────────────────────────────────────────

# ─── MAIN CODE ──────────────────────────────────────────────────────────────────

IJ.log("\\Clear")
IJ.log("Script starting...")

ome_xml = OME()

# Retrieve list of files
path_info = pathtools.parse_path(src_dir)
files = list_all_filenames(path_info["orig"], filename_filter)

# ome_xml = set_files_information(files, ome_xml)
new_ome = OME()

# Set info about plate
new_plate = Plate()
new_plate.setName(plate_name)
new_plate.setID("Plate:0")

out_xml = pathtools.join2(path_info["orig"], plate_name + ".companion.ome")

well_list = []

for file_index, file in enumerate(files):
    progressbar(file_index + 1, len(files), 1, "Working on : ")

    current_reader = get_ome_reader_from_image(file)
    metadata_root = current_reader.getMetadataStoreRoot()

    padded_index = pad_number(file_index, len(str(len(files))))

    file_info = pathtools.parse_path(file)
    file_name = file_info["basename"]
    well_name = file_name[4 : file_name.find("_")]

    if file_index == 0:
        for experimenter_index in range(metadata_root.sizeOfExperimenterList()):
            current_experimenter = metadata_root.getExperimenter(experimenter_index)
            new_ome.addExperimenter(current_experimenter)
        for instrument_index in range(metadata_root.sizeOfInstrumentList()):
            current_instrument = metadata_root.getInstrument(instrument_index)
            new_ome.addInstrument(current_instrument)

    if well_name not in well_list:
        well_list.append(well_name)
        new_well = Well()
        new_well.setID("Well:0:%s" % file_index)
        new_well.setRow(
            NonNegativeInteger(
                Integer(string.ascii_lowercase.index(well_name[0].lower()))
            )
        )
        new_well.setColumn(NonNegativeInteger(Integer(well_name[1:])))
    else:
        new_well = Plate.getWell(well_list.index(well_name))

    for image_index in range(metadata_root.sizeOfImageList()):
        new_image = metadata_root.getImage(image_index)
        new_image.setID("Image:%s" % padded_index)
        new_image.setDescription("")
        new_image.setName(file_info["fname"])

        new_pxls = new_image.getPixels()
        new_tiffdata = new_pxls.getTiffData(0)

        uuid_str = juuid.randomUUID().toString()

        new_uuid = UUID()
        new_uuid.setFileName(file_info["fname"])
        new_uuid.setValue("urn:uuid:%s" % uuid_str)
        new_tiffdata.setUUID(new_uuid)
        new_pxls.setTiffData(0, new_tiffdata)
        new_image.setPixels(new_pxls)

        new_well_sample = WellSample()
        new_well_sample.setID(
            "WellSample:0:%s:%s" % (padded_index, new_well.sizeOfWellSampleList())
        )

        new_well_sample.linkImage(new_image)
        new_well.addWellSample(new_well_sample)

        new_ome.addImage(new_image)

    new_plate.addWell(new_well)
new_ome.addPlate(new_plate)

new_ome_str = new_ome.toString()

# dbf = DocumentBuilderFactory.newInstance()
# db = dbf.newDocumentBuilder()

XMLWriter().writeFile(File(out_xml), new_ome, False)

# f = open(out_xml, "wb")
# f.write(new_ome_str)
# f.close()

IJ.log("FINISHED")
