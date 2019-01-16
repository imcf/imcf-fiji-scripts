/*
 * ImageJ macro to automate a 2 channel intensity measuring workflow.
 *
 * Requires at least 2 open images, asks the user in a dialog to assign one
 * image as the "red" and one as the "green" channel, select the desired
 * thresholding method and the filtering values for size and circularity that
 * are passed to "Analyze Particles" later.
 *
 * The "red" channel is then used to create a mask by the chosen thresholding
 * method, fill holes and watershed are run and "Analyze Particles" is used
 * with the given values to create ROI's and add them to the ROI Manager.
 *
 * Finally, the ROI's are used to measure area, mean and min intensity in both
 * input channels, creating separate result tables for each channel.
 */


if (nImages < 2) {
    msg = "Requires at least 2 open images.";
    showMessage("Error", msg);
    exit;
}

// assemble an array containing the currently open images:
// print("number of images: " + nImages);
setBatchMode(true);
names = newArray(nImages);
for (i=0; i < nImages; i++){
    selectImage(i+1);
    names[i] = getTitle();
    // print(names[i]);
}
// sort the names array so we can try to pre-assign the correct
// channels (given the files are named in a sensible way)
Array.sort(names);
setBatchMode(false);

// ***** USER INPUT DIALOG ***** //
Dialog.create("Thresholded Measurements / 2Ch, single slices");
msg = "Assign images to channels:";
Dialog.addMessage(msg);
Dialog.addChoice("RED channel:", names, names[0]);
Dialog.addChoice("GREEN channel:", names, names[1]);
// threshold method selection
methods = getList("threshold.methods");
Dialog.addChoice("threshold method:", methods, "RenyiEntropy");
Dialog.addNumber("size min: ", 100);
Dialog.addNumber("size max (0 for infinity): ", 0);
Dialog.addSlider("circularity min:", 0, 1, 0.5);
Dialog.addSlider("circularity max:", 0, 1, 1);
Dialog.addNumber("decimal places:", 0);
Dialog.show();


ch_red = Dialog.getChoice();
ch_grn = Dialog.getChoice();
thr_method = Dialog.getChoice();
size_min = Dialog.getNumber();
size_max = Dialog.getNumber();
if(size_max == 0)
    size_max = "Infinity";
circ_min = Dialog.getNumber();
circ_max = Dialog.getNumber();
decimal = Dialog.getNumber();
// ***** USER INPUT DIALOG ***** //

/*
print(ch_red);
print(ch_grn);
print(size_min);
print(size_max);
print(circ_min);
print(circ_max);
*/

setBatchMode(true);
// make sure the ROI Manager is empty
roiManager("reset");
// make sure nothing is selected
run("Select None");


// duplicate the red channel to create the mask
selectImage(ch_red);
run("Duplicate...", "title=masking_channel");
selectImage("masking_channel");
setAutoThreshold(thr_method + " dark");
// setOption("BlackBackground", false);
run("Convert to Mask");
run("Fill Holes");
run("Watershed");
run("Analyze Particles...",
    "size=" + size_min + "-" + size_max + " pixel"
    + " circularity=" + circ_min + "-" + circ_max
    + " show=Nothing exclude clear add");
// close(); // not required in batch mode

for(i=0; i<2; i++) {
    selectImage(names[i]);
    // workaround to make sure correct ROI's are active on this image:
    roiManager("Show None");
    roiManager("Show All");
    run("Set Measurements...", "area mean min "
        + " redirect=" + names[i]
        + " decimal=" + decimal);
    roiManager("Measure");
    // the select command is required, otherwise IJ renames the first
    // "Results" window again on the second iteration - bug?
    selectWindow("Results");
    IJ.renameResults("Results-" + names[i]);
}


setBatchMode(false);
