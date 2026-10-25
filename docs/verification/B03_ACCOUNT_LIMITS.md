# B03 account rate limits

**Observation recorded: 25 October 2026. Source: user-supplied Google AI Studio screenshot.**

The screenshot selects project **FigureTrail**, displays **Niveau sans frais** (free tier), and uses a **28-day** reporting period. Its original capture timestamp is not visible; the date above is when the screenshot was supplied and transcribed. No independent account API query or project-ID/key association check was performed. The screenshot is in the conversation and has not been copied into the repository.

## Observed limits

| AI Studio display name | Configured model ID | Requests/minute (RPM) | Input tokens/minute (TPM) | Requests/day (RPD) |
|---|---|---:|---:|---:|
| Gemini 3.5 Flash Lite | `gemini-3.5-flash-lite` | 15 | 250,000 | 500 |
| Gemini Embedding 2 | `gemini-embedding-2` | 100 | 30,000 | 1,000 |

Model IDs are mapped from the existing provider configuration; the screenshot shows display names. The denominators in each displayed pair are the limits. The values before the slash are usage peaks during the selected 28 days: generation shows 4 RPM, 9.36K TPM and 5 RPD; embeddings show 1 RPM, 11 TPM and 1 RPD. These are not remaining allowances or a reading of today's usage.

[Google's rate-limit documentation](https://ai.google.dev/gemini-api/docs/rate-limits) defines RPM, input TPM and RPD, applies limits per project rather than per key, and notes that actual capacity can vary. These observations are a dated account snapshot, not permanent entitlements or a capacity guarantee.

## Implications for FigureTrail

- Keep the selected provider and models for the next small compatibility check. The observed limits appear suitable for the planned small, paced experiments; this is a planning assessment, not a load-test result.
- Pace repeated generation requests within the 15 RPM limit and count all requests in an evaluation or agent run. The existing no-retry behavior avoids silently extending a quota failure.
- During B04 preparation, account for embedding input tokens as well as request counts: the 30,000 input TPM limit can constrain corpus embedding even below 100 RPM. Token-aware pacing is not currently implemented.
- Preserve the local allowance journal and spending ceiling. The displayed free tier does not reconcile historical charges; actual billing remains unverified. No billing settings were changed.

## B03 status

The account-quota checklist item is complete based on this screenshot. A subsequent [native tool check](B03_TOOL_CALL.md) verified the remaining item with validated arguments and original source values, completing B03. No model request, code change or throughput test was required for this observation. Earlier connection/pilot JSON snapshots retain the billing and quota knowledge available when those runs occurred.
