/*
#@ String (visibility=MESSAGE,label="Prerequisites:",value="a multi-Z Hyperstack with a line-selection.",persist=false) msg
#@ Boolean (label="Keep original stack?",default=true) keep_orig
#@ ImagePlus tst_stack
*/

/*
This macro is expecting a Hyperstack with >=2 z-slices and a straight line
selection. It will split the stack at the current slice (where the current slice
will belong to the second substack, which also requires it to be at least at
z-position "2") and shift the second substack (translation only) by the distance
defined through the line selection.
The idea is to allow the user to correct for "jumps" in the stack alignment by
interactively going to the "last good" z-slice, drawing a line starting at any
preferred landmark (line-end position doesn't matter), then switching to the
next slice, adjusting the end of the line to match the corresponding location
of that landmark on this slice. Running the macro will then shift the "lower"
part of the stack in X/Y by the distance defined through the line's end points.
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
	Stack.setSlice(cur_z);
} else {
	close();
}

selectImage(tst_stack_shifted);
Stack.setSlice(cur_z);

setBatchMode("exit and display");

print("tst:hyperstack-shifted:id:" + tst_stack_shifted);
print("\n\n--- Shift Substack COMPLETED ---\n\n");
