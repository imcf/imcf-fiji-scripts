/*
#@ String (visibility=MESSAGE,label="Slide Combiner",value="Horizontally combine two slide images (stacks).",persist=false) msg
#@ ImagePlus(label="1st slide") imp_left
#@ ImagePlus(label="2nd slide") imp_right
*/

if (imp_left == imp_right) {
	exit("Please select two different images!");
}

print("\\Clear");
selectImage(imp_left);
title1 = getTitle();
rename("tst-left");
getDimensions(_, height1, _, _, _);
// print(title + " - " + height1);

selectImage(imp_right);
getDimensions(_, height2, _, _, _);
title2 = getTitle();
rename("tst-right");
// print(title + " - " + height2);

if (height1 > height2) {
	selectImage(imp_right);
	run("Canvas Size...", "height=" + height1 + " position=Top-Left zero");
} else {
	selectImage(imp_left);
	run("Canvas Size...", "height=" + height2 + " position=Top-Left zero");
}

run("Combine...", "stack1=tst-left stack2=tst-right");
rename(title1 + "--" + title2);
tst_slide = getImageID();

print("tst:combined-slides:id:" + tst_slide);
print("\n\n--- Combine Slides COMPLETED ---\n\n");
