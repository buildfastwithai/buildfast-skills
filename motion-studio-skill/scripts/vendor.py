#!/usr/bin/env python3
"""vendor.py - fetch an optional browser library into a project's vendor/ folder (via npm pack; no global install).

  vendor.py PROJECT three          -> PROJECT/vendor/three.module.js (+ three.core.js)   for 3D scenes (WebGL)
  vendor.py PROJECT <npm-package> <file-inside-package> [...]   any other ES module / script

Use in composition.html:
  <script type="module">
    import * as THREE from '/vendor/three.module.js';
    MS.boot(C => { ... });
  </script>
WebGL canvases must be created with preserveDrawingBuffer: true so frames can be captured.
"""
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PRESETS = {"three": ("three", ["build/three.module.js", "build/three.core.js"])}


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    proj, name = Path(sys.argv[1]), sys.argv[2]
    pkg, files = PRESETS.get(name, (name, sys.argv[3:]))
    if not files:
        sys.exit("give the file(s) to copy from the package, e.g. dist/lib.min.js")
    vend = proj / "vendor"
    vend.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(["npm", "pack", pkg, "--silent"], cwd=td, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"npm pack {pkg} failed (network?): {r.stderr.strip()[:300]}")
        tgz = next(Path(td).glob("*.tgz"))
        with tarfile.open(tgz) as tf:
            tf.extractall(td)
        for f in files:
            src = Path(td) / "package" / f
            if not src.exists():
                sys.exit(f"{f} not found in {pkg}")
            shutil.copy(src, vend / src.name)
            print("vendored", vend / src.name)


if __name__ == "__main__":
    main()
