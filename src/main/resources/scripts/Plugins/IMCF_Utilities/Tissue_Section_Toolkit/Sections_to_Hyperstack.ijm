/*
#@ File (label="First file of image sequence") imgf
#@ Integer (label="Number of Channels",min=1) nchannels
*/


function parse_filename_from_log() {
    pattern = "tst:padded-sections:firstfile:";
    msgs = split(getInfo("Log"), "\n");
    // search the log backwards for a line with the pattern defined above:
    for (i=(msgs.length-1); i>=0; i--) {
    	if (startsWith(msgs[i], pattern)) {
    		fname = replace(msgs[i], pattern, "");
    		return fname;
    	}
    }
	exit("Unable to find sequence filename in log messages!");
}

// sequence-loading, renaming etc. doesn't work in BatchMode, so disable it:
setBatchMode(false);

if (endsWith(imgf, "[tst-from-log]")) {
	imgf = parse_filename_from_log();
}

// generate a pseudo-random image title:
title = "img_sequence_" + floor(random() * 100000000);
print("Loading image sequence, starting with " + imgf);
run("Image Sequence...", "open=[" + imgf + "] sort");
rename(title);
run("Deinterleave", "how=" + nchannels);

merge = "";
for (i=1; i<=nchannels; i++) {
	merge += "c" + i + "=[" + title + " #" + i + "] ";
}
print(merge);
run("Merge Channels...", merge + "create ignore");

// normalize windows paths
imgf = replace(imgf, "\\", "/");
// strip directories and (last) dot-suffix
imgf = substring(imgf, lastIndexOf(imgf, "/")+1, lastIndexOf(imgf, "."));
// strip special suffix from crop+pad macro:
imgf = replace(imgf, "_roi-0", "");
rename(imgf);
