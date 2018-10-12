importClass(Packages.ij.IJ);
importClass(Packages.ij.gui.GenericDialog);
importClass(Packages.ij.io.SaveDialog);
importClass(Packages.ij.io.DirectoryChooser);
importClass(Packages.ij.plugin.filter.ParticleAnalyzer);
importClass(Packages.ij.measure.ResultsTable);
importClass(Packages.ij.measure.Measurements);
importClass(Packages.java.lang.Double);
importClass(Packages.java.io.File);


pixelsize = 0.170;
ltm = 'Phansalkar';  // local thresholding method
// methods from https://github.com/fiji/Auto_Threshold/blob/master/src/main/java/fiji/threshold/Auto_Local_Threshold.java
ltm_all = ["Bernsen", "Contrast", "Mean", "Median", "MidGrey",
           "Niblack", "Otsu", "Phansalkar", "Sauvola"];
radius = 30;
erosion = 5;
smin = 1;
smax = 0;
cmin = 0.00;
cmax = 1.00;

gd = new GenericDialog("Oil Red O Segmentation");
gd.addNumericField("Calibration: pixel size in µm", pixelsize, 3);
gd.setInsets(20, 0, 5);
gd.addChoice("Select the Local Thresholding Method:", ltm_all, ltm);
gd.addNumericField("Local Thresholding Radius: ", radius, 0);
gd.setInsets(20, 0, 3);
gd.addNumericField("Watershed erosion: ", erosion, 2);
gd.setInsets(20, 0, 3);
// TODO: we could use a slider by calculating the max possible
// size using the pixel size and the calibration values
// gd.addSlider("Size min:", 0, 999999999, smin);
gd.addNumericField("Size min: ", smin, 2);
gd.addNumericField("Size max (0 for Infinity): ", smax, 2);
gd.addNumericField("Circularity min: ", cmin, 2);
gd.addNumericField("Circularity max: ", cmax, 2);
gd.showDialog();

//res = gd.getNumericFields();
pixelsize = gd.getNextNumber();
radius = gd.getNextNumber();
erosion = gd.getNextNumber();
smin = gd.getNextNumber();
smax = gd.getNextNumber();
cmin = gd.getNextNumber();
cmax = gd.getNextNumber();

// if (! (gd.wasCanceled())) process();
if (! (gd.wasCanceled())) {
    dc = DirectoryChooser('Directory with input files (.tif)');
    if (dc.getDirectory()) {
        process_directory(dc.getDirectory());
    }
}

function process_directory(dirname) {
    print(dirname);
    var filelist = File(dirname).list();
    for (var i = 0; i < filelist.length; i++) {
        var file = filelist[i];
        if (file.toUpperCase().endsWith('TIF') ||
            file.toUpperCase().endsWith('TIFF')) {
            print(file);
            process_file(dirname, file);
        }
    }
}

function process_file(dir, file) {
	// imp = IJ.getImage();
    imp = IJ.openImage(dir + file);

	IJ.run(imp, "Properties...", "unit=um pixel_width=" + pixelsize +
		" pixel_height=" + pixelsize);
	IJ.run(imp, "8-bit", "");
	IJ.run(imp, "Auto Local Threshold", "method=" + ltm +
		" radius=" + radius + " parameter_1=0 parameter_2=0");
	//IJ.run(imp, "Watershed", "");
	IJ.run(imp, "Watershed Irregular Features", "erosion=" + erosion);
	if (smax == 0) smax = Double.POSITIVE_INFINITY;
	set_measurements =
		Measurements.AREA +
		Measurements.CENTER_OF_MASS +
		Measurements.SHAPE_DESCRIPTORS +
		Measurements.INTEGRATED_DENSITY;
	rt = new ResultsTable();
	// ParticleAnalyzer(int options, int measurements, ResultsTable rt,
	//     double minSize, double maxSize, double minCirc, double maxCirc)
	pa = new ParticleAnalyzer(ParticleAnalyzer.ADD_TO_MANAGER,
		set_measurements, rt, smin, smax, cmin, cmax);
	pa.setHideOutputImage(true);
	pa.analyze(imp);
	rt.show("Oil Red O measurements");
    /*
	sd = new SaveDialog('Save measurement results as...', imp.shortTitle + "_results", ".csv");
	fout = sd.getFileName();
	if (fout == null) return;
	fout = sd.getDirectory() + fout;
    */
    fout = dir + imp.shortTitle + "_results.csv";
	rt.saveAs(fout);

    print(imp.getShortTitle());
    imp.close();
}
