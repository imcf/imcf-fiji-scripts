/*
#@ String (visibility=MESSAGE,label="Prerequisites:",value="a multi-Z Hyperstack with a line-selection.",persist=false) msg
#@ Boolean (label="Keep original stack?",default=true) keep_orig
#@ ImagePlus tst_stack
*/

selectImage(tst_stack);
title_orig = getTitle();

setBatchMode(true);

Stack.getPosition(_, cur_z, _);
getDimensions(sizex, sizey, channels, slices, _);
if (cur_z == 1) {
	exitmsg = "Current Z-position must be greater than 1!";
	print(exitmsg);
	exit(exitmsg);
}
upper = "1-" + (cur_z-1);
lower = "" + cur_z + "-" + slices;

if (selectionType() != 5) {
	exitmsg = "Straight line selection required!";
	print(exitmsg);
	exit(exitmsg);
}

print("Splitting into substacks: " + upper + " and " + lower);

// selection is a straight line (type "5", as checked above), so the x and y
// coordinates will be arrays with two entries each:
getSelectionCoordinates(xpoints, ypoints);
xdelta = xpoints[0] - xpoints[1];
ydelta = ypoints[0] - ypoints[1];
// print("delta: x=" + xdelta + " y=" + ydelta);

run("Make Substack...", "channels=1-" + channels + " slices=" + upper);
imp_upper = getImageID();
title_up = "tst-substack-upper";
rename(title_up);

selectImage(tst_stack);
run("Make Substack...", "channels=1-" + channels + " slices=" + lower);
imp_lower = getImageID();
title_lo = "tst-substack-lower";
rename(title_lo);

sizex_new = sizex + abs(xdelta);
sizey_new = sizey + abs(ydelta);
xcrop = abs(xdelta);
ycrop = abs(ydelta);
xpos_lower = "Left";
if (xdelta > 0) {
	xpos_lower = "Right";
	xcrop = 0;
}
ypos_lower = "Top";
if (ydelta > 0) {
	ypos_lower = "Bottom";
	ycrop = 0;
}
pos = ypos_lower + "-" + xpos_lower;
print("Shifting lower stack to the " + pos + " (" + xdelta + "/" + ydelta + ")");
run("Canvas Size...", "width=" + sizex_new + " height=" + sizey_new + " position=" + pos + " zero");
makeRectangle(xcrop, ycrop, sizex, sizey);
run("Crop");
run("Concatenate...", "  title=" + title_orig + " open image1=" + title_up + " image2=" + title_lo);
tst_stack_shifted = getImageID();

selectImage(tst_stack);
if (keep_orig) {
	rename("PRE-SHIFTED__" + getTitle());
} else {
	close();
}

selectImage(tst_stack_shifted);

setBatchMode("exit and display");

print("tst:hyperstack-shifted:id:" + tst_stack_shifted);
print("\n\n--- Shift Substack COMPLETED ---\n\n");
