# Engineering decisions

1. **Two state machines.** Visual hazard history and communications response are stored separately so cancellation never erases a visually confirmed event.
2. **Monotonic edge time.** Ordering, persistence, growth, and timeout eligibility use `monotonic_ns`; backend UTC is display/audit time only.
3. **Fixed binary envelope, JSON metadata.** A 32-byte network-order header supplies bounds, sequence, time, type, and CRC while JSON payloads remain inspectable.
4. **Bounded latest-frame behavior.** Video is replaceable; incidents and timeline events are durable. Slow UI/network consumers cannot back-pressure camera capture.
5. **SQLite without an ORM.** The backend uses explicit SQL and transactions, keeping call deduplication and persistence behavior auditable.
6. **No speculative QNX SDK calls.** Vendor adapters are compiled only when actual target headers and a verified camera sample are available.
7. **Provider acceptance is not connection.** A successful outbound API response becomes `CALL_INITIATED`/`CALL REQUEST ACCEPTED`; a provider callback is required for `CALL_CONNECTED`.
8. **Calling is server-side and deny-by-default.** The UI cannot submit a destination. Exact allowlists, emergency-number denial, one-call limits, and cooldown are enforced before any provider request.
9. **Deterministic observations.** A formatter converts typed evidence to bounded phrases. A language model never derives raw incident facts.
10. **Current ElevenLabs contract.** The frontend targets `@elevenlabs/react` 1.10.x and the backend uses the documented signed-URL and native Twilio outbound endpoints. Credentials never reach the browser.

