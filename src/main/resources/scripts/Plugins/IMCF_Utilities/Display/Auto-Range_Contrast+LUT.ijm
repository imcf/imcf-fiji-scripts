// use a channel order more common to microscopy images:
LUTs = newArray("Blue", "Green", "Red", "Cyan", "Magenta", "Yellow");

getDimensions(width, height, channels, slices, frames);

// go to the "central" slice in case this is a stack:
if (slices > 2) {
	Stack.setSlice((slices+1)/2);
}

// now enhance the contrast and set the LUT for every channel:
for (c=1; c<=channels; c++) {
    if (channels > 1) {
        Stack.setChannel(c);
        run(LUTs[c-1]);
    }
    run("Enhance Contrast", "saturated=0.35");
}

if (channels > 1) {
    // in case of multi-channel, switch to composite display mode:
    Stack.setDisplayMode("composite");
    // and jump back to the first channel:
    Stack.setChannel(1);
}
