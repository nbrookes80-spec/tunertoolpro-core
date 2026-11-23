# tunertoolpro-core

The GUI-free core of TunerToolPro (GM 4L60E / 6L80E transmission calibration tools): shift and
converter maths, BC Trans and EFILive file formats, vehicle and engine data, the AI-assistant tools,
the CAN bus sniffer logic (frames, sniffer model, ELM327 receive-only monitor, transports), and the
scanner: the OBD-II link (`tunertoolpro.link`), the PID catalogue, car profiles, CAN log import and
replay, data logging and the live stream (`tunertoolpro.scanner`, `live`, `grading`, `prefs`, `recorder`).
The link is read-only: the Mode 04 code clear is refused unless an app builds it with `allow_clear=True`.

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

## PID packs (other cars)

Nothing in a pack is confirmed on a real car; every row loads as "unconfirmed".

- Generic OBD-II (`data/torque_generic_obd2.csv`, 31 rows): SAE J1979 Mode 01 PIDs 0x00-0x5F that the built-in
  catalogue lacks, written from the public J1979 formulas (the fuel rate and fuel trim formulas also match the Torque
  Pro source in `torque-pro-main`). Mode 01 only, read from the broadcast address.
- GM and Holden: the Torque Pro exports `torque_gm_predefined.csv` and `torque_e38_t43_v5.csv`, unchanged.
- Toyota-style modules: the rows of the owner's Torque PID CSV that are not tagged `[GM]` (Mode 21 on 7B0, 7C0, 7C4
  and 7E1). The pack appears once that file is copied to `data/torque_toyota_style.csv`; the file was not available
  when the code was written, so no Toyota rows are shipped yet. Its Mode 21 reads are skipped ("module access is
  off") unless the link is built with `Elm327(..., extra_modules=True)`, which allows `ATSH` for exactly those four
  headers and Mode 21 requests for catalogued ids only; 2E, 2F, 31, 10, 27, 14 and 04 stay refused.
