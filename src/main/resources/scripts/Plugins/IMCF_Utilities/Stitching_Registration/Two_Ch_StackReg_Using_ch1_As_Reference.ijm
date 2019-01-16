/*
 * Macro to run MultiStackReg on a 2ch image, using the
 * first channel as the reference. For some unknown reason
 * (bug?) this can't be done in one pass, but the transformation
 * coordinates have to be saved inbetween and re-used for the
 * other channel.
 * 
 * Requires the MultiStackReg plugin available here:
 * http://bradbusse.net/downloads.html
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

getDateAndTime(year, month, dayOfWeek, dayOfMonth,
	hour, minute, second, msec);
tmpfile  = getDirectory("temp");
tmpfile += "multistackreg-" + year + "-" + month + "-" + dayOfMonth +
	"_" + hour + "-" + minute + "-" + second + ".txt";
run("MultiStackReg", "stack_1=" + c1
	+ " action_1=Align"
	+ " file_1=[" + tmpfile + "]"
	+ " stack_2=None"
	+ " action_2=Ignore"
	+ " file_2=[]"
	+ " transformation=Translation save");

run("MultiStackReg", "stack_1=" + c2 +
	" action_1=[Load Transformation File]" +
	" file_1=[" + tmpfile + "]" +
	" stack_2=None" +
	" action_2=Ignore" +
	" file_2=[]" +
	" transformation=Translation");

run("Merge Channels...", "c1=" + c1 +
	" c2=" + c2 +
	" create");
Stack.setDisplayMode("grayscale");

setBatchMode(false);