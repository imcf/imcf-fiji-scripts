#@ String(visibility=MESSAGE,persist=false,label="Heatmap Generator",value="") msg_header
#@ Integer(label="Box Width",min=8,max=256,value=32,style="slider") bwidth
#@ Integer(label="Box Height",min=8,max=256,value=32,style="slider") bheight
#@ LogService log

"""Region based average intensities calculation.

Create region based (rectangles) intensity heat-maps
for single-channel images.
"""

from ij import WindowManager
from ij.plugin import Duplicator
from ij.gui import GenericDialog


def rect_avg(proc, start_x, start_y, delta_x, delta_y):
    """Calculate average intensity of a rectangular area.

    Parameters
    ----------
    proc : ImageProcessor
    start_x, start_y : int
        The starting coordinates of the rectangle.
    delta_x, delta_y : int
        The width and height of the rectangle.

    Returns
    -------
    avg : int
        The average intensity.
    """
    bsum = 0
    for y in range(start_y, start_y + delta_y):
        for x in range(start_x, start_x + delta_x):
            bsum += proc.getPixel(x, y)
            # print "[%d, %d] = %d" % (x, y, proc.getPixel(x, y))
    avg = bsum / (delta_x * delta_y)
    return avg


def rect_set(proc, start_x, start_y, delta_x, delta_y, val):
    """Paint a rectangular area with a given value.

    Parameters
    ----------
    proc : ImageProcessor
    start_x, start_y : int
        The starting coordinates of the rectangle.
    delta_x, delta_y : int
        The width and height of the rectangle.
    val : int
        The value to use for painting.
    """
    # having 6 instead of 5 arguments is acceptable here:
    # pylint: disable-msg=R0913
    for y in range(start_y, start_y + delta_y):
        for x in range(start_x, start_x + delta_x):
            proc.putPixel(x, y, val)


def get_options():
    """Ask user for input values."""
    dlg = GenericDialog("Options for Boxed Heatmap")
    dlg.addMessage("Boxed Heatmap settings")
    dlg.addMessage("Specify box size:")
    dlg.addNumericField("Width", 32, 0)
    dlg.addNumericField("Height", 32, 0)
    dlg.showDialog()
    if dlg.wasCanceled():
        print "User canceled dialog."
        return  None
    # Read out the options
    boxw = int(dlg.getNextNumber())
    boxh = int(dlg.getNextNumber())
    return boxw, boxh


def boxed_intensities(imp1, width, height):
    """Create a new image with averaged intensity regions.

    Parameters
    ----------
    imp1 : ImagePlus
    width, height : int
        The width and height of the rectangles.

    Returns
    -------
    imp2 : ImagePlus
        The resulting ImagePlus, same dimensions as imp1.
    """
    imp2 = Duplicator().run(imp1)
    imp2.setTitle('heatmap-' + imp1.getTitle())

    imw = imp1.getWidth()
    imh = imp1.getHeight()

    ip1 = imp1.getProcessor()
    ip2 = imp2.getProcessor()

    if (imw % width + imh % height) > 0:
        msg = "WARNING: image size (%dx%d) not dividable by box (%dx%d)!"
        log.warn(msg % (imw, imh, width, height))

    for box_y in range(0, imh / height):
        start_y = box_y * height
        for box_x in range(0, imw / width):
            start_x = box_x * width
            # print "%d %d" % (start_x, start_y)
            bavg = rect_avg(ip1, start_x, start_y, width, height)
            # print bavg
            rect_set(ip2, start_x, start_y, width, height, bavg)

    return imp2


img_cur = WindowManager.getCurrentImage()
img_new = boxed_intensities(img_cur, bwidth, bheight)
img_new.show()
