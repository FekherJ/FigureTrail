# Hosted provider and model selection

**Decision date: 25 October 2026. Status: connection and source-case pilot verified; quotas/tool-call check pending.**

## Decision

Use the **Google Gemini Developer API**, starting with an eligible project's free tier.

| Responsibility | Selected model | Initial setting |
|---|---|---|
| Structured cell selection and later tool calling | `gemini-3.5-flash-lite` | Minimal thinking for the fixed-workflow pilot; bounded output. |
| Text embeddings for semantic retrieval | `gemini-embedding-2` | 768 dimensions; one vector per chunk, with the same model/configuration for questions. |

Google lists both model IDs as stable. Flash-Lite supports structured output and function calling. The embedding model accepts text and supports 768-dimensional output. These are documented capabilities, not FigureTrail measurements. [Generation model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [embedding model](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2).

## Rationale and alternatives

The task is narrow: select an allowed operation and source cells, then let application code validate and calculate. A latency-oriented model is a suitable starting point. One provider covers generation and embeddings, keeping the integration aligned with the existing architecture. FigureTrail retains its own preparation, retrieval, calculations, evaluations, tool permissions and execution records.

| Candidate | Assessment |
|---|---|
| Gemini Flash-Lite + Embedding 2 | Selected: documented free-tier access for both, stable IDs and the required capabilities. Basic account access subsequently passed the connection check. |
| OpenAI `gpt-6-luna` + `text-embedding-3-small` | Credible alternative with structured output, function calling and embeddings. Account credits are unknown. The initial choice favors the documented Gemini free tier. [Generation](https://developers.openai.com/api/docs/models/gpt-6-luna), [embeddings](https://developers.openai.com/api/docs/models/text-embedding-3-small), [pricing](https://developers.openai.com/api/docs/pricing). |
| Groq `openai/gpt-oss-20b` | Credible structured-generation option. The published free-plan summary includes an 8,000-token/minute limit, which may constrain repeated larger-context tests. It is not the initial provider. [Structured output](https://console.groq.com/docs/structured-outputs), [limits](https://console.groq.com/docs/rate-limits). |

Google currently restricts new-user access to older 2.5 models. Use the selected stable IDs rather than starting from an older tutorial's model name. [Model availability](https://ai.google.dev/gemini-api/docs/models).

## Free tier, paid fallback and budget

The published free tier covers generation input/output and text embeddings for these selections. If paid access becomes necessary, current Standard prices are **$0.30/million input tokens and $2.50/million output tokens** for Flash-Lite, and **$0.20/million text-input tokens** for Embedding 2. Prices are USD, before applicable tax and currency conversion. Output pricing includes thinking tokens. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing).

Illustration, not a project-cost forecast: 1,000 generation calls using 5,000 input and 300 total billable output tokens each cost $2.25 at those rates. Embedding 100,000 text tokens adds $0.02. Agent/tool cycles, failures and additional attempts add usage.

Start without enabling paid billing. If quotas repeatedly interrupt work, first evaluate the paid tier for the same models; that avoids a provider migration. This is a fallback decision, not a billing change. Keep the existing cumulative budget strictly below **EUR 30**, including all calls and preparation. Local estimates are not a guaranteed billing cap.

Limits depend on the account/project and model. Inspect the project's active RPM, TPM and daily quotas in AI Studio; do not assume a fixed number of free requests. Free access does not guarantee capacity or response time. Stop with a clear quota error rather than silently waiting through long retries. [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Integration requirements

- Use Google's official GenAI SDK in the single provider module. Verify compatibility with the project's Python runtime before locking its version.
- Read the API key from the local environment; do not put it in Git, browser code or execution records. Create/manage the key through [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key).
- Keep the existing 20-second provider timeout, 60-second execution deadline and 1,000-token output ceiling as initial limits. Explicitly account for thinking/output usage and disable hidden retries.
- Validate schema, source references and outcomes in Python. Documented JSON support does not establish semantic correctness.
- In B10, keep tool execution under application control and preserve provider-required conversation metadata. Reassess thinking effort using the fixed-versus-agent comparison. [Function calling](https://ai.google.dev/gemini-api/docs/function-calling).
- For Embedding 2, use the documented query/document retrieval formatting, with `title: none` when no title is verified. Produce a separate vector per chunk: multiple inputs may otherwise aggregate into one vector. Validate dimensions, finite values, norms and matrix mapping. Version model, dimensions and formatting together. [Embedding guidance](https://ai.google.dev/gemini-api/docs/embeddings).

## Validation gate

B03 remains open. The local key, locked SDK 2.33.0 and [connection check](../verification/B03_PROVIDER_CONNECTION.md) are verified. The [source-case pilot](../verification/B03_SOURCE_CASE.md) then produced three matching operation/cell selections at a 0.950-second median and one missing-period abstention. `app/llm.py` now centralizes generation/embedding requests, limits and SQLite allowances. Numeric project quotas and tool-call compatibility remain pending. No corpus embeddings or complete analysis workflow exist yet.

The connection check uses the supported `generateContent` and `embedContent` SDK paths. An offline quota test exposed inconsistent retry-count translation in the SDK's Interactions path. The selected paths were verified to send exactly one request on a simulated 429 error; no private SDK configuration is patched. Recheck this boundary after SDK upgrades.

The controlled pilot records model/prompt/code/source versions, duration, tokens and conservative paid-equivalent estimates. An embedding response was checked before corpus construction. Offline quota, invalid-reference and spending-limit checks passed without fees. Actual provider charges remain unknown; the local journal is a conservative allowance mechanism, not a billing cap.

Initial latency target: a median of at most five seconds across three sequential successful structured-output requests, each configured with a 20-second transport timeout. The source-case pilot passed at 0.950 seconds. This is a small-context feasibility result, not a speed guarantee or end-to-end RAG measurement. Reassess using broader cases and payloads during evaluation.

Record actual account quotas and measurements in B03 verification evidence. Revisit this selection if access, latency, cost or evaluation results are unsuitable; publish the findings rather than claiming an unmeasured benefit.
