/*
 * Macro to split a 2ch image and remove the background of the second
 * channel by blurring it with a large gaussian kernel (10% of the
 * average X/Y dimension) and subtracting the result from the original
 * channel data.
 */

function usage_exit() {
	exit("This macro requires EXACTLY ONE image stack (2ch) to be opened!");
}

if (nImages != 1) usage_exit();

getDimensions(width, height, channels, slices, frames);
if (channels != 2) usage_exit();

setBatchMode(true);

imgname = getTitle();
run("Split Channels");
c1 = "C1-" + imgname;
c2 = "C2-" + imgname;

selectImage(c2);
run("Duplicate...", "duplicate");

// use a kernel size of 10% of the average dimensions:
sigma = (width + height) / 20;
run("Gaussian Blur...", "sigma=" + sigma + " stack");
rename("bg");
selectWindow("bg");

// subtract the blurred stack from the original one:
imageCalculator("Subtract create stack", c2, "bg");
rename("C2-Background-Removed");

selectWindow("bg");
close();

// using "exit & display" will show all existing windows instead
// of just the last active one:
setBatchMode("exit & display");
