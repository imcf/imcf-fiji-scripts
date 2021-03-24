/*
 * Author: Laurent Guerard
 * Group: IMCF
 * Email: laurent.guerard@unibas.ch
 * Creation Date: Friday, 27th September 2019 3:32:35 pm
 * -----
 * Last Modified: Wednesday, 24th March 2021 12:10:13
 * Modified By: Laurent Guerard
 * -----
 * HISTORY:
 * Date         By  Comments
 * ------------ --- ---------------------------------------------------------
 * 2021-03-24	LG 	Fixed the output directory path
 * 2020-05-08   LG  Added log
 * 2019-09-27   LG  1st version. Working.
 */

// ImageJ script to make FRAP measurements from a timelapse image

// This script requires a 3D image to be opened (2D + time).
// It has the option to do registration in case the sample moved a bit. Once
// started, the script will ask for 3 ROIS (FRAP, whole cell, background) in the
// correct order and will measure the mean intensity in these 3 ROIs for all
// timepoints.
// Wil then save the result in a CSV which can be directly used in easyFRAP to
// have graphs and analysis.


import com.opencsv.CSVWriter
import ij.IJ
import ij.ImagePlus
import ij.plugin.Duplicator
import ij.plugin.frame.RoiManager
import ij.gui.WaitForUserDialog
import org.apache.commons.io.FilenameUtils

#@ Boolean(label="Do stack registration ?", value=true) do_stack
#@ ImagePlus imp

// Make a duplicate
imp_dup = new Duplicator().run(imp, 1, 1, 1, 1, 1, imp.getNFrames())

// Get info about the file
calibration = imp.getCalibration()
file_info = imp.getOriginalFileInfo()
basename = imp.getTitle()

if (file_info.directory == null)
	output_dir = System.properties.'user.home' + "/Desktop"
else
	output_dir = file_info.directory

// println(output_dir)

// Do stackreg if necessary
IJ.log("Starting registration")
if (do_stack)
    IJ.run(imp_dup, "StackReg", "transformation=[Rigid Body]")
IJ.log("Registration done")

// Build the ROI Manager
rm = RoiManager.getInstance()
if (rm == null)
    rm = new RoiManager()

// rm.reset()
rm.show()

// Wait for user window asking for the 3 ROIs
imp_dup.show()
new WaitForUserDialog("ROI Making", "Draw the 3 ROIs for FRAP, add them to the ROI Manager (press T on the keyboard) then click OK.\n" +
        "1st ROI: FRAP region\n" +
        "2nd ROI: whole cell region\n" +
        "3rd ROI: background").show();

nbr_ROI = rm.count

// Quits if the number is not 3
try {
    assert nbr_ROI == 3 : "There should be 3 ROIs"
} catch (AssertionError e) {
    println "Number of ROIs is incorrect, script will stop. " + e.getMessage()
    return
}

// Make the measurements on the image
IJ.run("Set Measurements...", "mean redirect=None decimal=3");
rm.deselect()
result_rt = rm.multiMeasure(imp_dup)

// Get the lists of values
frap_list = result_rt.getColumn(0)
whole_cell_list = result_rt.getColumn(1)
background_list = result_rt.getColumn(2)

// Info about the frame interval to get real life time info
time_frame = calibration.frameInterval

// Save the CSV
try {
    // create FileWriter object with file as parameter
    // print file_info.directory + basename
    FileWriter outputfile = new FileWriter(file_info.directory + basename + ".csv")

    // create CSVWriter with ';' as separator
    CSVWriter writer = new CSVWriter(outputfile, ';'.charAt(0),
            CSVWriter.NO_QUOTE_CHARACTER,
            CSVWriter.DEFAULT_ESCAPE_CHARACTER,
            CSVWriter.DEFAULT_LINE_END)

    // create a List which contains Data
    List<String[]> data = new ArrayList<String[]>()


    headers = new ArrayList<String>()
    headers = (["Time [s]", "Mean Intensity FRAP", "Mean intensity Cell", "Mean intensity background"])
    writer.writeNext(String.join(",", headers))

    for (int i = 0; i < frap_list.size(); i++)
    {
        text  = ([String.valueOf((i+1) * time_frame), String.valueOf(frap_list[i]), String.valueOf(whole_cell_list[i]), String.valueOf(background_list[i])])
        text2 = text.toArray(new String[0])
        String text_string = String.join(",", text2)
        writer.writeNext(text_string)
    }

    writer.close();
}
catch (IOException e) {
    // TODO Auto-generated catch block
    e.printStackTrace();
}

IJ.log("Macro finished")
IJ.log("The CSV should be found next to your image in the folder at " + output_dir + basename + ".csv")
