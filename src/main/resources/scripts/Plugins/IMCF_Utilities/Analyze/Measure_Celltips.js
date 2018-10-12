/* TODO:
 *  - replace IJ.run / rm.runCommand by proper code
 */

importClass(Packages.ij.IJ);
importClass(Packages.ij.Prefs);
importClass(Packages.ij.WindowManager);
importClass(Packages.ij.io.SaveDialog);
importClass(Packages.ij.plugin.ImageCalculator);
importClass(Packages.ij.plugin.ChannelSplitter);
importClass(Packages.ij.plugin.frame.RoiManager);
importClass(Packages.ij.plugin.filter.ParticleAnalyzer);
importClass(Packages.ij.measure.ResultsTable);
importClass(Packages.ij.measure.Measurements);


imp = IJ.getImage();
name = imp.title;
z_slice = imp.z;  // remember the z-position


cs = new ChannelSplitter();
channels = cs.split(imp);
// we need to show the channels to make the "Measure" command work,
// if we replace it by proper code this is probably not required:
channels[1].show();
channels[2].show();

ic = new ImageCalculator();
imp_combined = ic.run("Add create stack", channels[1], channels[2]);
imp_combined.show();
imp_combined.setZ(z_slice);

IJ.run(imp_combined, "Median...", "radius=1.3 stack");
Prefs.blackBackground = true;
IJ.setAutoThreshold(imp_combined, "IJ_IsoData dark");
IJ.run(imp_combined, "Convert to Mask", "method=IJ_IsoData background=Dark black");


IJ.run("Set Measurements...", "area mean min center integrated redirect=None decimal=0");
IJ.run(imp_combined, "Analyze Particles...", "size=25-Infinity pixel exclude clear include add slice");

// prepare the ROI Manager
rm = RoiManager.getInstance();
if (rm==null) rm = new RoiManager();


function measure_save(imp) {
	WindowManager.setCurrentWindow(imp.getWindow())
	rm.runCommand("Measure");
	rt = ResultsTable.getResultsTable();
	rtw = ResultsTable.getResultsWindow();
	rtw.rename('Results ' + imp.shortTitle);
	
	sd = new SaveDialog('Save measurement results as...',
		imp.shortTitle + "_z" + z_slice + "_results", ".csv");
	fout = sd.getFileName();
	if (fout != null) {
		fout = sd.getDirectory() + fout;
		rt.saveAs(fout);
	}
}

measure_save(channels[1]);
measure_save(channels[2]);
