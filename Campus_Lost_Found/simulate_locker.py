"""Local-only SIMULATED heartbeats. Never connects to a network or changes notices."""
from pathlib import Path
import argparse
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
if sys.platform == 'win32':
    sys.path.insert(0, str(ROOT / 'vendor'))
from stage2_features import record_simulated_event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / 'data' / 'campus.sqlite3')
    parser.add_argument('--telemetry', type=Path, default=ROOT / 'data' / 'telemetry.sqlite3')
    parser.add_argument('--samples', type=int, default=6)
    parser.add_argument('--interval', type=float, default=5)
    args = parser.parse_args()
    if not 1 <= args.samples <= 100 or not 0 <= args.interval <= 60:
        parser.error('Use 1–100 samples and an interval of 0–60 seconds.')
    print('SIMULATED: direct local SQLite writes; no sensors or network.')
    for index in range(args.samples):
        if index:
            time.sleep(args.interval)
        try:
            record_simulated_event(args.telemetry, args.database, 'heartbeat')
        except (ValueError, OSError) as error:
            print('No reading saved: ' + str(error), file=sys.stderr)
            return 1
        print('SIMULATED heartbeat %s/%s saved; latest door state preserved.' % (index + 1, args.samples), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

