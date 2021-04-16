/*
#@ String (visibility=MESSAGE,label="Prerequisites:",value="Tissue section stack and a mask image.",persist=false) msg
#@ Integer (label="Box Padding",description="how many pixels to enlarge bounding boxes",default=10) padding

#@ ImagePlus (label="Slide image with tissue sections") tst_slide
#@ ImagePlus (label="Pre-segmentation mask image") tst_mask
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


roiManager("reset");
run("Select None");

selectImage(tst_slide);
title_slide = getTitle();
print("Using image (" + tst_slide + ") as slide image: " + title_slide);

selectImage(tst_mask);
print("Using image (" + tst_mask + ") as mask image.");
getDimensions(width, height, _, _, _);

size = (width/15) * (height/10) / 4;
print("Minimum section size (in square pixels) estimated from image: " + size);
run("Analyze Particles...", "size=" + size + "-Infinity show=[Count Masks] pixel add");
tst_labels = getImageID();
rename("tst-sections-label-mask");
run("Enhance Contrast", "saturated=0.01");
run("glasbey on dark");


for (i=0; i < roiManager("count"); i++) {
    roiManager("select", i);
    // first rename the ROI using its value from the label image:
    Roi.getCoordinates(xpoints, ypoints);
    value = getPixel(xpoints[0], ypoints[0]);
    roiManager("rename", lpad(value, 5));

    // now replace the ROI by its bounding box, adding the padding requested:
    Roi.getBounds(x, y, width, height);
	// print(x + " " + y + " " + width + " " + height);
	makeRectangle(x-padding, y-padding, width+padding*2, height+padding*2);
	roiManager("update");
}

roiManager("sort");
// close();

/* do NOT close the mask image, we might have to go back to it!
selectImage(tst_mask);
close();
*/

selectImage(tst_labels);
roiManager("show all with labels");

print("tst:tissue-labels:id:" + tst_mask);
print("\n\n--- Masks To Segmentation COMPLETED ---\n\n");
