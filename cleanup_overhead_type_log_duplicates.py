"""One-shot cleanup for OverheadTypeLog rows whose `location_id` does not match
their parent `OverheadType.location_id`.

These were created by an older version of the monthly Celery generator that
looped `OverheadType x Locations` instead of using each OverheadType's own
`location_id`. The generator is now fixed; this script soft-deletes the
historical garbage.

Usage:
    python cleanup_overhead_type_log_duplicates.py                # dry-run
    python cleanup_overhead_type_log_duplicates.py --apply        # actually soft-delete
    python cleanup_overhead_type_log_duplicates.py --apply --force-paid
                                                                  # include rows with is_paid=True

Dry-run is the default and always safe.
"""

import argparse
import sys
from collections import Counter

from app import create_app
from backend.models.models import OverheadType, OverheadTypeLog, db


def find_mismatched_logs():
    """Return all non-deleted logs where log.location_id != parent OverheadType.location_id."""
    return (
        db.session.query(OverheadTypeLog, OverheadType)
        .join(OverheadType, OverheadType.id == OverheadTypeLog.overhead_type_id)
        .filter(
            OverheadTypeLog.deleted == False,
            OverheadTypeLog.location_id.isnot(None),
            OverheadType.location_id.isnot(None),
            OverheadTypeLog.location_id != OverheadType.location_id,
        )
        .order_by(OverheadTypeLog.calendar_year, OverheadTypeLog.calendar_month, OverheadTypeLog.id)
        .all()
    )


def summarize(rows):
    """Print a per-(year, month) and per-location_id breakdown."""
    by_month = Counter()
    by_location = Counter()
    paid_rows = []
    for log, _ot in rows:
        by_month[(log.calendar_year, log.calendar_month)] += 1
        by_location[log.location_id] += 1
        if log.is_paid:
            paid_rows.append(log)

    print(f"Total mismatched logs: {len(rows)}")
    print(f"Paid (is_paid=True): {len(paid_rows)}")
    print()
    print("By (calendar_year_id, calendar_month_id):")
    for key, count in sorted(by_month.items()):
        print(f"  {key}: {count}")
    print()
    print("By log.location_id:")
    for loc_id, count in sorted(by_location.items()):
        print(f"  location_id={loc_id}: {count}")

    if paid_rows:
        print()
        print("Paid rows (id, overhead_type_id, log.location_id, parent.location_id, overhead_id):")
        for log in paid_rows[:20]:
            print(
                f"  log_id={log.id} ot_id={log.overhead_type_id} "
                f"log_loc={log.location_id} overhead_id={log.overhead_id}"
            )
        if len(paid_rows) > 20:
            print(f"  ... and {len(paid_rows) - 20} more")
    return paid_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Actually soft-delete (default: dry-run)")
    parser.add_argument(
        "--force-paid",
        action="store_true",
        help="Include rows where is_paid=True (default: skip them; safer)",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        rows = find_mismatched_logs()
        if not rows:
            print("No mismatched logs found. Nothing to do.")
            return 0

        paid_rows = summarize(rows)

        if not args.apply:
            print()
            print("Dry-run only. Re-run with --apply to soft-delete the rows above.")
            return 0

        targets = rows
        if paid_rows and not args.force_paid:
            print()
            print(
                f"Refusing to soft-delete {len(paid_rows)} paid rows without --force-paid. "
                "Skipping paid rows; unpaid rows will still be processed."
            )
            targets = [(log, ot) for log, ot in rows if not log.is_paid]

        for log, _ot in targets:
            log.deleted = True
        db.session.commit()
        print(f"Soft-deleted {len(targets)} logs.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
