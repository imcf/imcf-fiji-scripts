/*
 * ImageJ macro for Spang Lab segmentation, 2014-03.
 *
 * Asks the user in a dialog to select one image for processing, select the
 * desired thresholding method and the filtering values for size and
 * circularity that that are passed to "Analyze Particles" later.
 *
 * Segmentation is done using the CLAHE local contrast algorithm, then using a
 * local thresholding, some tweaks on the binary mask (fill holes, open) and
 * finally applying the standard watershed method.
 *
 * The result is measured via "Analyze Particles" and displayed on the input
 * image for visual control
 */

infile = File.openDialog("Select a ZVI file");
// exit cleanly if the user clicks on cancel:
if (infile == '') {
    exit;
}
run("Bio-Formats Importer", "open=&infile " +
	"autoscale color_mode=Colorized view=Hyperstack stack_order=XYCZT");
getDimensions(sizeX, sizeY, sizeC, sizeS, sizeF);
orig_image = getTitle();
if (sizeC != 3) {
    msg = "This dataset has " + sizeC + " channels, whereas a 3-channel" +
        " dataset was expected! Stopping.";
    showMessage("Error", msg);
    exit;
}

// ***** USER INPUT DIALOG ***** //
Dialog.create("Cells segmentation parameters");
//Dialog.addMessage(msg);
channels = newArray("1", "2", "3");
Dialog.addChoice("Select channel to use for SEGMENTATION:", channels, "2");
Dialog.addNumber("CLAHE slope maximum: ", 2);
// threshold method selection (FIXME: complete the list!)
methods = newArray('Phansalkar', 'Niblack', 'Otsu', 'Mean', 'Median');
Dialog.addChoice("Local Thresholding method:", methods, "Phansalkar");
Dialog.addSlider("Local Thresholding radius:", 5, 100, 50);
Dialog.addNumber("Object size minimum: ", 50);
Dialog.addNumber("Object size maximum (0 for infinity): ", 0);
Dialog.addSlider("Circularity minimum:", 0, 0.99, 0.0);
Dialog.addSlider("Circularity maximum:", 0.1, 1, 1);
Dialog.show();


ch_segm = parseInt(Dialog.getChoice());
clahe_max = Dialog.getNumber();
thr_method = Dialog.getChoice();
thr_radius = Dialog.getNumber();
size_min = Dialog.getNumber();
size_max = Dialog.getNumber();
if(size_max == 0)
    size_max = "Infinity";
circ_min = Dialog.getNumber();
circ_max = Dialog.getNumber();
// ***** USER INPUT DIALOG ***** //

setBatchMode(true);
// make sure the ROI Manager is empty
roiManager("reset");
// make sure nothing is selected
run("Select None");

selectImage(orig_image);
Stack.setChannel(ch_segm);
// duplicate the red channel to create the mask
run("Duplicate...", "title=masking_channel duplicate channels=&ch_segm");
selectImage("masking_channel");
//run("Enhance Contrast", "saturated=5.0");
run("Enhance Local Contrast (CLAHE)",
	"blocksize=127 histogram=256 maximum=&clahe_max "
	+ "mask=*None* fast_(less_accurate)");
run("8-bit");  // local threshold only works on 8-bit images
run("Auto Local Threshold", "method=&thr_method radius=&thr_radius "
    + "parameter_1=0 parameter_2=0 white");
// setOption("BlackBackground", false);
run("Convert to Mask");
run("Fill Holes");
run("Open");
run("Watershed");
setBatchMode(false);
run("Analyze Particles...",
    "size=&size_min-&size_max pixel circularity=&circ_min-&circ_max"
    + " show=Nothing exclude clear add");
selectImage("masking_channel");
close(); // not required in batch mode

setBatchMode(false);

selectImage(orig_image);
setSlice(2); // make sure to have the correct channel for measuring
roiManager("Show All");

run("ROI Manager...");
run("Set Measurements...", "area mean min center redirect=None decimal=0");
roiManager("Measure");

