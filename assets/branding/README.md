# Awl owl logo

user-supplied design, the original SVG geometry, mask, white fill and 512×524 aspect ratio are preserved

- `awl.svg`, canonical SVG master, original descriptive title Owl retained
- `awl.png`, transparent512×524 PNG
- `awl@2x.png`, transparent1024×1048 PNG
- `awl-icon.png`,512×512 pure-black rounded-square icon with transparent outside corners, proportional padding, no stretching
- `awl.ico`, pure-black rounded-background multi-resolution Windows/favicon icon,16/24/32/48/64/128/256px

white-on-transparent assets need a contrasting background, only background-backed versions use the rounded pure-black tile, transparent masters and PNGs remain transparent, no changes to the owl paths or cutouts

the project README uses the icon, existing validated SDK archives and compiler/browser execution artifacts are unchanged, this ICO is an asset, not yet linked into the Windows executable

contributor-only reproduction requires resvg-py 0.5.0 and Pillow 13.0.0, run `python assets/branding/build.py` with those packages on the Python path, keep optional build dependencies outside the workspace

validation checks pure-black fill and transparent outside corners on the rounded icon, unchanged transparent masters, pupil/eye/beak cutouts, luminance masking and decoding of all seven ICO frames, file hashes and renderer versions are in validation.json

renderer reference https://github.com/linebender/resvg
