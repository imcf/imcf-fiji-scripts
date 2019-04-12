/*
#@ String (visibility=MESSAGE,label="Prerequisites:",value="Multi-channel image of cut sections or similar.",persist=false) msg
#@ String (label="Threshold Method",choices={"Minimum","Triangle","Intermodes","IsoData"}) method
#@ Integer (label="Mask Erosion",description="number of 'erode' steps during mask creation",default=5) erode_steps

#@ ImagePlus imp
*/

selectImage(imp);
title = getTitle();
print("Using image (" + imp + ") as slide image: " + title);
getDimensions(width, height, _, _, _);
run("Z Project...", "projection=[Sum Slices]");
id_sum = getImageID();
setAutoThreshold(method + " dark");
setOption("BlackBackground", true);
run("Convert to Mask");
resetThreshold();
rename("tissue-section-mask");

for (i=0; i < erode_steps; i++) {
	run("Erode");
}
run("Fill Holes");
tst_mask = getImageID();

print("tst:tissue-masks:id:" + tst_mask);
print("\n\n--- Create Tissue Masks COMPLETED ---\n\n");
