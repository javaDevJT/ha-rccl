# 2026-06-01 Loyalty Totals and Booking Attributes

## Symptom

Home Assistant displayed `Total cruise nights` and `Total cruise trips` as `0`
even though the account had visible cruise activity. This made the account
summary misleading.

## Root Cause

The integration trusted only `loyalty_summary.payload.totalTrips` and
`loyalty_summary.payload.totalNights`. RCCL can return an empty or zero summary
while richer loyalty-history sailing rows are available elsewhere in the
coordinator data.

## Fix

`loyalty_summary()` now normalizes several observed/likely total-key spellings
and backfills zero or missing totals from loyalty-history sailings when history
contains completed sailings.

## Data Exposure Decision

The Home Assistant-facing booking attributes should include booking identifiers
and passenger identity fields for account bookings. Real passenger names,
booking ids, account ids, and credentials should still not be committed to
repository docs or tests.

Club Royale offer sailings are different: the offer-detail payload is not a
confirmed booking payload and booking/passenger fields are not expected to be
available there. The Club Royale card should show sailing, ship, cabin, and
offer details instead.
