//@ LogService log

importClass(Packages.ij.Prefs);

Prefs.set("imcf.debugging", true);
Prefs.savePreferences();

log.info("Enabled IMCF debug logging.");
