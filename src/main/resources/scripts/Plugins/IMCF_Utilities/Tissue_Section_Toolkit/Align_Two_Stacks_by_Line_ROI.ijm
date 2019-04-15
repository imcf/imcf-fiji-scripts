/*
#@ ImagePlus (label="Reference Image",description="will be kept as-is") imp_ref
#@ ImagePlus (label="Image to be aligned",description="will be aligned to reference image") imp_toalign
*/

function getAngle(x1, y1, x2, y2) {
    /*
     * Calculate the angle (ccw) of the given line against the x-axis.
     *
     * Origin: https://imagej.nih.gov/ij/macros/Measure_Angle_And_Length.txt
     */
    q1 = 0; q2orq3 = 2; q4 = 3; //quadrant
    dx = x2 - x1;
    dy = y1 - y2;
    if (dx != 0)
        angle = atan(dy / dx);
    else {
        if (dy >= 0)
            angle = PI / 2;
        else
            angle = -PI / 2;
    }
    angle = (180 / PI) * angle;
    if (dx >= 0 && dy >= 0)
        quadrant = q1;
    else if (dx < 0)
        quadrant = q2orq3;
    else
        quadrant = q4;
    if (quadrant == q2orq3)
        angle = angle + 180.0;
    else if (quadrant == q4)
        angle = angle + 360.0;
    return angle;
}


function getStraightLineAngle() {
    getSelectionCoordinates(xpoints, ypoints);
    angle = getAngle(xpoints[0], ypoints[0], xpoints[1], ypoints[1]);
    return angle;
}


function getStraightLineCenter() {
    center = newArray(2);
    getSelectionCoordinates(xpoints, ypoints);
    xdelta = xpoints[0] - xpoints[1];
    ydelta = ypoints[0] - ypoints[1];
    center[0] = floor(xpoints[0] + (xdelta/2));
    center[1] = floor(ypoints[0] + (ydelta/2));
    return center;
}


selectImage(imp_ref);
angle_ref = getStraightLineAngle();
center_ref = getStraightLineCenter();

selectImage(imp_toalign);
angle_toalign = getStraightLineAngle();
center_toalign = getStraightLineCenter();

angle_delta = angle_toalign - angle_ref;
print("Angle delta: " + angle_delta);
print("Offset:" +
      " x=" + (center_ref[0] - center_toalign[0]) +
      " y=" + (center_ref[1] - center_toalign[1]));

// rotate the image (note the space after the dots!):
run("Rotate... ", "angle=" + angle_delta + " interpolation=Bilinear");
// rotate the selection:
run("Rotate...", "  angle=" + angle_delta);

center_aligned = getStraightLineCenter();
getDimensions(sizex_aligned, sizey_aligned, _, _, _);
selectImage(imp_ref);
getDimensions(sizex_ref, sizey_ref, _, _, _);
