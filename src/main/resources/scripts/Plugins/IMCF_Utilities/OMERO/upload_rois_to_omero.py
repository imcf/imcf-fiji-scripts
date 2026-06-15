# @ String(label="Username", description="please enter your username") USERNAME
# @ String(label="Password", description="please enter your password", style="password") PASSWORD
# @ ImagePlus imp
# @ RoiManager rm

# ─── Imports ──────────────────────────────────────────────────────────────────

import os
from ij import IJ, WindowManager as wm

from java.lang import Long

from imcflibs.imagej import omerotools

from fr.igred.omero import Client
from fr.igred.omero.roi import ROIWrapper

# ─── Functions ────────────────────────────────────────────────────────────────

# ─── Variables ────────────────────────────────────────────────────────────────

# OMERO server info
HOST = "omero.biozentrum.unibas.ch"
PORT = 4064
# datasetId = datasetid
groupId = "-1"

# ─── Main Code ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    try:
        user_client = Client()
        user_client.connect(HOST, PORT, USERNAME, PASSWORD)

        if rm.getCount() == 0:
            roi = imp.getRoi()
            if roi is not None:
                rm.addRoi(roi)
            else:
                IJ.log("No ROIs found in the image or ROI Manager.")
                exit()

        # Get the OMERO ID
        title = imp.getTitle()
        omero_id = title.split("_")[-1]

        image_wpr = user_client.getImage(Long(omero_id))
        omerotools.save_rois_to_omero(user_client, image_wpr, rm)

    finally:
        user_client.disconnect()

    IJ.log("ROIs have been saved to OMERO")



