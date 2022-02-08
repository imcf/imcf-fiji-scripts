/*
#@ String (visibility=MESSAGE,label="Prerequisites:",value="One or more ROIs required for cropping.",persist=false) msg
#@ ImagePlus tst_slide
#@ Boolean(label="Pad crops to same size?",description="pad all crops with black to match the maximum size in X and Y",default=true) pad_crops
#@ Boolean(label="Specify output directory for results",description="if unchecked, the next setting will be ignored",default=false) specify_out_dir
#@ Integer(label="Starting index for saving ROIs",min=0,persist=false) start_i
#@ File(label="Output directory (if enabled above)",style="directory") out_dir
*/

function dprint(message) {
    /* debug-print helper function */

    // uncomment the print statement to get debug messages:
    // print(message);
}


function lpad(str, len) {
    /* left-pad a string with zeros to a given total length */
    cur_len = lengthOf("" + str);
    if (cur_len < len) {
        for (i = 0; i < (len - cur_len); i++) {
            str = "0" + str;
        }
    }
    return str;
}

setBatchMode(true);

selectImage(tst_slide);
tst_slide_id = getImageID();
title = replace(getTitle(), ".tif", "");
title = replace(title, ".czi", "");

if (specify_out_dir == false) {
    out_dir = getDirectory("image");
}
print("Path for storing results: " + out_dir);

nrois = roiManager("count");
if (nrois == 0) {
    print("At least one ROI is required!");
    exit();
}

// find the largest ROI size in x and y (independently!):
roi_widths = newArray(nrois);
roi_heights = newArray(nrois);
for (i = 0; i < nrois; i++) {
    roiManager("select", i);
    Roi.getBounds(_, _, rwidth, rheight);
    // print(rwidth + " x " + rheight);
    roi_widths[i] = rwidth;
    roi_heights[i] = rheight;
}
Array.getStatistics(roi_widths, _, max_width, _, _);
Array.getStatistics(roi_heights, _, max_height, _, _);
print("maximum bounds size: " + max_width + " x " + max_height);

// now process all ROIs, duplicate them and optionally pad the result
print("Processing " + nrois + " ROIs...");
// pad index count by two more digits that the current ROI set would need, to
// allow for combining of multiple slides manually:
nroi_chars = lengthOf("" + nrois) + 2;
// use "cur_i" so we don't have to change "start_i" but can refer to it later:
cur_i = start_i;
out_pfx = out_dir + "/" + title + "_roi-";
for (i = 0; i < nrois; i++) {
    // print("Processing ROI " + i);
    run("Select None");
    roiManager("select", i);
    run("Duplicate...", "duplicate");
    if (pad_crops == true) {
        run("Canvas Size...", "width=" + max_width + " height=" + max_height + " position=Center zero");
    }
    out_fname = out_pfx + lpad(cur_i, nroi_chars) + ".tif";
    dprint("Saving ROI to " + out_fname);
    saveAs("Tiff", out_fname);
    cur_i++;
    close();
    selectImage(tst_slide_id);
}

setBatchMode("exit and display");
print("Processed " + nrois + " ROIs.");

print("tst:padded-sections:firstfile:" + out_pfx + lpad(start_i, nroi_chars) + ".tif");
print("tst:padded-sections:lastfile:" + out_pfx + lpad(cur_i - 1, nroi_chars) + ".tif");
print("\n\n--- Crop and Pad ROIs COMPLETED ---\n\n");
