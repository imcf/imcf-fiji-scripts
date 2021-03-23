// @File(label="source directory",style="directory") dir1
// @File(label="destination directory",style="directory") dir2
// @String(label="open only files of type",choices={".mvd2",".lif",".sld",".czi", ".nd2", ".tif", ".tf8", ".lsm"}) infiletype
// @String(label="save as file type",choices={"ICS-1","ICS-2","OME-TIFF1","OME-TIFF2", "ImageJ-TIF", "CellH5"}) outfiletype

// -------------------------------------------------------------------------------
// This is a batch converter to convert between Bio-formats/ImageJ supported file formats
// -------------------------------------------------------------------------------

// check user selection and translate into proper file endings
if (outfiletype == "ICS-1") {
    tgt_suffix = ".ids";
} else if (outfiletype == "ICS-2") {
    tgt_suffix = ".ics";
} else if (outfiletype == "OME-TIFF1") {
    tgt_suffix = ".ome.tif";
} else if (outfiletype == "OME-TIFF2") {
    tgt_suffix = ".tif";
} else if (outfiletype == "ImageJ-TIF") {
    tgt_suffix = ".tif";
} else if (outfiletype == "CellH5") {
    tgt_suffix = ".ch5";
}

list = getFileList(dir1);

setBatchMode(true);

for (i=0; i<list.length; i++) {
    // only open an image with the requested extension:
    if(endsWith(list[i], infiletype)){

        incoming = dir1 + File.separator + list[i];

        //open the image at position i as a hyperstack using the bio-formats
        //opens all images of a container file (e.g. *.lif, *.sld)
        run("Bio-Formats Importer", "open=[" + incoming + "] color_mode=Default open_all_series view=Hyperstack stack_order=XYCZT use_virtual_stack");

        // get image IDs of all open images:
        all = newArray(nImages);

        for (k=0; k < nImages; k++) {
            selectImage(k+1);
            all[k] = getImageID;
            title = getTitle();
            title = replace(title, infiletype, "");
            title = replace(title, " ", "_");
            if (indexOf(title, "/") >= 0) {
                title = replace(title, '/', '_');
            }
            print("saving file..." + title);

            // construct the output file name and path
            outFile = dir2 + File.separator + title + tgt_suffix;

            // save the image in the chosen file format
            if (outfiletype == "ImageJ-TIF"){
                saveAs("Tiff", outFile);
            }

            else {
                run("Bio-Formats Exporter", "save=[" + outFile + "]");
            }

            print("Done");
        }

        // close all images to free the memory
        run("Close All");
    }
}

print(" ");
print("All done");
