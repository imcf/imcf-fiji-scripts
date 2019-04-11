/*
#@ String (visibility=MESSAGE,label="Prerequisites:",value="a label image and ROIs with the labels as names.",persist=false) msg

#@ ImagePlus (label="Slide image with tissue sections") tst_slide
#@ ImagePlus (label="Label image") tst_labels
*/


function lpad(str, len) {
	/* left-pad a string with zeros to a given total length */
	cur_len = lengthOf("" + str);
    if (cur_len < len) {
        for (i=0; i<(len-cur_len); i++) {
            str = "0" + str;
        }
    }
    return str;
}


function select_and_rename_roi(label, new_name) {
    /* Select the ROI whose name matches the given label and rename it.

    Parameters
    ----------
    label : int
        The label to look for in the list of ROIs. ROI names from the ROI
        Manager will be parsed to integers and compared to this value. All ROIs
        with non-numeric names (i.e. strings) will therefore be ignored as the
        parseInt() call will return 'NaN' on them.
    new_name : str
        The new name for the matching ROI.

    Returns
    -------
    bool
        True in case a ROI with a matching name was found (which will also be
        the selected one then), false otherwise.
    */
	for (i=0; i < roiManager("count"); i++) {
		roiManager("select", i);
		cur_label = parseInt(Roi.getName);
		if (cur_label == label) {
			// print("Renaming ROI '" + Roi.getName + "' to '" + new_name + "'");
			roiManager("rename", new_name);
			return true;
		}
	}
    print("WARNING: unable to find ROI for label " + label);
    return false;
}


function select_next_unprocessed_roi() {
    /* Select the top- and leftmost ROI whose name doesn't start with "tst-".

    Scans through all ROIs in the ROI Manager, checking if their name is
    starting with the specific "tst-" prefix. If not, the X/Y coordinates of the
    ROI are summed up and compared to the current minimum (the euklidean
    distance would be more precise, but since we have only rectangular ROIs
    arranged in a more or less non-overlapping fashion, this does the job and is
    much simpler). After all ROIs have been processed, the one with the smallest
    value is selected (which corresponds to the one closest to 0/0).

    Returns
    -------
    bool
        True in case any ROI without the specific prefix was found (which will
        also be the selected one then), false otherwise.
    */
    getDimensions(imgsizex, imgsizey, _, _, _);
	topleftdist = imgsizex + imgsizey;
	selected = -1;

	for (i=0; i < roiManager("count"); i++) {
		roiManager("select", i);
		cur_name = Roi.getName;
		if (!startsWith(cur_name, "tst-")) {
			Roi.getBounds(x, y, _, _);
            // Pythagoras would be more precise, but the sum does the job here:
            if (topleftdist > x+y) {
				topleftdist = x+y;
				selected = i;
			}
		}
	}
	if (selected == -1) {
		return false;
	}
	roiManager("select", selected);
	return true;
}

// print("\\Clear");

selectImage(tst_slide);
title_slide = getTitle();
print("Using image (" + tst_slide + ") as slide image: " + title_slide);

selectImage(tst_labels);
title_labels = getTitle();
print("Using image (" + tst_labels + ") as label image: " + title_labels);
// remove any calibration from the label image:
run("Properties...", "unit=pixel pixel_width=1 pixel_height=1 voxel_depth=1");
getDimensions(_, img_height, _, _, _);

label_order = newArray(roiManager("count"));

// start off with the first ROI:
i = 0;
roiManager("select", i);
val = parseInt(Roi.getName);
if (isNaN(val)) {
	exit("Unable to parse value of first label: " + Roi.getName);
}
// print("First label value: " + val);
label_order[i] = val;
select_and_rename_roi(val, "tst-" + lpad(i, 5));

unprocessed = true;
while (unprocessed) {
	Roi.getBounds(x, y, xsize, ysize);
	cx = floor(x + (xsize/2));
	cy = floor(y + (ysize/2));
	// print("roi:" + Roi.getName + " x:" + cx + " y:" + cy + " val:" + val);

	// now scan downwards from the ROI center for the next label:
	label_found = false;
	for (sy=cy; sy<=img_height; sy++) {
		val = getPixel(cx, sy);
		if ((val != label_order[i]) && (val > 0)) {
			// print("New label found: " + val);
            label_found = true;
			i++;
			label_order[i] = val;
            ret = select_and_rename_roi(val, "tst-" + lpad(i, 5));
            if (!ret) {
                exit("Unable to find a ROI matching label: " + val);
            }
			// exit the for-loop by breaking the condition:
			sy = img_height + 1;
		}
	}

    // only if no label was found (i.e. the cursor reached the image boundaries
    // while scanning) we need to call select_next_unprocessed_roi(), otherwise
    // the next ROI is already selected from the steps above!
	if (!label_found) {
        // Array.print(label_order);
        unprocessed = select_next_unprocessed_roi();
	}
}
print("All ROIs processed. New order (label values):");
Array.print(label_order);

roiManager("deselect");
roiManager("sort");

selectImage(tst_slide);
roiManager("show all with labels");

selectImage(tst_labels);
roiManager("show all with labels");
