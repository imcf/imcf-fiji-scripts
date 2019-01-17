#@ String(label="command", choices={"init", "update_selection", "get_status", "mark_primary", "mark_secondary"}) cmd


function logger(level, msg) {
    // verbosity logging, print "msg" only if "level" is equal or
    // higher than the value of the global variable "loglevel"
    // levels: 0:quiet, 3:warn, 4:info, 5:debug
    if (loglevel - level >= 0)
        print(msg);
}

function window_exists(title) {
    // walk through the list of open (non-image) windows and
    // check if a window with the given title exists
    windows = getList("window.titles");
    for (i=0; i<windows.length; i++) {
        if (windows[i] == title)
            return true;
    }
    return false;
}

function get_table_selection() {
    // return the value of the first field of the "Results" table's current
    // selection ("String.copyResults" ALWAYS works on the default "Results"
    // table, no way to adjust this!)
    // TODO: refactor this to return an array(row, ID, ROI)
    String.copyResults();
    str = String.paste();
    fields = split(str, "\t");
    return fields[0];
}

function get_table_row_by_id(id){
    // look up a given ID in the Results table and return the
    // row (index number) if it exists, otherwise -1
    // TODO: after refactoring get_table_selection this should
    // not be required any more
    setOption("ShowRowNumbers", true);
    updateResults;
    id_ret = -1;
    for (i=0; i < nResults; i++){
        id_cur = getResult("ID", i);
        if (id == id_cur){
            id_ret = i;
        }
    }
    setOption("ShowRowNumbers", false);
    updateResults;
    return id_ret;
}

function get_table_row_by_roiname(name){
    // look up a given ROI-name in the Results table and return the
    // row (index number) if it exists, otherwise -1
    // TODO: after refactoring get_table_selection this needs to
    // be refactored as well
    setOption("ShowRowNumbers", true);
    updateResults;
    id_ret = -1;
    for (i=0; i < nResults; i++){
        name_cur = getResultString("ROI", i);
        if (name == name_cur){
            id_ret = i;
        }
    }
    setOption("ShowRowNumbers", false);
    updateResults;
    return id_ret;
}

function roim_select_from_results(){
    // update the ROI manager selection to match the selected
    // entry from the Results window
    sel = get_table_selection();
    logger(4, "selection in results table: " + sel);
    roim_select(sel-1);
}

function roim_select(id) {
    // select a single entry in the ROI manager
    roiManager("Deselect");
    // check for invalid index (e.g. after initialization)
    if (id < 0)
        return;
    roiManager("select", id);
}

function create_advanced_results_table() {
    // convert an existing "Results" table into a new one that has a fixed
    // "ID" column (which doesn't change when elements get deleted) and some
    // additional columns (the ROI name, Mother- and Daughter-Cell property)

    if (roiManager("count") < 2) {
        msg = "ERROR: At least two ROIs required, not initializing!";
        logger(0, msg);
        exit(msg);
    }

    // make sure the ID column is disabled:
    setOption("ShowRowNumbers", false);

    // make sure the results table contains only measurements of current ROIs:
    run("Clear Results");
    roiManager("Deselect");
    roiManager("Measure");

    // get the data and close the original Results table:
    selectWindow("Results");
    lines = split(getInfo("window.contents"), "\n");
    run("Close");

    headings = split(lines[0], "\t");
    for (i=1; i < lines.length; i+=1) {
        roiManager("select", i-1);
        name = Roi.getName;
        setResult("ID", i-1, i);
        setResult("ROI", i-1, name);
        fields = split(lines[i], "\t");
        for (j=0; j < fields.length; j++) {
            setResult(headings[j], i-1, fields[j]);
        }
        setResult("Mothercell", i-1, "");
        setResult("Daughtercell", i-1, "");
    }

    // make sure the ID column is disabled:
    setOption("ShowRowNumbers", false);
    updateResults;
}

function table_name(title){
    // convenience wrapper creating the string surrounded by square
    // brackets required to create and print to a table window
    return "[" + title + "]";
}

function create_status_table(title) {
    // create a table window, requires the title enclosed in square
    // brackets (see table_name() for details)
    // NOTE: the blank at the end of "New... " is required!!!
    run("New... ", "name="+title+" type=Table");
}

function get_status_table(title) {
    // return contents of status table (NOTE: name *MAY NOT* be given
    // with the surrounding square brackets!), if the table does
    // not exist yet, it will be created and 0 will be returned
    if (window_exists(pcw) == false) {
        create_status_table(pct);
        return 0;
    }
    selectWindow(title);
    return getInfo("window.contents");
}

function set_status_table(table, value) {
    // set the content of the status table (name required in square
    // brackets, see table_name() for details)
    // create the "primary cell" status table if not existing:
    logger(3, "status table name: " + table);
    logger(3, "new status value: " + value);
    if (window_exists(pcw) == false) {
        logger(4, "creating status table " + table);
        create_status_table(pct);
    }
    print(table, "\\Update0:" + value);
}

function roi_mark_primary() {
    // mark the ROI currently selected as a "primary" ROI, updating its status
    // in the table, highlighting it using a large stroke width and adding the
    // corresponding properties to the ROI in the manager
    sel_id = roiManager("index");
    logger(3, "selected ROI index (0-based): " + sel_id);
    sel_name = Roi.getName();
    row = get_table_row_by_roiname(sel_name);
    logger(3, "selected ROI name: " + sel_name);
    // before resetting the stroke width, we need to select the previous
    // primary cell (stored in the status table)
    roim_select(parseInt(get_status_table(pcw)) - 1);
    Roi.setStrokeWidth(1);
    roim_select(sel_id);
    // now we adjust the new cell
    Roi.setStrokeColor("red");
    Roi.setStrokeWidth(7);
    Roi.setProperty("Mothercell", "M-" + (sel_id+1));
    logger(3, "ROI properties: " + Roi.getProperties);
    set_status_table(pct, (sel_id+1));
    setResult("Mothercell", row, "M-" + (sel_id+1));
    // we need to reset the "Daughtercell" value as well in case the ROI was
    // labeled as being of that type before:
    setResult("Daughtercell", row, "");
}

function roi_mark_secondary() {
    // mark the ROI currently selected as a "secondary" ROI, updating its
    // status in the table, highlighting it using a different color and adding
    // the corresponding properties to the ROI in the manager
    sel_id = roiManager("index");
    logger(3, "selected ROI index (0-based): " + sel_id);
    sel_name = Roi.getName();
    logger(3, "selected ROI name: " + sel_name);
    row = get_table_row_by_roiname(sel_name);
    // we need the primary cell's id to create the relation
    pc_id = parseInt(get_status_table(pcw));
    Roi.setStrokeWidth(1);
    Roi.setStrokeColor("green");
    Roi.setProperty("Daughtercell", "M-" + pc_id + ":D-" + (sel_id+1));
    logger(3, "ROI properties: " + Roi.getProperties);
    setResult("Mothercell", row, "M-" + pc_id);
    setResult("Daughtercell", row, "D-" + (sel_id+1));
}

// set the global loglevel (0:quiet, 3:warn, 4:info, 5:debug):
loglevel = 0;

// global variables for "primary cell" window and table:
pcw = "Current mother cell";
pct = table_name(pcw);


logger(5, "arguments: " + cmd);
if (cmd == "init") {
    create_advanced_results_table();
} else if (cmd == "update_selection") {
    roim_select_from_results();
} else if (cmd == "get_status") {
    print(get_status_table(pcw));
} else if (cmd == "mark_primary") {
    roi_mark_primary();
} else if (cmd == "mark_secondary") {
    roi_mark_secondary();
} else {
    print("ERROR: no or unknown argument given!");
}
