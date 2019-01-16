/*
 * ImageJ macro to stitch all .lsm files in a directory.
 *
 * Asks the user for an input directory containing the LSM files to be stitched
 * and an output directory for the results (can be the same) and runs Fiji's
 * "Grid/Collection stitching" plugin with fixed settings, using the stage
 * positions stored within the LSM files.
 *
 * NOTE: the macro assumes all LSM files belong to the same tiling acquisition.
 * For multiple tilings, put the corresponding files into separate directories!
 *
 * The stitching result is saved as plain TIFF (no OME!).
 */

function stitch_LSM_file(infile, outfile) {
	print("stitching file: " + infile);
	
	settings = "type=[Positions from file] " +
	"order=[Defined by image metadata] " +
	"browse=[" + infile + "] " +
	"multi_series_file=[" + infile + "] " +
	"fusion_method=[Linear Blending] " +
	"regression_threshold=0.30 " +
	"max/avg_displacement_threshold=2.50 " +
	"absolute_displacement_threshold=3.50 " +
	"compute_overlap " +
	"increase_overlap=0 " +
	"subpixel_accuracy " +
	"computation_parameters=[Save computation time (but use more RAM)] " +
	"image_output=[Fuse and display]";
	//print(settings);

	run("Grid/Collection stitching", settings);
	
	print("saving result as: " + outfile);
	saveAs("Tiff", outfile);
	close();
}

function process_files(indir, outdir) {
	list = getFileList(indir);
	for (i=0; i<list.length; i++) {
		if (endsWith(list[i], ".lsm")) {
			infile = indir + list[i];
			outfile = outdir + list[i];
			//print("infile: " + infile);
			stitch_LSM_file(infile, outfile);
		} else {
			print("skipping '" + list[i] +"'");
	}
}

setBatchMode(true);
indir = getDirectory("Directory containing input files");
outdir = getDirectory("Directory for saving stitched files");
//if (lengthOf(indir) > 0) print("selected input directory: " + indir);
//if (lengthOf(outdir) > 0) print("selected output directory: " + outdir);

count = 1;
process_files(indir, outdir); 

setBatchMode(false);
