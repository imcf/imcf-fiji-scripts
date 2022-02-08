//@ LogService log

importClass(Packages.ij.Prefs);

Prefs.set("imcf.debugging", true);
Prefs.savePreferences();

log.info("Enabled IMCF debug logging.");


/*
NOTE: in ImageJ-Macro use the following approach for a debug-print function that
will respect the IMCF debugging preference setting (please do *NOT* put the
`eval` statement inside the function as it is terribly slow!):
----

DEBUG = eval("js", "debug = Prefs.get('imcf.debugging', false)");

function dprint(message) {
    if (DEBUG) {
        print(message);
    }
}

----
*/