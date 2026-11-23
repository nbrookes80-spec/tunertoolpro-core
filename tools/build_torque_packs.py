"""Build the Ford PID pack from the Torque Pro extraction (torque-pro-main/5-extracted-data).

    python3 tools/build_torque_packs.py /path/to/5-extracted-data

Reads manufacturer-pids/ford_incl_powerstroke.csv and ford_secondary_table.csv, keeps only the rows this app
can read safely, and writes tunertoolpro/data/torque_ford.csv in the same Torque layout as the other packs. The
safety checks are the app's own: every row goes through scanner/torque_csv.py, so only Mode 01 and Mode 22
reads with a plain A-to-D equation are kept. On top of that this tool drops any row that asks for a module the
app does not know how to address (the file says TCM, ABS, 726, C410F1 and so on). The reader would otherwise
quietly send such a row to the broadcast address, which would read the wrong module. The dropped rows are
printed with the reason so nothing disappears unseen.
"""

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tunertoolpro.scanner import torque_csv  # noqa: E402

SOURCES = ('ford_incl_powerstroke.csv', 'ford_secondary_table.csv')
ADDRESSED = ('', 'AUTO', '7E0', '7E2', '7E3')   # headers the app can address; anything else is dropped here
FIELDS = ('name', 'short_name', 'mode_and_pid', 'equation', 'min_value', 'max_value', 'unit', 'header')
HEAD = ['Name', 'ShortName', 'ModeAndPID', 'Equation', 'Min Value', 'Max Value', 'Units', 'Header',
        'startDiagnostic', 'stopDiagnostic', 'scale', 'minimumRefreshDelayMillis']


def build(extract):
    rows, dropped = [], []
    for name in SOURCES:
        with open(Path(extract) / 'manufacturer-pids' / name, encoding='utf-8', newline='') as handle:
            for raw in csv.DictReader(handle):
                header = raw['header'].strip().upper()
                if header not in ADDRESSED:
                    dropped.append((raw['name'], f'module "{raw["header"]}" is not an address the app can use'))
                    continue
                rows.append([raw[f] for f in FIELDS] + ['', '', raw.get('scale') or '1', '0'])
    # every row must pass the app's own reader; keep the first of a repeated PID, as the app does
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator='\n')
    writer.writerow(HEAD)
    for row in rows:
        row[2] = '0x' + row[2].strip().upper().removeprefix('0X')
        writer.writerow(row)
    found, rejected = torque_csv.parse(out.getvalue(), 'ford')
    kept = {p.pid for p in found}
    reason = {r['name']: r['reason'] for r in rejected}
    final, seen = [], set()
    for row in rows:
        pid = row[2][2:]
        if row[0] in reason or pid not in kept or pid in seen:
            continue
        seen.add(pid)
        final.append(row)
    dropped += [(name, why) for name, why in reason.items()]
    return final, dropped


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    final, dropped = build(sys.argv[1])
    target = ROOT / 'tunertoolpro' / 'data' / 'torque_ford.csv'
    with open(target, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL, lineterminator='\n')
        writer.writerow(HEAD)
        writer.writerows(final)
    print(f'{len(final)} Ford rows written to {target}')
    for name, why in dropped:
        print(f'  dropped: {name}: {why}')


if __name__ == '__main__':
    main()
