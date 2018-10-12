// example macro demonstrating how to launch the OIF/OIB/OIR stitcher
// with predefined parameters / inputs (can be launched from the command line
// using `ImageJ-linux64 --run run_oir_stitcher.ijm` or similar):

opts =  "";
opts += "msg_header=[none],";
opts += "infile=[/data/sample_data/fluoview/oir__two-polygon-rois/matl.omp2info],";
opts += "msg_sec_stitching=[none],";
opts += "stitch_register=[false],";
opts += "stitch_regression=[0.3],";
opts += "stitch_maxavg_ratio=[2.5],";
opts += "stitch_abs_displace=[3.5]";
opts += "msg_sec_output=[none],";
opts += "angle=[0],";
opts += "print_code=[false],";
opts += "msg_citation=[none],";

run("FluoView OIF OIB OIR Stitcher", opts);

print("FluoView OIF OIB OIR Stitcher options: " + opts);
