# The providers of the free tier

AgenTether talks to the providers through
`agentether.adapters.openai_compatible`, one generic worker and a small
table of presets (`agentether.adapters.openai_compatible.PROVIDERS`).

**Everything in this document was read on 2026-10-20** from the official
documentation of each provider.  A fact that the documentation does not
state is marked **UNVERIFIED**; it is never guessed.  The presets in the
code carry the same marks in their `notes` field, and a test
(`tests/test_openai_compatible.py`) fails when a provider has no link to
its documentation or no access date.

**The hard rule of this project: nothing is ever paid for.**  A provider
that answers `HTTP 402` (payment required) is stopped at once and reported;
the tool never enables a paid plan, never adds a payment method and never
rotates a key to get around a quota.

## The table

| Provider | Base URL | Key | RPM | RPD | Seed | Models list |
| --- | --- | --- | --- | --- | --- | --- |
| OpenRouter | `https://openrouter.ai/api/v1` | `Authorization: Bearer` | 20 | 50 | `seed` | `/models` **with the price** |
| Groq | `https://api.groq.com/openai/v1` | `Authorization: Bearer` | 30 | 1000 | `seed` | `/models` (no price) |
| Cerebras | `https://api.cerebras.ai/v1` | `Authorization: Bearer` | 5 | **UNVERIFIED** (1000 used) | `seed` | `/models` (no price) |
| Mistral | `https://api.mistral.ai/v1` | `Authorization: Bearer` | **UNVERIFIED** (2 used) | **UNVERIFIED** (100 used) | `random_seed` | `/models` (no price) |
| Google AI Studio | `https://generativelanguage.googleapis.com/v1beta/openai` | `Authorization: Bearer` | **UNVERIFIED** (15 used) | **500 per model** (verified from the answer of the provider, 2026-10-21) | none for chat | `/models` (no price) |
| Ollama (local) | `http://localhost:11434/v1` | none | no quota | no quota | `seed` | `/models` (no price) |

The path of the call is `/chat/completions` in every case, but the **base
paths differ**: Groq is `.../openai/v1` (not `.../v1`), Gemini is
`.../v1beta/openai`, and Ollama is `.../v1`.  A base URL and a path are
therefore never concatenated by hand in the code.

## The facts and where they come from

### OpenRouter

* Pages: <https://openrouter.ai/docs/quickstart>,
  <https://openrouter.ai/docs/api-reference/overview>,
  <https://openrouter.ai/docs/api-reference/limits>,
  <https://openrouter.ai/docs/api-reference/errors>,
  <https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties>
* Base `https://openrouter.ai/api/v1`, `POST /chat/completions`. **verified**
* `Authorization: Bearer <key>`, the key is normally `OPENROUTER_API_KEY`.
  **verified**
* `GET /api/v1/models` returns `pricing.prompt` and `pricing.completion`
  per model, so the free models are the ones whose price is zero.  The
  catalogue also accepts `?min_price=0&max_price=0&min_output_price=0&max_output_price=0`.
  **verified**
* Free tier: **20 requests per minute**; **50 requests per day** while the
  account has bought no credits (1000 per day after a purchase of 10
  credits -- this project never buys credits).  The number of tokens per
  day is **UNVERIFIED**.  **verified**
* `response_format` (`json_object` and `json_schema`) and `seed` are
  supported.  **verified**
* The rate limit is `HTTP 429` with
  `{"error": {"code": 429, "message": ..., "metadata": {...}}}`; the
  platform adds `X-RateLimit-Limit`, `X-RateLimit-Remaining` and
  `X-RateLimit-Reset`, and `Retry-After` when the upstream provider gives
  a hint.  **verified**
* `HTTP 402` is documented: it is a credits or budget condition
  (`metadata.limit_source` is `openrouter_credits`, `openrouter_key_limit`
  or `openrouter_in_flight_budget`).  **verified**

### Groq

* Pages: <https://console.groq.com/docs/api-reference>,
  <https://console.groq.com/docs/openai>, <https://console.groq.com/docs/rate-limits>,
  <https://console.groq.com/docs/errors>
* Base `https://api.groq.com/openai/v1`, `POST /chat/completions`.  **verified**
* `Authorization: Bearer $GROQ_API_KEY`.  **verified**
* `GET /openai/v1/models` lists the models.  The **price of a model is not
  documented**, so the catalogue cannot be used to find the free ones.
  **verified (URL), UNVERIFIED (price)**
* The free plan limits are given **per model**: the instruction models
  (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`) get
  30 requests per minute, 1000 requests per day and 200000 tokens per
  day; the guard models get 14 400 requests per day; the transcription
  models get 20 requests per minute and 2000 requests per day.  **verified**
* `response_format` (`json_object` and `json_schema`) and `seed` are
  supported (the determinism of the seed is best effort).  **verified**
* The rate limit is `HTTP 429`.  The headers are `retry-after`,
  `x-ratelimit-limit-requests`, `x-ratelimit-limit-tokens`,
  `x-ratelimit-remaining-requests`, `x-ratelimit-remaining-tokens`,
  `x-ratelimit-reset-requests` and `x-ratelimit-reset-tokens`.  The shape
  of the JSON body of the error is **UNVERIFIED**.  **verified**
* There is **no 402** in the list of the documented status codes of Groq.
  **verified (absence)**
* `max_tokens` is deprecated in favour of `max_completion_tokens`.  The
  layer sends `max_tokens`, which is still accepted.  **verified**

### Cerebras

* Pages: <https://inference-docs.cerebras.ai/resources/openai>,
  <https://inference-docs.cerebras.ai/support/rate-limits>,
  <https://inference-docs.cerebras.ai/support/error>,
  <https://inference-docs.cerebras.ai/api-reference/models/list-models>
* Base `https://api.cerebras.ai/v1`, `POST /chat/completions`.  **verified**
* `Authorization: Bearer $CEREBRAS_API_KEY`.  **verified**
* `GET /v1/models` returns `id`, `object`, `created` and `owned_by`.  The
  **price of a model is not in the schema**, so the free models cannot be
  found by their price.  **verified (URL and fields)**
* The free models (`gpt-oss-120b`, `qwen-3.8-27b`) get **5 requests per
  minute**, 1000000 tokens per day, 30000 uncached tokens per minute and
  1000000 tokens per hour.  The **number of requests per day is
  UNVERIFIED**.  **verified**
* `response_format` (`json_object` and `json_schema`) and `seed` are
  supported.  **verified**
* The rate limit is `HTTP 429`.  The **headers and the shape of the body
  are UNVERIFIED**.  **verified (status)**
* `HTTP 402` exists in the error mapping of Cerebras (`PaymentRequired`).
  When it happens on a free tier is **UNVERIFIED**.  **verified (status)**
* The context of the free models is 64k or 65k tokens.  **verified**

### Mistral

* Pages: <https://docs.mistral.ai/api/>,
  <https://docs.mistral.ai/resources/error-glossary>,
  <https://docs.mistral.ai/admin/billing-usage/usage-limits>,
  <https://docs.mistral.ai/models>
* Base `https://api.mistral.ai/v1`, `POST /chat/completions`.  **verified**
* `Authorization: Bearer $MISTRAL_API_KEY`.  **verified**
* `GET /v1/models` lists the models.  The **price of a model is
  UNVERIFIED**.  **verified (URL)**
* The **limits of the free tier are UNVERIFIED**: the documentation says
  that the limits are shown on a "Limits" page of the console and names
  the dimensions (requests per second, tokens per minute, tokens per
  month), but publishes no number for the free tier.  **unverified**
* `response_format` (`text`, `json_object`, `json_schema`) is supported.
  There is **no `seed`**: the parameter is called **`random_seed`**.  **verified**
* The rate limit is `HTTP 429` with the body
  `{"object": "error", "message": ..., "type": "rate_limit_error", ...}`.
  **verified**
* `HTTP 402` is documented as a billing error (credits exhausted, spending
  limit reached, failed invoice).  Whether it can happen on a free tier is
  **UNVERIFIED**.  **verified (status and meaning)**
* The small models have a context of 32k tokens.  **verified**

### Google AI Studio

* Pages: <https://ai.google.dev/gemini-api/docs/openai>,
  <https://ai.google.dev/gemini-api/docs/rate-limits>,
  <https://ai.google.dev/gemini-api/docs/api-errors>,
  <https://ai.google.dev/gemini-api/docs/billing>
* Base `https://generativelanguage.googleapis.com/v1beta/openai`,
  `POST /chat/completions`.  **verified**
* `Authorization: Bearer $GEMINI_API_KEY`.  **verified**
* `GET /v1beta/openai/models` lists the models.  The **price of a model is
  UNVERIFIED**: the schema of the native API has the token limits but no
  cost field.  **verified (URL)**
* The **numeric limits of the free tier**: the documentation says that
  they depend on the tier and are shown in AI Studio, and it publishes no
  number.  Two facts are documented: the limits apply **per project, not
  per key**, and the daily count is **reset at midnight Pacific time**.
  **verified**
* The **daily limit of the free tier is 500 requests per model**, and the
  answer of the provider says so when the quota is spent:

  ```text
  HTTP 429 - "Quota exceeded for metric:
  generativelanguage.googleapis.com/generate_content_free_tier_requests,
  limit: 500, model: gemini-3.5-flash-lite.
  Please retry in 6h56m14.06411813s."
  ```

  The limit is **per model**: `gemini-3.6-flash` was refused while
  `gemini-3.5-flash-lite` still answered.  The day of the provider turns
  at **midnight Pacific time** (07:00 UTC), and not at midnight UTC: a
  run that starts at 00:10 UTC meets the quota of the day that is ending.
  **verified (the answer of the provider, 2026-10-21)**
* The **token limit of the free tier is still UNVERIFIED**: the answer of
  the provider names the request metric and the number of requests, and
  not a number of tokens.  The runs of this project impose a token cap
  of their own (250 000 tokens for the Google model).
* `response_format` is a supported parameter of the chat completions.
  Whether the mode `{"type": "json_object"}` is accepted for the chat is
  **UNVERIFIED**.  **verified (parameter), UNVERIFIED (mode)**
* There is **no `seed` for the chat completions**: `seed` only appears for
  the video generation.  **verified**
* The rate limit is `HTTP 429` with the codes `rate_limit_exceeded`,
  `quota_exceeded` and `too_many_requests`.  The **rate limit headers are
  UNVERIFIED**.  **verified**
* `HTTP 402` is documented: an account with a Prepay balance of zero gets
  `402 Payment Required` on every key of the billing account.  The plain
  free tier without a billing account is not described as returning 402.
  **verified**
* The names of the usage fields in the OpenAI compatible answer are
  **UNVERIFIED**: the native API uses `total_tokens`,
  `total_input_tokens` and `total_output_tokens`.  The layer reads
  `prompt_tokens` and `completion_tokens`; if the provider answers with
  the native names, the token count of that provider is zero.

### Ollama (local)

* Pages: <https://docs.ollama.com/api/openai-compatibility>,
  <https://docs.ollama.com/api>
* Base `http://localhost:11434/v1`, `POST /chat/completions`.  **verified**
* **No key is needed** for a local server.  **verified**
* **The setup of this machine** (2026-10-21): the Windows bundle
  (`ollama-windows-amd64.zip`, 1.47 GB) is extracted in
  `<HOME>/ollama` and the server runs as the user, with
  `OLLAMA_MODELS=<HOME>/ollama-models` and
  `OLLAMA_NUM_PARALLEL=4`.  The model of the trial is
  `qwen2.5:1.5b-instruct` (986 MB, Q4_K_M), which runs **entirely in the
  VRAM** of the GeForce RTX 3050 of the machine.  The total of the
  downloads is 2.46 GB.  **verified (the machine)**
* `GET /v1/models` returns `created` and `owned_by`.  The **price of a
  model is UNVERIFIED**.  **verified (URL and fields)**
* A local server has **no quota**.  **verified (absence)**
* `response_format` and `seed` are supported.  **verified**
* The **rate limit status, the body and the headers are UNVERIFIED**: the
  documentation does not describe them.  **verified**
* The names of the usage fields in the answer are **UNVERIFIED**.

## What the layer does with the differences

* The **base URL** and the **path** are in the preset, never
  concatenated by hand.
* The **seed** is sent under the name of the provider (`seed`,
  `random_seed`, or not at all).  A provider without a seed is called
  without one; the temperature is 0 instead.
* The **free models** are discovered live from the catalogue of the
  provider: by the price when the catalogue has one (OpenRouter), by the
  free marker of the name when it does not.  No model id is hard-coded in
  the library.
* The **rate** is kept under the limit of the provider by a token bucket,
  and the **daily count** is kept under the limit by a counter that is
  written to disk with an atomic replace.  A run that is interrupted and
  continued does not start the day from zero.
* **401, 403 and 402 are never retried**: another attempt would fail the
  same way and would burn the quota.
* The **key** is read from the environment only.  It is never written to a
  file, never passed on a command line, never logged and never in an
  error message: every message that could echo the server answer goes
  through a redaction step first.  There is a test for every provider.

## The state of the live tests

The live tests are opt-in: `AGENTETHER_LIVE_TESTS=1` runs them, the
normal test run never touches the network.  The live tests of the
providers that had a key on this machine were run on 2026-10-20; the
result is in `docs/WORKLOG.md` and in the final report.
