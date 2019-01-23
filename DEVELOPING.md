Development Instructions
========================

Making a new release
--------------------

To create a new release, clone the [scijava-scripts][gh_scijava-scripts] repo
(e.g. in `/opt/imagej/`) and run the `release-version.sh` helper:

```bash
BASE_DIR=/opt/imagej
mkdir -pv "$BASE_DIR"
cd "$BASE_DIR"
git clone https://github.com/scijava/scijava-scripts
cd -

"$BASE_DIR/scijava-scripts/release-version.sh" --skip-push --skip-gpg
```

Build & Deploy using Visual Studio Code
---------------------------------------

Building and deploying the package can be greatly simplified using "tasks" in
[Visual Studio Code][www_vscode]. By adding the following settings to the
`.vscode/tasks.json` file, you can simply press `Ctrl+B` in VS Code and select
the *deploy* task for running Maven and have the resulting JAR file bein placed
in `/opt/fiji-packaging/Fiji.app/jars/`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "verify",
            "type": "shell",
            "command": "mvn -B verify",
            "group": "build"
        },
        {
            "label": "test",
            "type": "shell",
            "command": "mvn -B test",
            "group": "test"
        },
        {
            "label": "deploy",
            "type": "shell",
            "command": "mvn -Dimagej.app.directory=/opt/fiji-packaging/Fiji.app",
            "group": {
                "kind": "build",
                "isDefault": true
            },
            "problemMatcher": []
        }
    ]
}
```

[gh_scijava-scripts]: https://github.com/scijava/scijava-scripts
[www_vscode]: https://code.visualstudio.com/
