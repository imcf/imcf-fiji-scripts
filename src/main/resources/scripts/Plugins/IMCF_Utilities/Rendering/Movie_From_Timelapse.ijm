/*
 * ImageJ macro to create a movie (MIP or single slice) from a timelapse-stack.
 *
 * Asks for a file, a step-size, whether to do a maximum intensity projection
 * or what slice to use otherwise, and a scaling factor. Then it opens the file
 * using the Bio-Formats reader and does the projection or selects the desired
 * slice, scales it, runs auto-contrast for each channel and finally stores the
 * RGB converted variant as a JPEG-compressed AVI movie.
 */

infile = File.openDialog("Select file");
// exit cleanly if the user clicks on cancel:
if (infile == '') {
    exit;
}

Dialog.create("Create overview movie options");
msg = "Choose a stepsize to use every N-th timeframe of the dataset.\n";
msg+= "(This can significantly speed up the file reading).";
Dialog.addMessage(msg);
Dialog.addNumber("stepsize:", 10);

msg = "Do a Z-projection (maximum intensity) for stacks?";
Dialog.addMessage(msg);
Dialog.addCheckbox("projection?", true);

msg = "Choose a scaling factor:";
Dialog.addMessage(msg);
Dialog.addNumber("scale:", 1);

Dialog.show;
stepping = Dialog.getNumber();
mip = Dialog.getCheckbox();
scale = Dialog.getNumber();

if (!mip) {
	msg = "Set slice number to use for the movie:";
	slice = getNumber(msg, 15);
} else {
	slice = 0;
}

mk_overview_movie(infile, stepping, mip, slice, scale);

function update_focus_close_old(title) {
    curfocus = getTitle();
    selectWindow(title);
    close();
    selectWindow(curfocus);
    return curfocus;
}

function mk_overview_movie(infile, stepping, mip, slice, scale) {
    // assemble the Bio-Formats options in advance as the string gets very long
    bf_options =  " color_mode=Composite specify_range stack_order=XYCZT";
    if (!mip) {
        bf_options += " z_begin=" + slice + " z_end=" + slice;
    }
    bf_options += " t_begin=1 t_step=" + stepping;
    // print(bf_options);
    setBatchMode(true);
    run("Bio-Formats Importer", "open=" + infile + bf_options);
    focused = getTitle();

    if (mip) {
        run("Z Project...", "projection=[Max Intensity] all");
        focused = update_focus_close_old(focused);
    }

    // "create" is required, otherwise "scale" adds black borders
    if (scale != 1) {
        scaleopts  = "x=" + scale + " y=" + scale;
        scaleopts += " interpolation=Bilinear average create";
        run("Scale...", scaleopts);
        focused = update_focus_close_old(focused);
    }
    getDimensions(im_width, im_height, im_channels, im_slices, im_frames);
    // channels numbers start with 1
    for (c=1; c<=im_channels; c++) {
        Stack.setChannel(c);
        run("Enhance Contrast", "saturated=0.35");
    }
    run("RGB Color", "frames");
    run("AVI... ", "compression=JPEG frame=5");
    // disable the close() call if the result should get displayed after the
    // macro terminates
    close();
    setBatchMode(false);
}
