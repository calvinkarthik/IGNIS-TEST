# IGNIS dashboard

The dashboard renders authoritative Pi/backend state. It never marks a call connected without a provider callback and never treats a missing visual signature as proof of safety.

```powershell
pnpm install
pnpm dev
pnpm test -- --run
pnpm build
```

Voice is manual opt-in. The ElevenLabs API key remains on the backend; the browser receives only a short-lived signed URL.

