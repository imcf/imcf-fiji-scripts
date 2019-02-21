//@ LogService log

importClass(Packages.ij.Prefs);

Prefs.set("imcf.debugging", false);
Prefs.savePreferences();

log.info("Disabled IMCF debug logging.");
