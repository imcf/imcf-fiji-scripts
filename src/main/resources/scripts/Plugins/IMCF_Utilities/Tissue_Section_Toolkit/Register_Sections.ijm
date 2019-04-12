/*
#@ String (visibility=MESSAGE,label="Prerequisites:",value="a multi-channel, multi-Z Hyperstack.",persist=false) msg
#@ String (label="Registration channel(s):",description="separated by commas") hsr_ch
#@ ImagePlus tst_stack
*/

selectImage(tst_stack);

param = "";
channels = split(hsr_ch, ",");
for (i=0; i<channels.length; i++) {
	param += " channel" + channels[i];
}
print("Running HyperStackReg on:" + param);

selectImage(tst_stack);
run("Re-order Hyperstack ...", "channels=[Channels (c)] slices=[Frames (t)] frames=[Slices (z)]");
t0 = getTime();
run("HyperStackReg", "transformation=[Rigid Body] " + param + " show");
print("HyperStackReg took about " + floor((getTime() - t0) / 1000) + " seconds");
tst_stack_registered = getImageID();

selectImage(tst_stack);
run("Re-order Hyperstack ...", "channels=[Channels (c)] slices=[Frames (t)] frames=[Slices (z)]");
rename("NON-REGISTERED STACK");
selectImage(tst_stack_registered);
run("Re-order Hyperstack ...", "channels=[Channels (c)] slices=[Frames (t)] frames=[Slices (z)]");
