/*
#@ String (visibility=MESSAGE,label="Prerequisites:",value="Tissue section stack and a mask image.",persist=false) msg
#@ Integer (label="Box Padding",description="how many pixels to enlarge bounding boxes",default=10) padding

#@ ImagePlus (label="Slide image with tissue sections") tst_slide
#@ ImagePlus (label="Pre-segmentation mask image") tst_mask
*/


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
run("Analyze Particles...", "size=" + size + "-Infinity show=Nothing pixel add");

for (i=0; i < roiManager("count"); i++) {
	roiManager("select", i);
	Roi.getBounds(x, y, width, height);
	// print(x + " " + y + " " + width + " " + height);
	makeRectangle(x-padding, y-padding, width+padding*2, height+padding*2);
	roiManager("update");
}
roiManager("deselect");
roiManager("sort");
// close();

selectImage(tst_slide);
roiManager("show all with labels");
