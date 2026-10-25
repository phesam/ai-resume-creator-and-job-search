# ATS / Careers-Site API Reference (verified live)

Research date: 2026-10-02. All endpoints are public (no API keys). Requests made with a normal
desktop Chrome User-Agent: `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36`.

Status legend: **VERIFIED** = called live today and got real job data back. **PARTIAL** = some parts verified.
**BLOCKED** = public access blocked / needs browser. **UNVERIFIED** = documented from knowledge only.

Already covered elsewhere (existing adapters): Greenhouse, Lever, Ashby, Workday CXS, SmartRecruiters, Workable, Recruitee.

**Global gotchas (apply to every adapter):**
- **Force `Accept-Encoding: gzip, deflate`.** With `requests` 2.32 + urllib3 2.x + the `zstandard` package installed, requests advertises
  `zstd`; amazon.jobs and metacareers.com then answer with `content-encoding: zstd` and decoding **fails** on larger bodies
  (`ContentDecodingError ... cannot use a decompressobj multiple times`). Sending `gzip, deflate` fixed it.
- Always check `status_code` before `.json()` — several APIs return HTML error pages (429/400/403) with 200-looking flows.
- In the snippets below `UA` = the Chrome UA string above; `import requests, json, re` assumed.

> Status: COMPLETE (2026-10-02). Every `Python` snippet in this file was executed end-to-end on 2026-10-02 and returned live jobs (20/20).

## Summary table

| # | Target | Platform | Status | Endpoint |
|---|--------|----------|--------|----------|
| 1 | Amazon | amazon.jobs custom (iCIMS-backed) | **VERIFIED** | `GET https://www.amazon.jobs/en/search.json` |
| 2 | Microsoft | Eightfold PCSX (apply.careers.microsoft.com) | **VERIFIED** (rate-limited) | `GET https://apply.careers.microsoft.com/api/pcsx/search` |
| 3 | Apple | jobs.apple.com custom | **VERIFIED** | `POST https://jobs.apple.com/api/v1/search` (+CSRF) |
| 4 | Google | Google Careers (boq / batchexecute) | **VERIFIED** | `POST .../_/HiringCportalFrontendUi/data/batchexecute?rpcids=r06xKb` or HTML `ds:1` |
| 5 | Meta | metacareers.com Relay GraphQL | **VERIFIED** (doc_id rotates) | `POST https://www.metacareers.com/graphql` (doc_id 27807005005556827) + JSON-LD on job pages |
| 6a | Eightfold (classic v2) — e.g. Netflix | Eightfold | **VERIFIED** | `GET https://explore.jobs.netflix.net/api/apply/v2/jobs?domain=netflix.com` |
| 6a' | Eightfold (PCSX) — e.g. Qualcomm, Microsoft | Eightfold | **VERIFIED** | `GET https://careers.qualcomm.com/api/pcsx/search?domain=qualcomm.com` |
| 6b | Phenom — e.g. Thermo Fisher, Activision | Phenom People | **VERIFIED** | `POST https://jobs.thermofisher.com/widgets` (ddoKey refineSearch / jobDetail) |
| 6c | Oracle Recruiting Cloud — e.g. JPMorgan Chase | Oracle HCM CE REST | **VERIFIED** | `GET https://{pod}.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions` |
| 6d | iCIMS — e.g. Peraton | iCIMS (HTML + JSON-LD, no JSON API) | **VERIFIED** | `GET https://careers-{co}.icims.com/jobs/search?pr=N&in_iframe=1` + job page JSON-LD |
| 6e | SAP SuccessFactors Career Site Builder — e.g. Nestlé | SuccessFactors RMK/CSB (HTML, RSS, sitemap) | **VERIFIED** | `GET https://{site}/search/?q=&sortColumn=referencedate&sortDirection=desc&startrow=N` + `/sitemap.xml` |
| 6f | Jobvite — e.g. Nutanix | Jobvite (HTML only) | **VERIFIED** (no dates) | `GET https://jobs.jobvite.com/{co}/jobs` |
| 6g | BambooHR — e.g. Scribd | BambooHR | **VERIFIED** | `GET https://{co}.bamboohr.com/careers/list` + `/careers/{id}/detail` |
| 6h | Pinpoint — e.g. Thought Machine | Pinpoint | **VERIFIED** | `GET https://{co}.pinpointhq.com/postings.json` |
| 6i | Rippling ATS — e.g. Rippling | Rippling | **VERIFIED** | `GET https://ats.rippling.com/api/v2/board/{slug}/jobs?page=0&pageSize=500` |
| 6j | Gem — e.g. Gem | Gem | **VERIFIED** | `GET https://api.gem.com/job_board/v0/{slug}/job_posts/` |
| 6k | Dover — e.g. Dover | Dover | **VERIFIED** | `GET https://app.dover.com/api/v1/careers-page-slug/{slug}` → `/api/v1/careers-page/{client_id}/jobs` |
| 6l | Teamtailor — e.g. Teamtailor, Kry | Teamtailor | **VERIFIED** | `GET https://{careersite}/jobs.json` (JSON Feed) / `/jobs.rss` |
| 6m | Breezy HR — e.g. Attentive | Breezy | **VERIFIED** | `GET https://{co}.breezy.hr/json?verbose=true` |
| 6n | JazzHR | JazzHR (applytojob.com) | **PARTIAL** (no live tenant with openings found) | `GET https://{co}.applytojob.com/apply` (HTML) |
| 6o | Radancy TalentBrew front-ends — e.g. Disney, Intuit | Radancy (TalentBrew) | **VERIFIED** | `GET https://{site}/{lang}/search-jobs/results?...RecordsPerPage=100&CurrentPage=N` |
| 6p | Kenexa/IBM BrassRing — e.g. General Atomics | BrassRing TG New UI | **VERIFIED** | `POST https://sjobs.brassring.com/TgNewUI/Search/Ajax/MatchedJobs` |
| 7 | SoCal employers (Snap, Disney, Lockheed, GA, Qualcomm, Intuit, Tesla, Blizzard/Activision, Riot, NG, Boeing, RTX) | mixed | see §7 | see §7 |

---

## 1. Amazon — amazon.jobs (custom search API) — VERIFIED 2026-10-02

- **Endpoint:** `GET https://www.amazon.jobs/en/search.json` (no auth, no cookies, plain UA works; JSON).
- **Pagination:** `offset` (0-based) + `result_limit` (**max 100**; 101+ returns `{"error":"Result limit cannot be greater than 100","jobs":null}`).
- **Hard cap:** `offset + result_limit` cannot exceed **10,000** (`{"error":"Cannot return more than 10000 results at once"}`).
  `hits` is also capped at 10000 for broad queries. Amazon currently has >10k jobs (USA facet alone = 13,446),
  so to get ALL jobs you must **partition**: loop `normalized_country_code[]`, and for USA loop `normalized_state_name[]`
  (largest state Washington ≈ 5.5k, under the cap). Get partition values from facets (below).
- **Sort:** `sort=recent` → server sorts by internal `CREATED_DATE DESCENDING` (default is `relevant`).
- **Filters (verified; `[]` must be URL-encoded as `%5B%5D` or passed as dict key `"x[]"` with requests):**
  - `normalized_country_code[]=USA` (ISO3) — e.g. USA, IND, GBR, CAN
  - `normalized_state_name[]=California` (full name) — CA = 2,373 jobs
  - `normalized_city_name[]=Irvine` — 96 jobs (matches any of a job's locations)
  - `category[]=software-development` (slug) — 2,660 jobs
  - `business_category[]=aws` (slug)
  - `schedule_type_id[]=Full-Time`
  - `base_query=machine learning` (keyword), `loc_query=...` + `latitude`,`longitude`,`radius=24km` (geo bounding box)
  - NOT working: `city[]=`, `state[]=`, `country[]=` (silently ignored). `country=USA` (no brackets) is accepted as a location facet.
- **Facets (for partition counts):** add `facets[]=normalized_country_code&facets[]=normalized_state_name&facets[]=business_category`
  → response `facets.normalized_country_code_facet = [{"USA":13446},{"IND":2347},...]` (counts are per location, so jobs with multiple locations count multiple times).
- **Total count field:** `hits` (exact when < 10000; capped at 10000 otherwise).
- **Response:** `{"error":null,"hits":N,"facets":{},"jobs":[...],"job_posting_search_request":"<json string echo of the parsed query>"}`.
  The `job_posting_search_request` echo is handy to confirm a filter was actually applied (`filterFacets`).
- **Job fields:** `id` (uuid), `id_icims` (numeric req id, use as stable key), `title`, `company_name`, `job_category`, `job_family`,
  `business_category`, `location` ("US, RI, Providence"), `normalized_location`, `city`, `state`, `country_code` (ISO3),
  `locations` (list of JSON-encoded strings with lat/long, `type` ONSITE/REMOTE, building codes), `job_schedule_type`,
  `job_path` ("/en/jobs/10567966/area-manager"), `url_next_step` (apply link), `team.label`, `is_intern`, `is_manager`, `source_system`.
- **Dates:** `posted_date` = human string shown on the site as "Posted ..." e.g. `"October  2, 2026"` (format `%B %e, %Y` — note the
  **double space** before single-digit days; normalize whitespace then `strptime("%B %d, %Y")`). `updated_time` = relative humanized
  age of last update (`"3 minutes"`, `"13 days"`, `"3 months"`). No ISO timestamp. NOTE: `sort=recent` orders by internal created date,
  and `posted_date` is NOT monotonic in that order (43/99 inversions seen) — use a safety margin for incremental "stop when older than X" logic.
- **Description:** included in search results — `description` (HTML with `<br/>`), `description_short` (plain, truncated),
  `basic_qualifications`, `preferred_qualifications` (HTML). No detail call needed.
- **URLs:** job page = `https://www.amazon.jobs` + `job_path`; apply = `url_next_step` (`https://account.amazon.jobs/jobs/<id_icims>/apply`).
  Detail page is HTML only (`/en/jobs/<id>.json` → 302).
- **Blocking:** none observed (~15 requests, plain UA). Be polite (≤1 req/s).
- **Python:**
  ```python
  requests.get("https://www.amazon.jobs/en/search.json", params={"result_limit":100,"offset":0,"sort":"recent","normalized_country_code[]":"USA","normalized_state_name[]":"California"}, headers={"User-Agent":UA,"Accept-Encoding":"gzip, deflate"}).json()["jobs"]
  ```

## 2. Microsoft — Eightfold "PCSX" at apply.careers.microsoft.com — VERIFIED 2026-10-02

- **Status of old endpoints:** `gcsservices.careers.microsoft.com/search/api/v1/search` is **dead** (TLS cert no longer matches host → connection error).
  `jobs.careers.microsoft.com` 301-redirects to `https://apply.careers.microsoft.com/`. The generic Eightfold v2 API
  (`/api/apply/v2/jobs?domain=microsoft.com`) returns **403 `{"message": "Not authorized for PCSX"}`** — Microsoft is on the newer PCSX API.
- **Search endpoint:** `GET https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=&location=&start=0&sort_by=timestamp`
  - `domain=microsoft.com` required. `query` = keywords. `location` = free text (e.g. `United States`, `California, United States`,
    `Irvine, CA, United States` → server adds `distance=160` and `includeRemote=1` automatically; see `data.appliedFilters`).
  - `sort_by=timestamp` (newest first by `postedTs`) or `relevance`.
- **Pagination:** `start` offset, **page size fixed at 10** (`page_size` > 10 → HTTP 400 `{"message": "Too many rows requested."}`;
  `num`, `limit`, `size`, `count`, `rows`, `pageSize` are ignored). Deep offsets work (start=2370 returned the last job).
  All jobs ≈ 2,374 → ~238 requests.
- **Total count field:** `data.count` (2,374 worldwide; 1,189 for `location=United States`; 255 for California).
- **Response:** `{"status":200,"error":{...},"data":{"positions":[...],"count":N,"filterDef":{facets, smartFilters, allFilters},"sortBy":..,"appliedFilters":{}}}`.
- **Position fields (search):** `id` (Eightfold position id, e.g. 1970393557014465), `displayJobId` / `atsJobId` (Microsoft job number "200058419"),
  `name` (title), `locations` (["United States, Washington, Redmond"]), `standardizedLocations` (["Redmond, WA, US"]), `department`,
  `workLocationOption` (onsite/hybrid/remote), `postedTs`, `creationTs`, `positionUrl` ("/careers/job/<id>"), `isHot`.
- **Dates:** `postedTs` = Unix **seconds** (UTC) of (latest) posting — this is what `sort_by=timestamp` orders by and what the site shows;
  `creationTs` = Unix seconds when the position was created (can be days earlier than `postedTs`).
- **Description (detail endpoint):** `GET https://apply.careers.microsoft.com/api/pcsx/position_details?position_id={id}&domain=microsoft.com&hl=en`
  → `data.jobDescription` (HTML: Overview / Responsibilities / Qualifications), `data.publicUrl`, `data.efcustomTextWorkSite` (["3 days / week in-office"]),
  `efcustomTextRequiredTravel`, `efcustomTextRoletype`, `efcustomTextEmploymentType` (["Full-Time"]), `efcustomTextTaDisciplineName`, plus all search fields.
- **URLs:** job page / apply = `https://apply.careers.microsoft.com/careers/job/{id}` (= `data.publicUrl`).
- **Rate limiting (IMPORTANT):** aggressive. ~6 rapid requests → **HTTP 429 "Please try again later"** (text/html). Even at 2.5 s spacing a
  429 appeared after ~10 requests. Use ≥4–5 s between calls, exponential backoff on 429, and incremental crawling
  (`sort_by=timestamp`, stop when `postedTs` < last-run watermark) rather than full re-crawls; fetch details only for new ids.
- **Python:**
  ```python
  requests.get("https://apply.careers.microsoft.com/api/pcsx/search", params={"domain":"microsoft.com","query":"","location":"United States","start":0,"sort_by":"timestamp"}, headers={"User-Agent":UA,"Accept":"application/json"}).json()["data"]  # ["positions"], ["count"]
  ```

## 3. Apple — jobs.apple.com (custom API, CSRF) — VERIFIED 2026-10-02

- **Step 1 (CSRF):** `GET https://jobs.apple.com/api/v1/CSRFToken` → response header `x-apple-csrf-token: <hex>` and sets
  cookies `jssid`, `jobs`, `AWSALBAPP-0` (keep them — use a `requests.Session`). (Old `/api/csrfToken` now 301s; old `/api/role/search` is 404.)
- **Step 2 (search):** `POST https://jobs.apple.com/api/v1/search` with headers `x-apple-csrf-token`, `Origin: https://jobs.apple.com`,
  `Referer: https://jobs.apple.com/en-us/search`, JSON body:
  ```json
  {"query":"","filters":{"locations":["postLocation-USA"]},"page":1,"locale":"en-us","sort":"newest",
   "format":{"longDate":"MMMM D, YYYY","mediumDate":"MMM D, YYYY"}}
  ```
  **GOTCHAS (both fail silently with HTTP 200 + `{"searchResults":[],"totalRecords":0}`):** (a) missing CSRF token/cookies,
  (b) missing `format` object in the body. Always assert `totalRecords > 0` on page 1.
- **Pagination:** `page` (1-based), fixed **20 per page**; last page = ceil(totalRecords/20) (USA: 4,532 → page 227 had 12). Deep pages work.
- **Total count field:** `res.totalRecords` (all locations: 6,214; USA: 4,532; California: 3,056 — CA includes nationwide "United States" roles).
- **Filters:** `filters.locations` takes postLocation ids. `postLocation-USA` (country). Look up others with
  `GET https://jobs.apple.com/api/v1/refData/postlocation?input=california&locale=en-us` → `postLocation-state953` = California;
  `input=Irvine` → `postLocation-IRV` (Irvine, CA). `{}` filters = worldwide. `query` = keyword (broad full-text match).
  `sort`: `newest` (verified; the UI also offers relevance — value not verified).
- **Result fields:** `id` ("PIPE-114438158" / "200674218"), `positionId` (stable key), `reqId`, `postingTitle`, `transformedPostingTitle` (slug),
  `jobSummary` (plain text summary — not full description), `locations[]` (`name`, `city`, `stateProvince`, `countryName`, `postLocationId`),
  `team.teamName/teamCode`, `type` ("REQ" or "PIPE"), `managedPipelineRole`, `homeOffice`, `isMultiLocation`, `standardWeeklyHours`.
- **Dates:** `postDateInGMT` ISO-8601 UTC (e.g. `2026-10-01T21:05:13.210Z`) = posting date/time; `postingDate` formatted ("Oct 01, 2026").
  Managed-pipeline/evergreen roles (`managedPipelineRole: true`, e.g. Retail "Specialist") get **re-stamped to ~now** on every request —
  treat their date as unreliable.
- **Description (detail endpoint):** `GET https://jobs.apple.com/api/v1/jobDetails/{positionId}?locale=en-us` (no CSRF needed) →
  `res.description`, `res.responsibilities`, `res.minimumQualifications`, `res.preferredQualifications`, `res.jobSummary`,
  `res.postingFooters` (pay & benefits text incl. salary range), `res.postDateInGMT`, `res.postingDateMeta` ("2026-10-01"), `res.employmentType`, `res.jobType`.
- **URLs:** job page `https://jobs.apple.com/en-us/details/{positionId}/{transformedPostingTitle}` (bare `/details/{positionId}` 301-redirects to it);
  apply `https://jobs.apple.com/app/en-us/apply/{positionId}` (redirects to Apple ID sign-in).
- **Blocking:** none observed (~12 requests). CSRF token/cookie appears valid ~30 min (`jssid` expiry).
- **Python:**
  ```python
  s=requests.Session(); s.headers["User-Agent"]=UA; tok=s.get("https://jobs.apple.com/api/v1/CSRFToken").headers["x-apple-csrf-token"]; res=s.post("https://jobs.apple.com/api/v1/search", headers={"x-apple-csrf-token":tok,"Origin":"https://jobs.apple.com","Referer":"https://jobs.apple.com/en-us/search"}, json={"query":"","filters":{"locations":["postLocation-USA"]},"page":1,"locale":"en-us","sort":"newest","format":{"longDate":"MMMM D, YYYY","mediumDate":"MMM D, YYYY"}}).json()["res"]  # res["searchResults"], res["totalRecords"]
  ```

## 4. Google — google.com/about/careers (no public JSON API; batchexecute RPC + embedded data) — VERIFIED 2026-10-02

- The old `https://careers.google.com/api/v3/search/` is **404**. Two working options:
- **Option A (recommended, ~130 KB/page): batchexecute RPC `r06xKb`**
  - `POST https://www.google.com/about/careers/applications/_/HiringCportalFrontendUi/data/batchexecute?rpcids=r06xKb&source-path=/about/careers/applications/jobs/results/&hl=en-US&rt=c`
  - Header `Content-Type: application/x-www-form-urlencoded;charset=UTF-8`; form body `f.req=<json>` where
    `f.req = [[["r06xKb", json.dumps(REQ), null, "generic"]]]` and
    `REQ = [[QUERY_or_null, null, null, null, "en-US", null, [["United States"]] or null, PAGE, null, null, SORT]]`
    (verified: idx0 = keyword query, idx6 = list of location strings, idx7 = page 1-based, idx10 = `1` → sort by date, `null` → relevance).
    No cookies / `f.sid` / `bl` needed.
  - Response is Google's chunked format: strip the `)]}'` prefix line + length line, `json.loads` the first chunk line, find the
    element `["wrb.fr","r06xKb","<payload json string>",...]` and `json.loads(element[2])`.
- **Option B: HTML page** `GET https://www.google.com/about/careers/applications/jobs/results/?location=United%20States&sort_by=date&page=2`
  (~1.2 MB). Regex `AF_initDataCallback\(\{key: 'ds:1', hash: '\d+', data:(.*?), sideChannel: \{\}\}\);</script>` → `json.loads(group1)`.
  (`ds:0` = list of companies: Google, DeepMind, GFiber, ...). Other URL params: `q=`, `location=` (repeatable), `page=`, `sort_by=date`.
- **Payload shape (same for A and B):** `[jobs[20], null, TOTAL, PAGE_SIZE(20)]`.
  - **Total count:** `payload[2]` (US: 1,857; worldwide: 3,367; `q="software engineer"`+US: 957). **Page size fixed 20**; pages past the end return `[]`
    (US last page = 93 with 17 jobs).
- **Job array (positional; verified by inspection):**
  `[0]` job id ("112598809917170374"), `[1]` title, `[2]` apply URL (`.../applications/signin?jobId=...`), `[3][1]` responsibilities HTML,
  `[4][1]` qualifications HTML (minimum + preferred), `[5]` company resource name, `[7]` company name ("Google", "DeepMind", ...),
  `[8]` language, `[9]` locations list of `[display, [address], city, zip, state, country]`, `[10][1]` "About the job" description HTML,
  `[11]` list of ints — likely degree levels (2=Bachelor's, 3=Master's, 4=PhD; inferred), `[12]`/`[13]`/`[14]` timestamps as `[unix_seconds, nanos]`,
  `[15][1]` legal/fair-chance text, `[18][1]` preferred-location note, `[19][1]` minimum qualifications HTML, `[20]` (optional) int — likely experience level
  (inferred). Arrays can be length 20 or 21 → always index defensively.
- **Dates:** `[12]` = creation / first-posted time (e.g. 2026-09-24 for a job whose `[13]` is 2026-10-02); `[13]` (≈`[14]`) = last updated /
  republished time — `sort_by=date` orders by `[13]` DESC. Use `[12]` as "posted date", `[13]` as "updated".
- **Description:** fully included in search results (`[10]`, `[3]`, `[4]`/`[19]`) — no detail call needed.
- **URLs:** job page `https://www.google.com/about/careers/applications/jobs/results/{id}` (slug optional, e.g. `{id}-senior-product-manager-...`);
  apply = `[2]`.
- **Blocking:** none seen (~10 requests at ~1.5 s). Google may show CAPTCHA/429 under heavy load — keep ≥1–2 s spacing.
- **Python (Option A):**
  ```python
  t=requests.post("https://www.google.com/about/careers/applications/_/HiringCportalFrontendUi/data/batchexecute", params={"rpcids":"r06xKb","source-path":"/about/careers/applications/jobs/results/","hl":"en-US","rt":"c"}, data={"f.req":json.dumps([[["r06xKb",json.dumps([[None,None,None,None,"en-US",None,[["United States"]],1,None,None,1]]),None,"generic"]]])}, headers={"User-Agent":UA}).text; payload=json.loads(next(e for e in json.loads(t[t.index("[["):].split("\n")[0]) if e[0]=="wrb.fr")[2])  # payload[0]=jobs, payload[2]=total
  ```

## 5. Meta — metacareers.com (Relay GraphQL + JSON-LD job pages) — VERIFIED 2026-10-02

- **Gotcha:** plain `curl` with only a UA gets **HTTP 400 "Sorry, something went wrong"**. Send full browser navigation headers
  (`Accept: text/html,...`, `Accept-Language`, `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Site: none`, `Sec-Fetch-Dest: document`,
  `Sec-Fetch-User: ?1`, `Upgrade-Insecure-Requests: 1`). `/jobs` 301 → `/jobsearch/`.
- **Step 1 (token):** `GET https://www.metacareers.com/jobsearch/` (nav headers, keep cookies `datr`,`ps_l`,`ps_n`) and regex
  `"LSD",\[\],\{"token":"([^"]+)"` → `lsd`.
- **Step 2 (all jobs, ONE call, no pagination):** `POST https://www.metacareers.com/graphql`, form-encoded:
  - `lsd=<lsd>`, `fb_api_caller_class=RelayModern`, `fb_api_req_friendly_name=CPJobSearchSourceQuery`, `doc_id=27807005005556827`, `server_timestamps=true`,
  - `variables={"search_input":{"q":"","divisions":[],"offices":[],"roles":[],"leadership_levels":[],"saved_jobs":[],"saved_searches":[],"sub_teams":[],"teams":[],"is_leadership":false,"is_remote_only":false,"sort_by_new":true,"results_per_page":null}}`
  - headers: `X-FB-LSD: <lsd>`, `X-FB-Friendly-Name: CPJobSearchSourceQuery`, `Origin: https://www.metacareers.com`, `Referer: https://www.metacareers.com/jobsearch/`,
    **`Sec-Fetch-Site: same-origin`, `Sec-Fetch-Mode: cors`, `Sec-Fetch-Dest: empty` — REQUIRED** (without them the POST returns HTTP 400 HTML).
  - Response (content-type says text/html but body is JSON): `data.job_search_with_featured_jobs.all_jobs[]` = `{id, title, locations[]}` —
    **1,063 jobs** returned in one ~137 KB response. Also `matching_teams`. Filters go in `search_input` (`offices` e.g. `["Menlo Park, CA"]`, `q`, `teams`, `is_remote_only`).
  - **Total count:** `len(all_jobs)` (no count field).
  - **doc_id stability:** `doc_id` is a persisted-query id that changes when Meta redeploys. Discover it dynamically: the jobsearch page HTML
    lists ~10 `static.xx.fbcdn.net/rsrc.php/...js` bundles; grep them for
    `__d("CPJobSearchSourceQuery_candidate_portalRelayOperation",[],(function(t,n,r,o,a,i){a.exports="(\d+)"})`.
    (The older `CareersJobSearchResultsDataQuery` is still referenced but its doc id is lazy-loaded; `CPJobSearchQuery` 27808175508766384 is a different, non-search query.)
- **Dates + description (per job):** `GET https://www.metacareers.com/jobs/{id}/` (nav headers) → 302 to `/profile/job_details/{id}/` (~500 KB HTML) containing
  `<script type="application/ld+json">` **JobPosting** with `datePosted` (ISO-8601 with offset, e.g. `2026-10-02T09:07:19-07:00`), `description`,
  `responsibilities`, `qualifications`, `jobLocation[]` (PostalAddress with locality/region/country), `employmentType` (FULL_TIME), `identifier.value`
  (internal req id), `directApply`. No `baseSalary` / `validThrough` in JSON-LD. The search call has **no date field**, so dates require one page fetch per job
  (cache by id; only fetch new ids).
- **URLs:** job/apply page `https://www.metacareers.com/jobs/{id}/` (canonical `https://www.metacareers.com/profile/job_details/{id}/`).
- **Blocking:** works from a residential IP with browser headers (~6 requests). Meta is bot-sensitive: keep it to 1 search call/day + incremental detail
  fetches at ≥2 s spacing; expect occasional 400/checkpoint pages.
- **Python:**
  ```python
  s=requests.Session(); NAV={"User-Agent":UA,"Accept-Encoding":"gzip, deflate","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9","Sec-Fetch-Mode":"navigate","Sec-Fetch-Site":"none","Sec-Fetch-Dest":"document","Sec-Fetch-User":"?1","Upgrade-Insecure-Requests":"1"}; lsd=re.search(r'"LSD",\[\],\{"token":"([^"]+)"', s.get("https://www.metacareers.com/jobsearch/", headers=NAV).text).group(1); jobs=s.post("https://www.metacareers.com/graphql", headers={"User-Agent":UA,"X-FB-LSD":lsd,"Origin":"https://www.metacareers.com","Referer":"https://www.metacareers.com/jobsearch/","Sec-Fetch-Site":"same-origin","Sec-Fetch-Mode":"cors","Sec-Fetch-Dest":"empty","Accept-Encoding":"gzip, deflate"}, data={"lsd":lsd,"fb_api_caller_class":"RelayModern","fb_api_req_friendly_name":"CPJobSearchSourceQuery","doc_id":"27807005005556827","variables":json.dumps({"search_input":{"q":"","divisions":[],"offices":[],"roles":[],"leadership_levels":[],"saved_jobs":[],"saved_searches":[],"sub_teams":[],"teams":[],"is_leadership":False,"is_remote_only":False,"sort_by_new":True,"results_per_page":None}})}).json()["data"]["job_search_with_featured_jobs"]["all_jobs"]
  ```

## 6a. Eightfold (generic) — two API generations — VERIFIED 2026-10-02

Every Eightfold tenant serves exactly ONE of two APIs; the other returns HTTP 403 with a telltale message. Adapter logic: try PCSX → if
403 `"PCSX is not enabled for this user."` use classic v2; if v2 returns 403 `"Not authorized for PCSX"` use PCSX.

| Tenant | Host | `domain=` | API | Verified count |
|---|---|---|---|---|
| Netflix | `explore.jobs.netflix.net` | `netflix.com` | classic v2 | 470 |
| Qualcomm | `careers.qualcomm.com` | `qualcomm.com` | PCSX | 2,044 (San Diego 684) |
| Microsoft | `apply.careers.microsoft.com` | `microsoft.com` | PCSX | 2,374 (see §2) |
| Lockheed Martin | `lockheedmartin.eightfold.ai` | `lockheedmartin.com` | PCSX | 5,560 (California 760) |
| Northrop Grumman | `jobs.northropgrumman.com` | `ngc.com` | PCSX | 3,755 (front-end over Workday) |

### Classic v2 (Netflix)
- **Search:** `GET https://{host}/api/apply/v2/jobs?domain={domain}&start=0&num=10&sort_by=timestamp` (+ optional `query=`, `location=` e.g. `Los Angeles, California, United States` → 140).
- **Pagination:** `start` offset; **page size fixed at 10** (`num=20/50/100` still return 10). Deep paging fine (start=460 of 470 OK).
- **Total:** top-level `count`. Positions in `positions[]` (response also carries lots of site-config keys — ignore).
- **Fields:** `id` (Eightfold position id), `ats_job_id`/`display_job_id` (e.g. "AJRT30201"), `name`/`posting_name`, `location`, `locations[]`,
  `department`, `business_unit`, `work_location_option`, `hot` (pinned jobs come first even with sort_by=timestamp), `canonicalPositionUrl`, `type` ("ATS").
- **Dates:** `t_create` (Unix seconds, day granularity = first posted) and `t_update` (Unix seconds, last update). `sort_by=timestamp` → newest `t_create` first (after `hot` jobs).
- **Description:** `job_description` is `""` in search results → **detail** `GET https://{host}/api/apply/v2/jobs/{id}?domain={domain}` → `job_description` (HTML, ~8 KB), `custom_JD`, `urls`.
- **URLs:** `https://{host}/careers/job/{id}` (= `canonicalPositionUrl`; apply from there).
- **Python:** `requests.get("https://explore.jobs.netflix.net/api/apply/v2/jobs", params={"domain":"netflix.com","start":0,"num":10,"sort_by":"timestamp"}, headers={"User-Agent":UA}).json()["positions"]`

### PCSX (Qualcomm, Microsoft)
- **Search:** `GET https://{host}/api/pcsx/search?domain={domain}&query=&location=&start=0&sort_by=timestamp` → `data.positions[]`, `data.count`.
  Page size fixed 10 (`page_size` > 10 → 400 "Too many rows requested."). `location` free text (e.g. `San Diego, California, United States`).
- **Fields:** `id`, `displayJobId`/`atsJobId`, `name`, `locations`, `standardizedLocations`, `department`, `workLocationOption`, `postedTs`, `creationTs`, `positionUrl`.
- **Dates:** `postedTs` = Unix seconds of latest (re)post — at Qualcomm it is day-granular and many old reqs (creationTs = June 2026) show postedTs = today,
  i.e. Qualcomm **refreshes postedTs**; use `creationTs` as the true "first posted" date and `postedTs` as "last refreshed".
- **Detail:** `GET https://{host}/api/pcsx/position_details?position_id={id}&domain={domain}&hl=en` → `data.jobDescription` (HTML), `data.publicUrl`.
- **URLs:** `https://{host}/careers/job/{id}`.
- **Rate limiting:** Eightfold returns **429 "Please try again later"** (sometimes as a non-JSON body) after short bursts; the limit appears to apply per IP
  across tenants. Use ≥5 s spacing + backoff; always check `status_code` before `.json()`.
- **Python:** `requests.get("https://careers.qualcomm.com/api/pcsx/search", params={"domain":"qualcomm.com","query":"","location":"","start":0,"sort_by":"timestamp"}, headers={"User-Agent":UA}).json()["data"]["positions"]`

## 6b. Phenom People (generic) — VERIFIED 2026-10-02 on Thermo Fisher (`jobs.thermofisher.com`)

- **Detect:** HTML contains `phApp.ddo = {...}` / `cdn.phenompeople.com`; config values in HTML: `"refNum":"TFSCGLOBAL"`, `"pageId":"page13"`,
  `"locale":"en_global"`, `"csrfToken":"..."`, and `eagerLoadRefineSearch":{"status":200,"hits":10,"totalHits":2938` (first page is server-rendered).
  Other Phenom tenants seen: `careers.activision.com` (Activision Blizzard).
- **Search:** `POST https://{host}/widgets` JSON body:
  ```json
  {"lang":"en_global","deviceType":"desktop","country":"global","pageName":"search-results","ddoKey":"refineSearch",
   "sortBy":"","subsearch":"","from":0,"jobs":true,"counts":true,"all_fields":["category","country","state","city","type"],
   "size":100,"clearAll":false,"jdsource":"facets","isSliderEnable":false,"pageId":"page13","siteType":"external",
   "keywords":"","global":true,"selected_fields":{},"locationData":{}}
  ```
  `lang`/`country` must match the site path (`/global/en/` → `en_global`/`global`; US-only sites use e.g. `en_us`/`us`). `pageId` from HTML.
  Filters: `selected_fields` e.g. `{"country":["United States of America"],"state":["California"]}` (verified → 114 jobs; matches any of a job's locations); keyword via `keywords`.
  Facet values/counts come back in `refineSearch.data.aggregations[]` when `"counts":true` and `all_fields` lists the fields.
  CSRF header `x-csrf-token` + cookies (`PLAY_SESSION`, `PHPPPE_ACT`) were **not required** on this tenant (still send them if available — some tenants enforce).
- **Pagination:** `from` (offset) + `size`. `size=500` returned 500 rows (no cap hit); `from=2900,size=100` → last 38. Response `refineSearch.hits` = rows returned,
  `refineSearch.totalHits` = **total count** (2,938).
- **Sort:** `sortBy` values `"Most recent"`, `"Most relevant"` etc. had **no effect** on this tenant (order is stable but unsorted) → crawl everything and sort client-side.
- **Job fields (search):** `jobId`/`reqId` ("P-100223"), `jobSeqNo` ("TFSCGLOBALP100223EXTERNALENGLOBAL", needed for detail), `title`, `location`,
  `city`,`state`,`country`, `multi_location[]`, `category`, `type` ("Full-Time"), `descriptionTeaser` (short plain text), `ml_skills`, `externalApply`,
  `postedDate` ("2026-06-03T00:00:00.000+0000" = posting date, day-granular), `dateCreated` (exact ingest timestamp).
- **Detail (description):** same endpoint, body `{"lang":"en_global","deviceType":"desktop","country":"global","pageName":"job","ddoKey":"jobDetail","jobSeqNo":"<jobSeqNo>"}`
  → `jobDetail.data.job.description` (HTML), `postedDate`, `dateCreated`, `jobUpdatedDate`, `postedDateTrack[]`, `ats` (source ATS), `jobRequirements`, `benefits`.
- **URLs:** job page `https://{host}/{country}/{lang}/job/{jobId}` (slug optional, e.g. `/global/en/job/P-100223/Program-Documentation-Specialist-I`); apply button on that page.
- **Blocking:** none on Thermo Fisher (~10 calls). Some Phenom tenants sit behind Akamai/Cloudflare (e.g. `careers.rtx.com` returned **403** to curl).
- **Python:** `requests.post("https://jobs.thermofisher.com/widgets", json={"lang":"en_global","deviceType":"desktop","country":"global","pageName":"search-results","ddoKey":"refineSearch","sortBy":"","subsearch":"","from":0,"jobs":True,"counts":False,"all_fields":[],"size":100,"clearAll":False,"jdsource":"facets","isSliderEnable":False,"pageId":"page13","siteType":"external","keywords":"","global":True,"selected_fields":{},"locationData":{}}, headers={"User-Agent":UA}).json()["refineSearch"]  # ["data"]["jobs"], ["totalHits"]`

## 6c. Oracle Recruiting Cloud (HCM Candidate Experience REST) — VERIFIED 2026-10-02 on JPMorgan Chase

- **Tenant identification:** career site URL looks like `https://{pod}.fa.{dc}.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{siteNumber}/requisitions`
  (JPMC: host `jpmc.fa.oraclecloud.com`, `siteNumber=CX_1001`). Same host serves the REST API, no auth.
- **Search (list):**
  `GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber=CX_1001,limit=200,offset=0,sortBy=POSTING_DATES_DESC`
  - **`expand=requisitionList` (or `requisitionList.secondaryLocations`) is REQUIRED** — without it the `requisitionList` key is absent.
  - Finder params are `;`-then-`,`-separated inside `finder=` (use `curl -g` / don't let your client re-encode `;`,`,`). Useful ones:
    `keyword="software engineer"` (quoted, URL-encoded), `locationId=300000000289738` (= United States here; ids come from facets),
    `sortBy=POSTING_DATES_DESC` (verified), `facetsList=LOCATIONS` (verified; full list `LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS`),
    and the standard ORC facet selectors `selectedLocationsFacet=<id>`, `selectedCategoriesFacet=<id>`, `selectedPostingDatesFacet=7` (not individually verified; `locationId=` and `keyword=` were).
  - To get facet ids: add `facetsList=LOCATIONS` and `expand=requisitionList,locationsFacet` → `items[0].locationsFacet[] = {Id, Name, TotalCount}`
    (JPMC: United States 5,372; NY 1,209; TX 966 ...).
- **Pagination:** `offset` + `limit`; **max limit 200** (`limit=500` silently returns 200). Deep offsets OK (offset 7350 of 7358 → 8 rows).
- **Total count:** `items[0].TotalJobsCount` (JPMC 7,358; keyword "software engineer" + US 1,051).
- **List fields (`items[0].requisitionList[]`):** `Id` (requisition number, e.g. "210714035"), `Title`, `PostedDate` ("2026-10-02", date only),
  `PostingEndDate`, `PrimaryLocation` ("Columbus, OH, United States"), `PrimaryLocationCountry`, `secondaryLocations[]`, `JobFamily`, `JobFunction`,
  `WorkplaceType`/`WorkplaceTypeCode`, `ShortDescriptionStr` (1-sentence teaser), `HotJobFlag`, `Relevancy`.
- **Dates:** list `PostedDate` = external posting start date (date only). Detail `ExternalPostedStartDate` = full ISO timestamp (`2026-10-02T14:59:07+00:00`),
  `ExternalPostedEndDate` = scheduled unpost date (often null).
- **Detail (description):**
  `GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true&finder=ById;Id="{Id}",siteNumber=CX_1001`
  → `items[0].ExternalDescriptionStr` (HTML), `ExternalResponsibilitiesStr`, `ExternalQualificationsStr`, `CorporateDescriptionStr`, `OrganizationDescriptionStr`,
  `ExternalPostedStartDate`, `workLocation[]`, `otherWorkLocations[]`, `skills`, `requisitionFlexFields` (tenant-specific, e.g. pay range), `JobSchedule`, `WorkerType`.
- **URLs:** job + apply page `https://{host}/hcmUI/CandidateExperience/en/sites/{siteNumber}/job/{Id}` (200 verified).
- **Blocking:** none (~8 calls). Oracle REST is fast and unthrottled at low volume.
- **Python:** `requests.get("https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber=CX_1001,limit=200,offset=0,sortBy=POSTING_DATES_DESC", headers={"User-Agent":UA}).json()["items"][0]  # ["requisitionList"], ["TotalJobsCount"]`
  (pass the full URL string, NOT `params=`, so `;` and `,` stay literal).

## 6d. iCIMS — VERIFIED 2026-10-02 on Peraton (`careers-peraton.icims.com`); also live: `careers-lmi.icims.com`

- **No public JSON search API.** Scrape the server-rendered "iframe" search page + JSON-LD on job pages. (`/jobs/rss` and `mode=rss` just return HTML.)
- **Search page:** `GET https://careers-{co}.icims.com/jobs/search?ss=1&in_iframe=1&pr={page0}` (plain UA OK). `in_iframe=1` returns the bare list (no site chrome).
  - **50 jobs per page**; `pr` = 0-based page index. Total pages from pager text `of 30 , Current Page` (regex `of (\d+) , Current Page`). No total-jobs field
    (pages × 50 is an upper bound).
  - **Newest first:** `GET .../jobs/search?mode=redo&pr=0&schemaId=%24T%7BJob%7D.%24T%7BJobPost%7D.%24F%7BPostedDateTime%7D&o=A&in_iframe=1`
    (`schemaId=$T{Job}.$T{JobPost}.$F{PostedDateTime}`; **`o=A` = newest first** — iCIMS' Asc/Desc labels are inverted; `o=D` gives oldest first).
  - Filters: `searchKeyword=software` (verified: 30 → 14 pages; also matches description text), `searchLocation=` (tenant-specific id from the
    `<select name="searchLocation">`), `searchCategory=`, `searchPositionType=`, `searchZip=`+`searchRadius=` (select/input names from the form; not individually verified).
  - Row parsing: job links `https://careers-{co}.icims.com/jobs/{id}/{slug}/job?in_iframe=1` (anchor `title="{id} - {Title}"`), location cell after
    `<span class="sr-only field-label">Job Locations</span>` (e.g. `US-VA-Chantilly`), posted date after the `... Posted Date</span>` label as
    `<span title="10/2/2026 11:27 AM">58 minutes ago` (tenant-local time, `%m/%d/%Y %I:%M %p`). Which columns appear is **tenant-configurable**.
- **Detail / description:** `GET https://careers-{co}.icims.com/jobs/{id}/job?in_iframe=1` (slug optional) → one `<script type="application/ld+json">`
  **JobPosting**: `title`, `description` (HTML), `datePosted` (`2026-10-02T04:00:00.000Z` — date only, midnight tenant TZ in UTC), `validThrough`
  (iCIMS default = +1 year, not a real close date), `jobLocation[].address` (`addressLocality`/`addressRegion`/`postalCode`/`addressCountry`), `employmentType`,
  `occupationalCategory`, `hiringOrganization.name`, `url`.
- **Apply URL:** `https://careers-{co}.icims.com/jobs/{id}/{slug}/login` (the job page's Apply button); canonical job URL = JSON-LD `url`.
- **Tenant discovery:** subdomain patterns `careers-{co}.icims.com`, `jobs-{co}.icims.com`, `uscareers-{co}.icims.com`, `external-{co}.icims.com`
  (404 page = wrong guess). Many companies front iCIMS with their own domain and iframe it in.
- **Blocking:** none observed (~8 requests).
- **Python:** `html=requests.get("https://careers-peraton.icims.com/jobs/search", params={"ss":1,"in_iframe":1,"pr":0}, headers={"User-Agent":UA}).text; ids=sorted(set(re.findall(r'icims\.com/jobs/(\d+)/[^"/]+/job', html)))`

## 6e. SAP SuccessFactors Career Site Builder (RMK/CSB) — VERIFIED 2026-10-02 on Nestlé (`jobdetails.nestle.com`)

- **Note on jobs.sap.com itself:** it was rebuilt as a Next.js site (`/en/jobs/`), and its job ids (e.g. `744000153220909`) are **SmartRecruiters**
  posting ids (SAP acquired SmartRecruiters). Public SR API: `GET https://api.smartrecruiters.com/v1/companies/SAPITBusinessSysteme/postings` → 52 postings
  (the SR error message for a wrong company id reveals the right one: *"Provided companyIdentifier (SAP) does not match companyIdentifier (SAPITBusinessSysteme)"*).
  → use the existing SmartRecruiters adapter for SAP. The old `jobs.sap.com/search/` 301s to `/en/jobs/`.
- **No public JSON API** on CSB sites (`POST /services/recruiting/v1/jobs` → **401**). Three public sources instead:
  1. **Search HTML:** `GET https://{site}/search/?q=&sortColumn=referencedate&sortDirection=desc&startrow={offset}` — rows per page are tenant-configured
     (Nestlé 10; often 25). Total from `Results <b>1 – 10</b> of <b>2117</b>` (regex `of <b>([\d,]+)</b>`). Rows: `a.jobTitle-link[href="/job/{slug}/{id}/"]`,
     `span.jobDate` ("Oct 2, 2026" = reference/posting date), `span.jobLocation`. Keyword `q=`; other CSB filters (`locationsearch=`, `optionsFacetsDD_country=`) are standard but not verified here.
  2. **`/sitemap.xml`** — lists **every** open job URL with `<lastmod>` (Nestlé: 2,117 URLs = total). Cheapest way to enumerate all ids.
  3. **RSS:** `GET https://{site}/services/rss/job/?locale=en_US&keywords=` → newest **20** items with `title`, full HTML `description`, `pubDate`
     (`Fri, 02 Oct 2026 2:01:00 GMT`), `link`. No paging (`startrow` ignored); `keywords=()` errors. Good for incremental "what's new" polling.
- **Job page (description + exact date):** `GET https://{site}/job/{slug}/{id}/` → schema.org **microdata** (no JSON-LD): `itemprop="datePosted"
  content="Fri Oct 02 02:01:00 UTC 2026"`, `itemprop="title"`, `itemprop="description"` (HTML block), `itemprop="addressLocality|addressRegion|postalCode|addressCountry"`,
  `itemprop="hiringOrganization"`.
- **Apply URL:** the job page's apply button → `https://{site}/talentcommunity/apply/{id}/?locale=en_US` (standard CSB pattern; not opened).
- **Tenant detection:** HTML references `rmkcdn.successfactors.com`; classic (non-CSB) portals live at `https://career{N}.successfactors.com/career?company={id}` (JS app, harder).
- **Blocking:** none observed (~8 requests).
- **Python:** `html=requests.get("https://jobdetails.nestle.com/search/", params={"q":"","sortColumn":"referencedate","sortDirection":"desc","startrow":0}, headers={"User-Agent":UA}).text; rows=re.findall(r'class="jobTitle-link"[^>]*href="(/job/[^"]+/(\d+)/)"', html)`

## 6f. Jobvite — VERIFIED 2026-10-02 on Nutanix (`jobs.jobvite.com/nutanix`), Egnyte (`jobs.jobvite.com/egnyte`)

- **No public JSON API.** Legacy XML feed `https://app.jobvite.com/CompanyJobs/Xml.aspx?c={companyCode}` needs the internal company code
  (e.g. `qX1abcde`) and redirects to login when wrong — not usable without it.
- **List (all jobs, one page):** `GET https://jobs.jobvite.com/{co}/jobs` → HTML table(s) grouped by department; rows
  `<td class="jv-job-list-name"><a href="/{co}/job/{jobId}">Title</a></td><td class="jv-job-list-location">San Jose, California</td>`.
  Nutanix: ~117 unique jobs on one page, no pagination. Unknown `{co}` → 302 to `jobvite.com/support/job-seeker-support/?invalid=1`.
  (Some tenants use `https://jobs.jobvite.com/careers/{co}/jobs`; `/search?q=&l=` also works.)
- **Total count:** count unique `/{co}/job/{id}` links.
- **Detail:** `GET https://jobs.jobvite.com/{co}/job/{jobId}` → `div.jv-job-detail-description` (HTML), `p.jv-job-detail-meta`
  ("Accounting & Finance · San Jose, California · Req.Num.: 32541"). **No JSON-LD and no posted date anywhere** → record first-seen date yourself.
- **Apply URL:** `https://jobs.jobvite.com/{co}/job/{jobId}/apply`.
- **Python:** `ids=set(re.findall(r'href="/nutanix/job/([A-Za-z0-9]+)"', requests.get("https://jobs.jobvite.com/nutanix/jobs", headers={"User-Agent":UA}).text))`

## 6g. BambooHR — VERIFIED 2026-10-02 (endpoint shape on Scribd; also Thinkific/Toggl/Mozilla/Pipedrive return valid empty JSON)

- **List:** `GET https://{co}.bamboohr.com/careers/list` → `{"meta":{"totalCount":N},"result":[...]}` (all jobs, no pagination).
  Unknown/disabled tenants → 302 to HTML. Fields: `id` ("144"), `jobOpeningName`, `departmentId`, `departmentLabel`, `employmentStatusLabel`,
  `location{city,state}`, `atsLocation{country,state,province,city}`, `isRemote`, `locationType` ("0" seen for on-site; other values likely remote/hybrid — unverified). **No date in list.**
- **Total count:** `meta.totalCount`.
- **Detail:** `GET https://{co}.bamboohr.com/careers/{id}/detail` → `result.jobOpening`: `description` (HTML), **`datePosted`** ("2019-09-09", date only),
  `jobOpeningStatus` ("Open"), `location{city,state,postalCode,addressCountry}`, `compensation`, `minimumExperience`, `employmentStatusLabel`,
  `jobOpeningShareUrl`; plus `result.formFields` (application form).
- **URLs:** job + apply page `https://{co}.bamboohr.com/careers/{id}` (= `jobOpeningShareUrl`).
- **Python:** `requests.get("https://scribd.bamboohr.com/careers/list", headers={"User-Agent":UA}).json()["result"]`

## 6h. Pinpoint — VERIFIED 2026-10-02 on Thought Machine (`thoughtmachine.pinpointhq.com`)

- **List (all postings incl. descriptions):** `GET https://{co}.pinpointhq.com/postings.json` → `{"data":[...]}` (no pagination, no meta/count; unknown tenant → 404 HTML).
  Fields: `id`, `title`, `url` (`https://{co}.pinpointhq.com/en/postings/{uuid}`), `path`, `description`, `key_responsibilities`, `skills_knowledge_expertise`,
  `benefits` (all HTML, with matching `*_header` labels), `compensation`, `compensation_minimum/maximum/currency/frequency`, `compensation_visible`,
  `employment_type` (`full_time`), `workplace_type` (`onsite`/`remote`/`hybrid`), `deadline_at` (closing date or null),
  `job{id, requisition_id, department{name}, division{name}}`, `location{name, city, province, postal_code}`.
- **Dates:** **no posted date in postings.json.** The posting page `GET {url}` has JSON-LD JobPosting with `datePosted` (`2025-06-16T15:57:35+01:00`),
  `jobLocation`, `applicantLocationRequirements`, `identifier` (posting uuid).
- **Total count:** `len(data)`.
- **Apply URL:** `{url}` (apply button on the posting page).
- **Python:** `requests.get("https://thoughtmachine.pinpointhq.com/postings.json", headers={"User-Agent":UA}).json()["data"]`

## 6i. Rippling ATS — VERIFIED 2026-10-02 on Rippling's own board (slug `rippling`, 646 jobs)

- Board URL `https://ats.rippling.com/{slug}/jobs` (Rippling's own board redirects to its marketing site, but the API works).
- **v2 list (paged):** `GET https://ats.rippling.com/api/v2/board/{slug}/jobs?page=0&pageSize=500` → `{"items":[...],"page":0,"pageSize":500,"totalItems":646,"totalPages":2}`.
  `page` is 0-based; default pageSize 20; 500 verified. Items: `id` (uuid), `name`, `url`, `department.name`, `locations[]` (`name`, `country`, `countryCode`, `state`, `stateCode`, ...), `language`.
  (Same API also on `https://api.rippling.com/platform/api/ats/v2/board/{slug}/jobs`.)
- **v1 list (all at once):** `GET https://ats.rippling.com/api/v1/board/{slug}/jobs` → bare JSON array (646): `uuid`, `name`, `department{id,label}`, `url`, `workLocation{label,id}`.
- **Total count:** v2 `totalItems`. **No dates in lists.**
- **Detail:** `GET https://ats.rippling.com/api/v2/board/{slug}/jobs/{id}` (v1 identical) → `description.company` + `description.role` (HTML),
  **`createdOn`** (`2026-03-31T17:37:26.093000-07:00` = posting creation), `workLocations[]`, `employmentType{label,id}` ("SALARIED_FT"),
  `payRangeDetails[]` (`rangeStart`/`rangeEnd`/`currency`/`frequency`/`location`), `companyName`, `department.department_tree`, `jsonLd` (null here).
- **URLs:** job/apply page = `url` = `https://ats.rippling.com/{slug}/jobs/{id}`.
- **Python:** `requests.get("https://ats.rippling.com/api/v2/board/rippling/jobs", params={"page":0,"pageSize":500}, headers={"User-Agent":UA}).json()["items"]`

## 6j. Gem — VERIFIED 2026-10-02 on Gem's own board (`jobs.gem.com/gem`)

- **List (all posts, Greenhouse-like schema):** `GET https://api.gem.com/job_board/v0/{slug}/job_posts/` → JSON array (no pagination; trailing slash used).
  Fields: `id`, `title`, `absolute_url` (`https://jobs.gem.com/{slug}/{id}` = job + apply page), `content` (HTML) and `content_plain`,
  `location.name`, `location_type` (hybrid/remote/onsite), `offices[]`, `departments[]`, `employment_type`, `requisition_id`, `internal_job_id`,
  **`first_published_at`** (ISO, = posted date), `created_at`, `updated_at`.
- **Detail:** `GET https://api.gem.com/job_board/v0/{slug}/job_posts/{id}` (same fields; not needed since list has content).
- **Total:** `len(list)`. Slug = path segment of `jobs.gem.com/{slug}`.
- **Python:** `requests.get("https://api.gem.com/job_board/v0/gem/job_posts/", headers={"User-Agent":UA}).json()`

## 6k. Dover — VERIFIED 2026-10-02 on Dover's own careers page (`app.dover.com/jobs/dover`)

- **Step 1 (slug → client id):** `GET https://app.dover.com/api/v1/careers-page-slug/{slug}` → `{"id":"733c3162-...","slug":"dover","name":"Dover",...}`.
- **Step 2 (list):** `GET https://app.dover.com/api/v1/careers-page/{client_id}/jobs` → DRF-style `{"count":5,"next":null,"previous":null,"results":[...]}`
  (follow `next` if non-null). Results: `id` (uuid), `title`, `locations[]` (`location_type` REMOTE/..., `location_option{display_name,city,state,country}`),
  `workplace_type`, `is_published`, `is_sample`. **No dates/description in list.**
- **Detail:** `GET https://app.dover.com/api/v1/inbound/application-portal-job/{job_id}` → `user_provided_description` (HTML), **`created`**
  (ISO, posting creation), `compensation{lower_bound,upper_bound,currency_code,...}`, `locations`, `workplace_type`, `visa_support`, `active`, `client_domain`.
- **URLs:** apply page `https://app.dover.com/apply/{slug}/{job_id}` (SPA, 200).
- **Python:** `cid=requests.get("https://app.dover.com/api/v1/careers-page-slug/dover", headers={"User-Agent":UA}).json()["id"]; jobs=requests.get(f"https://app.dover.com/api/v1/careers-page/{cid}/jobs", headers={"User-Agent":UA}).json()["results"]`

## 6l. Teamtailor — VERIFIED 2026-10-02 on `career.teamtailor.com` (16 jobs) and `career.kry.se` (49 jobs)

- **JSON Feed (best):** `GET https://{careersite}/jobs.json` (content-type `application/feed+json`, JSON Feed 1.1) → `items[]` with `id` (uuid), `title`,
  `url` (`https://{careersite}/jobs/{numericId}-{slug}`), **`date_published`** (ISO with offset), `content_html` (full description), and `_jobposting`
  (embedded schema.org JobPosting: description, employmentType, jobLocation, datePosted, ...). Feed appears to contain **all** published jobs (Kry: 49 in feed vs. 20/page in HTML); no `next_url` seen.
- **RSS alternative:** `GET https://{careersite}/jobs.rss` → `item`: `title`, `description` (HTML), `pubDate`, `link`, `guid`, plus `tt:` extensions
  `remoteStatus`, `locations`, `department`, `role`, `division`.
- `{careersite}` is either `{co}.teamtailor.com` or the company's custom domain (detect via `jobs.json` returning feed JSON). Official API needs a token — not needed.
- **Python:** `requests.get("https://career.teamtailor.com/jobs.json", headers={"User-Agent":UA}).json()["items"]`

## 6m. Breezy HR — VERIFIED 2026-10-02 on `attentive.breezy.hr` (and `breezy.breezy.hr`)

- **List:** `GET https://{co}.breezy.hr/json` → JSON array of positions (all, no pagination); unknown tenant → HTML page.
  **`?verbose=true` adds `description` (HTML)** to every item. Fields: `id`, `friendly_id`, `name`, `url` (`https://{co}.breezy.hr/p/{friendly_id}` = job + apply),
  **`published_date`** (ISO), `type{id,name}` (fullTime...), `location{country{name,id},city,name}`, `locations[]`, `department`, `salary`, `company{name,friendly_id}`.
- **Dates:** `published_date` (list) vs JSON-LD `datePosted` on the position page — they can differ (2019-09-23 vs 2019-05-30 seen); `published_date` looks like latest publish.
- **Python:** `requests.get("https://attentive.breezy.hr/json", params={"verbose":"true"}, headers={"User-Agent":UA}).json()`

## 6n. JazzHR — PARTIAL (structure only; no active tenant with openings found in ~30 probes)

- Public boards live at `https://{co}.applytojob.com/apply` (HTML). Unknown tenants redirect to `https://www.jazzhr.com/job-seekers`;
  disabled ones show title "JazzHR - Inactive Career Page"; live-but-empty example: `roadtrippers.applytojob.com` ("Roadpass Digital - Career Page").
- Expected (from JazzHR's standard board, NOT verified today): job links `https://{co}.applytojob.com/apply/{jobCode}/{slug}`; job pages carry JSON-LD JobPosting
  (`datePosted`, `description`). The JSON API (`api.resumatorapi.com/v1/jobs?apikey=...`) requires the customer's API key → not usable.
- Adapter approach: scrape `/apply` for `/apply/{code}/` links, then parse JSON-LD per job; treat as low priority.

## 6o. Radancy TalentBrew career sites (generic) — VERIFIED 2026-10-02 on Disney (`www.disneycareers.com`) and Intuit (`jobs.intuit.com`)

- **Detect:** HTML references `tbcdn.talentbrew.com`; job URLs look like `/{lang}/job/{city}/{slug}/{companySiteId}/{jobId}` (Disney `.../391/{jobId}`, Intuit `/job/{city}/{slug}/27595/{jobId}`).
  TalentBrew is only a front-end — the "Apply" link goes to the real ATS (Disney → Workday `disney.wd5.myworkdayjobs.com/.../disneycareer/...`,
  Intuit → Avature `intuit.avature.net/externalCareers/JobApplication?pipelineId=...`).
- **Search (JSON wrapper around HTML):**
  `GET https://{site}/{lang}/search-jobs/results?ActiveFacetID=0&CurrentPage=1&RecordsPerPage=100&Distance=50&RadiusUnitType=0&Keywords=&Location=&ShowRadius=False&IsPagination=False&CustomFacetName=&FacetTerm=&FacetType=0&SearchResultsModuleName=Search+Results&SearchFiltersModuleName=Search+Filters&SortCriteria=0&SortDirection=0&SearchType=5&PostalCode=&fc=&fl=&fcf=&afc=&afl=&afcf=`
  (Intuit has no `/{lang}` prefix: `https://jobs.intuit.com/search-jobs/results?...`). Header `X-Requested-With: XMLHttpRequest` recommended.
  → JSON `{"filters": "<html>", "results": "<html>", "hasJobs": true, "hasContent": ...}`.
  - `RecordsPerPage=100` honored (Disney); `CurrentPage` 1-based. Totals inside `results` HTML: `data-total-job-results="742"`, `data-total-pages="8"`,
    `data-current-page`. (Intuit: 578 jobs.)
  - Rows: `<a href="/en/job/{city}/{slug}/391/{jobId}" data-job-id="{jobId}">` + `<h2>Title</h2>`, `span.job-location`, `span.job-brand`, `span.job-date-posted`
    (if the tenant shows dates).
- **Detail:** job page HTML has JSON-LD **JobPosting**: `datePosted` (**not zero-padded**, e.g. `2026-9-30` / `2026-10-2` → parse with `%Y-%m-%d` after splitting ints),
  `description` (HTML), `identifier` (ATS req id, e.g. Workday `10155352` / Avature `24263`), `jobLocation`, `employmentType`, `hiringOrganization`, `baseSalary`.
  Apply URL in `data-apply-url="..."` or the Apply anchor.
- **Python:** `r=requests.get("https://www.disneycareers.com/en/search-jobs/results", params={"ActiveFacetID":0,"CurrentPage":1,"RecordsPerPage":100,"SearchResultsModuleName":"Search Results","SearchFiltersModuleName":"Search Filters","SearchType":5,"SortCriteria":0,"SortDirection":0}, headers={"User-Agent":UA,"X-Requested-With":"XMLHttpRequest"}).json()["results"]; ids=re.findall(r'data-job-id="(\d+)"', r)`

## 6p. Kenexa / IBM BrassRing ("TG New UI") — VERIFIED 2026-10-02 on General Atomics (partnerid 25539)

- **Step 1:** `GET https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid={pid}&siteid={sid}` (~1.1 MB) → keep cookies
  (`tg_session_*`, `tg_rft`, `tg_rft_mvc`, `TS01...`) and read `<input name="__RequestVerificationToken" type="hidden" value="...">`.
  The page also embeds `<input id="searchResults" type="hidden" value="{...html-escaped JSON...}">` with `TotalCount` (GA US site: 791),
  `KeywordCustomSolrFields` ("Department,FORMTEXT1,FORMTEXT8,FORMTEXT34"), `LocationCustomSolrFields` ("FORMTEXT4,FORMTEXT5"), and 10 `HotJobs` (most recent).
- **Step 2 (page 1):** `POST https://sjobs.brassring.com/TgNewUI/Search/Ajax/MatchedJobs`, headers `RFT: <token>`, `Content-Type: application/json`,
  `X-Requested-With: XMLHttpRequest`, `Referer: <home url>`; body
  `{"partnerId":"25539","siteId":"5313","keyword":"","location":"","keywordCustomSolrFields":"Department,FORMTEXT1,FORMTEXT8,FORMTEXT34","locationCustomSolrFields":"FORMTEXT4,FORMTEXT5","linkId":"","Latitude":0,"Longitude":0,"facetfilterfields":{"Facet":[]},"powersearchoptions":{"PowerSearchOption":[]},"SortType":"LastUpdated","encryptedSessionValue":""}`
  → `Jobs.Job[]` (**50 per page**), **`JobsCount`** = total (791).
- **Step 3 (pages 2..N):** `POST https://sjobs.brassring.com/TgNewUI/Search/Ajax/ProcessSortAndShowMoreJobs` with the same body + `"pageNumber": 2` (verified).
- **Job fields:** each job has `Questions[]` of `{QuestionName, Value}`: `reqid` (internal id), `autoreq` (public req "57622BR"), `jobtitle`, `formtext8`
  (display title at GA), `department` (company/division, e.g. "General Atomics Aeronautical Systems" = GA-ASI; also "General Atomics", "GA Systems Integration"),
  `formtext5` city, `formtext4` state, **`lastupdated`** (`02-Oct-2026`, `%d-%b-%Y`; the only date — last update/repost), `jobdescription` (summary HTML),
  plus `Link` = `https://sjobs.brassring.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25539&siteid=5313&PageType=JobDetails&jobid={reqid}` (job + apply).
  formtext numbering is **tenant-specific** — map via `JobFieldsToDisplay` in the embedded JSON.
- **Detail:** `POST https://sjobs.brassring.com/TgNewUI/Search/Ajax/JobDetails` body `{"partnerId":"25539","siteId":"5313","jobid":"{reqid}","configMode":"","jobSiteId":"5313"}`
  → `ServiceResponse.Jobdetails.JobDetailQuestions[]` (`VerityZone`, `QuestionName`, `AnswerValue`): Job Summary (`jobdescription`), Job Qualifications (`formtext16`),
  Job Category, Experience Level, Workstyle (Onsite), Full/Part-time, **Pay Range Low/High**, Travel, Relocation, US Citizenship Required, Clearance Required/Level.
- **Blocking:** none (~10 calls).

## 7. Southern California employers — platform + endpoint (verified 2026-10-02)

| Employer | Platform | Endpoint / identifiers | Live count | Notes |
|---|---|---|---|---|
| **Snap** | **Workday** behind custom `careers.snap.com` | tenant `snapchat`, site `snap`, `wd1`: `POST https://snapchat.wd1.myworkdayjobs.com/wday/cxs/snapchat/snap/jobs` (also works on `https://wd1.myworkdaysite.com/wday/cxs/snapchat/snap/jobs`) | 188 | careers.snap.com HTML also embeds all 188 jobs as Elasticsearch `_source` objects (`absolute_url`, `title`, `departments`, `offices`, `location`, `role`, `employment_type`). Use existing Workday adapter. |
| **Disney** | **Workday** + Radancy TalentBrew front-end (`disneycareers.com`) | Workday: `disney.wd5.myworkdayjobs.com`, tenant `disney`, site **`disneycareer`** (`POST .../wday/cxs/disney/disneycareer/jobs`) | Workday 608; TalentBrew 742 | TalentBrew counts per location (and includes brands like Disneyland Paris); see §6o for the TalentBrew JSON. |
| **Lockheed Martin** | **Eightfold PCSX** (moved off lockheedmartinjobs.com, which now redirects) | `GET https://lockheedmartin.eightfold.ai/api/pcsx/search?domain=lockheedmartin.com&query=&location=&start=0&sort_by=timestamp`; details `.../api/pcsx/position_details?position_id={id}&domain=lockheedmartin.com&hl=en` | 5,560 (CA: 760) | v2 API → 403 "Not authorized for PCSX". Extra fields: `efcustomTextFinalclearancefortherole`, `...Levelofexperience`, `...Custshift`, `...Typeofjob`. Job URL `https://lockheedmartin.eightfold.ai/careers/job/{id}`. Rate-limit as §6a. |
| **General Atomics / GA-ASI** | **Kenexa BrassRing** | partnerid **25539**; siteid **5313** = US jobs (791), 5757 = international (18), 5310 = other/early-careers (12). See §6p. GA-ASI = `department` "General Atomics Aeronautical Systems". | 791 | `www.ga-asi.com/careers` returns 403 to curl (WAF); `www.ga.com/careers` links to BrassRing. |
| **Qualcomm** | **Eightfold PCSX** | `GET https://careers.qualcomm.com/api/pcsx/search?domain=qualcomm.com&...` | 2,044 (San Diego 684) | See §6a. `postedTs` refreshed daily → use `creationTs`. |
| **Intuit** | Radancy TalentBrew front-end; ATS = **Avature** | `GET https://jobs.intuit.com/search-jobs/results?...&RecordsPerPage=100` (§6o); apply `https://intuit.avature.net/externalCareers/JobApplication?pipelineId={id}` | 578 | Avature feed `intuit.avature.net/externalCareers/SearchJobs/feed/` returns empty → use TalentBrew. JSON-LD `identifier` = Avature pipelineId. |
| **Tesla** | Custom (`tesla.com/careers`), ATS = **Avature** | List: `GET https://www.tesla.com/cua-api/apps/careers/state` (1.6 MB JSON: `lookup{regions,sites,locations,departments,types}`, `departments`, `geo`, `listings[]` = 8,411 items `{id, t:title, dp:dept id, f, l:location id, y:type, sp, pu}`). Detail: `GET https://www.tesla.com/cua-api/careers/job/{id}` → `title`, `department`, `jobFamily`, `location`, `state`, `country`, `jobDescription`, `jobResponsibilities`, `jobRequirements`, `jobCompensationAndBenefits` (HTML), `timeType`, `postUntilDate`, `url` (`/careers/search/job/{slug}-{id}`), `applyUrl` (`https://tesla.avature.net/Careers/ApplicationMethods?jobId={id}`). | 8,411 | **BLOCKED for curl/requests: Akamai returns 403 "Access Denied"** (even the HTML page). Works only inside a real browser session (verified via in-browser `fetch`); repeat calls get **429 `{"cpr_chlge":...}`** (Akamai crypto challenge) until the page JS solves it. **No posting date anywhere** (use first-seen). Needs Playwright/real browser + low frequency. |
| **Blizzard Entertainment** | **Phenom** | `POST https://careers.blizzard.com/widgets` with `lang=en_global`, `country=global`, `pageId=page14` (refNum `BLENGLOBAL`) | 39 | Mostly Irvine, CA. See §6b. |
| **Activision** | **Phenom** | `POST https://careers.activision.com/widgets` with `lang=en_us`, `country=us`, `pageId=page3` (refNum `ACPUUS`), page path `/search-results` | 92 | See §6b. |
| **Riot Games** | **Greenhouse** | `GET https://boards-api.greenhouse.io/v1/boards/riotgames/jobs` (`?content=true` for descriptions) | 165 | Existing Greenhouse adapter. |
| **Northrop Grumman** | **Workday** (ATS) + **Eightfold PCSX** front-end | Workday: `ngc.wd1.myworkdayjobs.com`, tenant `ngc`, site **`Northrop_Grumman_External_Site`**. Eightfold: `GET https://jobs.northropgrumman.com/api/pcsx/search?domain=ngc.com&query=&location=&start=0&sort_by=timestamp` (`displayJobId` = Workday req id, e.g. `R10247512`) | Workday 3,749; Eightfold 3,755 | Both verified. northropgrumman.com/careers "For External Candidates" → `jobs.northropgrumman.com/careers` (Eightfold); `ngc.eightfold.ai/careerhub` is the internal (employee) hub. Prefer Workday CXS (no aggressive rate limit). |
| **Boeing** | **Workday** | `boeing.wd1.myworkdayjobs.com`, tenant `boeing`, site **`EXTERNAL_CAREERS`** | 750 | Confirmed via CXS. |
| **RTX** (Raytheon, Collins, P&W) | **Workday** | `globalhr.wd5.myworkdayjobs.com`, tenant `globalhr`, site **`REC_RTX_Ext_Gateway`** | 4,897 | Confirmed via CXS. `careers.rtx.com` (Phenom front-end) returns 403 to curl. |

Workday CXS body used for the confirmations: `{"appliedFacets":{},"limit":1,"offset":0,"searchText":""}` with `Content-Type: application/json`.

## 8. Cheat sheet — which field to use as "posted date"

| Platform | Best "first posted" field | Other date fields | Granularity / caveat |
|---|---|---|---|
| Amazon | `posted_date` ("October  2, 2026") | `updated_time` (relative) | day; not monotonic with `sort=recent` |
| Microsoft / Eightfold PCSX | `creationTs` (unix s) | `postedTs` (latest (re)post; sort key) | Qualcomm refreshes `postedTs` daily |
| Eightfold v2 (Netflix) | `t_create` (unix s) | `t_update` | day |
| Apple | `postDateInGMT` (ISO) | `postingDate`, detail `postingDateMeta` | evergreen PIPE roles re-stamped to "now" |
| Google | `[12]` (unix s) | `[13]`/`[14]` updated (sort key) | second |
| Meta | JSON-LD `datePosted` (per job page) | — | second; needs 1 page fetch per job |
| Phenom | `postedDate` | `dateCreated`, `jobUpdatedDate`, `postedDateTrack[]` | day |
| Oracle ORC | `PostedDate` (list) / `ExternalPostedStartDate` (detail) | `ExternalPostedEndDate` | day / second |
| iCIMS | list `<span title="10/2/2026 11:27 AM">` or JSON-LD `datePosted` | JSON-LD `validThrough` (= +1y default) | minute (tenant TZ) |
| SuccessFactors CSB | microdata `datePosted` / list `span.jobDate` | sitemap `lastmod`, RSS `pubDate` | second |
| Jobvite | — (none public) | — | use first-seen |
| BambooHR | detail `datePosted` | — | day |
| Pinpoint | JSON-LD `datePosted` (posting page) | `deadline_at` | second |
| Rippling | detail `createdOn` | — | ms |
| Gem | `first_published_at` | `created_at`, `updated_at` | ms |
| Dover | detail `created` | — | µs |
| Teamtailor | `date_published` (JSON feed) / RSS `pubDate` | — | second |
| Breezy | `published_date` | JSON-LD `datePosted` (can be earlier) | ms |
| TalentBrew | JSON-LD `datePosted` ("2026-9-30", unpadded) | list `span.job-date-posted` | day |
| BrassRing | `lastupdated` ("02-Oct-2026") | — | day; it is last-updated, not first-posted |
| Tesla | — (none) | `postUntilDate` (usually null) | use first-seen |
