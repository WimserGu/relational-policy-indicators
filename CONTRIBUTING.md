# Contributing

Issues that improve reproducibility, documentation, portability, or verification are welcome.

1. Open an issue describing the proposed change and the affected analytical object.
2. Do not commit raw PeeringDB/CAIDA archives, credentials, private correspondence, or provider files excluded by `data/README.md`.
3. Preserve the distinctions among recorded positive, recorded zero under the frozen construction, and not observed.
4. Do not change frozen analytical values without a new, documented analysis version and provenance record.
5. Run `python scripts/verification/verify_repository.py` and `python -m unittest discover -s tests -v` before submitting code changes.

The manuscript's causal and construct boundaries are part of the scientific contract. Shared-ASN participation must not be relabelled as direct peering, traffic, bandwidth, latency, or research use.
