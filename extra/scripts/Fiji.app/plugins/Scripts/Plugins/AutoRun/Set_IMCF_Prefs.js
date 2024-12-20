//@ LogService log
importClass(Packages.ij.IJ);
importClass(Packages.ij.Prefs);

importClass(Packages.java.io.File);
importClass(Packages.java.util.Arrays);
importPackage(java.nio.file);
importPackage(java.nio.charset);
importClass(Packages.ij.Prefs);

// Get the debugging flag from the preferences
debug = Prefs.get("imcf.debugging", "");
function log_debug(msg) {
    /**
     * Logs a debug message if debugging is enabled.
     *
     * @param {string} msg - The message to log.
     */
    if (debug != "")
        print(msg);
}


function checkFileAndSetPrefs() {
    /**
     * Checks for the existence of a settings file in the directory of FIji installation
     * and sets preferences based on keys and values in it.
     */

    // Get the parent directory where the settings file is located
    var parentDir = IJ.getDirectory("imagej");
    if (parentDir == null) {
        log_debug("Cannot determine the parent directory. Exiting...");
        return;
    }

    // Define the path to the JSON file
    var jsonFile = new File(parentDir, "imcf-settings.json");

    // Check if the file exists
    if (!jsonFile.exists()) {
        log_debug("config.json not found in the located directory.");
        return;
    }

    // Read the JSON file content and join strings
    var jsonString = readFile(jsonFile).join("\n");
    var jsonData;
    try {
        jsonData = JSON.parse(jsonString);
    } catch (e) {
        log_debug("Error parsing json file: " + e.message);
        return;
    }

    // Check for required keys in settings file and set preferences
    if (jsonData.imcf) {
        if (jsonData.imcf.smtpserver && jsonData.imcf.sender_address) {
            log_debug("Setting preferences based on imcf-settings.json...");
            Prefs.set("imcf.smtpserver", jsonData.imcf.smtpserver);
            Prefs.set("imcf.sender_email", jsonData.imcf.sender_address);
            Prefs.savePreferences();
            log_debug("Preferences successfully set.");
        } else {
            log_debug("Missing 'smtpserver' or 'sender_address' in config.json.");
        }
    } else {
        log_debug("'imcf' key not found in config.json.");
    }
}

// Utility function to read file content
function readFile(file) {
    var lines = [];
    try {
        var br = new BufferedReader(new FileReader(file));
        var line;
        while ((line = br.readLine()) != null) {
            lines.push(line);
        }
        br.close();
    } catch (e) {
        log_debug("Error reading file: " + e.message);
    }
    return lines;
}

checkFileAndSetPrefs();