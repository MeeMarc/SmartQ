# Queue Mode Flow

SmartQ now stores queue workflow mode per generated QR using two fields:

- `processing_method`: `Online` or `Walk-in`
- `release_type`: `Digital Copy` or `Physical Claim`

## Flow Matrix

1. `Online + Digital Copy`
- Registration is submitted online.
- Release is digital (email/download flow).

2. `Online + Physical Claim`
- Registration is submitted online.
- Release is onsite pickup/claim.

3. `Walk-in + Digital Copy`
- Queue processing may be onsite.
- Release is digital (email/download flow).

4. `Walk-in + Physical Claim`
- Queue processing is onsite.
- Release is onsite pickup/claim.

## Notes

- Existing queues without mode values default to `Online` + `Digital Copy`.
- Scan Tracking hides `Send Document` when a queue is configured as `Physical Claim`.
- The user-facing `Download Ticket` action now exports a branded PNG proof card with the ticket QR, registration details, and current application status.
