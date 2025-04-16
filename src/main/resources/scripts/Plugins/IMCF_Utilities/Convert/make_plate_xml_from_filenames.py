# @ File(label="Folder with your images", style="directory", description="Folder with the images") src_dir
# @ String(label="Extension for the images to look for", value="vsi") filename_filter
# @ String(label="Name of the plate") plate_name

# ─── IMPORTS ────────────────────────────────────────────────────────────────────

import string

from ij import IJ
from imcflibs import pathtools, strtools
from imcflibs.imagej import misc
from java.io import File
from java.lang import Integer
from java.util import UUID as juuid
from loci.formats import ImageReader, MetadataTools
from ome.specification import XMLWriter
from ome.xml.model import OME, UUID, Plate, TiffData, Well, WellSample
from ome.xml.model.primitives import NonNegativeInteger

# ─── FUNCTIONS ──────────────────────────────────────────────────────────────────


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




# ─── VARIABLES ──────────────────────────────────────────────────────────────────

# ─── MAIN CODE ──────────────────────────────────────────────────────────────────

IJ.log("\\Clear")
IJ.log("Script starting...")

ome_xml = OME()

# Retrieve list of files
path_info = pathtools.parse_path(src_dir)
    files = pathtools.listdir_matching(
        path_info["orig"], filename_filter, fullpath=True, sort=True
    )

# ome_xml = set_files_information(files, ome_xml)
new_ome = OME()

# Set info about plate
new_plate = Plate()
new_plate.setName(plate_name)
new_plate.setID("Plate:0")

    if filename_filter.startswith("tif"):
        out_xml = pathtools.join2(path_info["orig"], plate_name + ".companion.ome")
else:
    out_xml = pathtools.join2(path_info["orig"], plate_name + ".ome.xml")

well_list = []
well_index = 0

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
        new_well.setID("Well:0:%s" % well_index)
        new_well.setRow(
            NonNegativeInteger(
                Integer(string.ascii_lowercase.index(well_name[0].lower()))
            )
        )
        new_well.setColumn(NonNegativeInteger(Integer(well_name[1:])))
        new_plate.addWell(new_well)
        well_index = well_index + 1
    else:
        out_xml = pathtools.join2(path_info["orig"], plate_name + ".ome.xml")

    for image_index in range(metadata_root.sizeOfImageList()):
        current_padded_index = pad_number(
            image_index, len(str(metadata_root.sizeOfImageList()))
        )
        misc.progressbar(file_index + 1, len(files), 1, "Working on : ")
        new_image = metadata_root.getImage(image_index)
        new_image.setID("Image:%s" % current_padded_index)
        new_image.setDescription("")
        if metadata_root.sizeOfImageList() > 1:
        padded_index = strtools.pad_number(file_index, len(str(len(files))))
        file_info = pathtools.parse_path(file)
        else:
            image_name = file_info["fname"]
        new_image.setName(image_name)
            current_padded_index = strtools.pad_number(
                image_index, len(str(metadata_root.sizeOfImageList()))
            )

        new_pxls = new_image.getPixels()
        try:
            new_tiffdata = new_pxls.getTiffData(0)
            new_uuid = UUID()
            new_uuid.setFileName(image_name)
            uuid_str = juuid.randomUUID().toString()
            new_uuid.setValue("urn:uuid:%s" % uuid_str)
            new_tiffdata.setUUID(new_uuid)
        except:
            new_tiffdata = TiffData()
            # new_tiffdata.setIFD(NonNegativeInteger(0))

        new_pxls.addTiffData(new_tiffdata)
        new_image.setPixels(new_pxls)

        new_well_sample = WellSample()
        new_well_sample.setID(
            "WellSample:0:%s:%s" % (well_index, new_well.sizeOfWellSampleList())
        )

        new_well_sample.linkImage(new_image)
        new_well.addWellSample(new_well_sample)

        new_ome.addImage(new_image)

new_ome.addPlate(new_plate)

new_ome_str = new_ome.toString()


XMLWriter().writeFile(File(out_xml), new_ome, False)


IJ.log("FINISHED")
