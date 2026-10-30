# tunertoolpro-core

The GUI-free core of TunerToolPro (GM 4L60E / 6L80E transmission calibration tools): shift and
converter maths, BC Trans and EFILive file formats, vehicle and engine data, the AI-assistant tools,
and the CAN bus sniffer logic (frames, sniffer model, ELM327 receive-only monitor, transports).

It has no GUI and no required dependencies. `pyserial` (serial adapters) and `pandas` (log import)
are imported lazily and only when those features are used.

## Using it

The apps do not install this package. Each app keeps a copy of these files in its own
`tunertoolpro/` folder, pinned to a release tag recorded in its `core.lock`. To move an app to a new
release, run that app repo's `tools/update_core.py <tag>`.

Releases are git tags (`v0.1.0`, ...). Never change a tag once it is published.

## Developing

    python -m unittest discover -s tests -t .

Change the core here, tag a release, then update the apps. Do not edit the vendored copies inside an
app: the app's test suite fails if they drift from the pinned tag.

## Licence

GPL-3.0 (see `LICENSE`). Third-party notices are in `docs/THIRD_PARTY.md`.
