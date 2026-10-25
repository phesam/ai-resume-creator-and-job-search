# Company registry notes

These notes go with `company_registry_seed.yaml`. All checks ran on 2026-10-02.

## Totals
- **270 companies.** 254 were checked with a live call to their public job API (`verified: true`). 16 are listed but not verified.
- **197 companies have SoCal locations.** A city is listed when it had at least 2 open postings at check time, or when it is a known SoCal office.
- Each entry's `notes` field gives the posting count for each SoCal city. Big-employer counts are approximate (see the caveats at the end).

| ATS | Entries | Verified |
|---|---|---|
| greenhouse | 104 | 104 |
| workday | 52 | 51 |
| ashby | 39 | 39 |
| lever | 18 | 18 |
| custom (Google, Apple, Amazon/Ring/Twitch, TikTok, Atlassian, Meta, Tesla) | 9 | 7 |
| eightfold (Northrop, Lockheed, Microsoft, Qualcomm, PayPal, Netflix) | 6 | 6 |
| smartrecruiters (NBCU, Mattel, ServiceNow, Western Digital, Experian) | 5 | 5 |
| icims via Jibe (Rivian, AMD, Viasat, Panasonic) | 4 | 4 |
| successfactors (Paramount, Skyworks, L3Harris) | 3 | 3 |
| oracle_hcm (Oracle, Uber, Molina) | 3 | 3 |
| avature (EA, Intuit) | 2 | 2 |
| one each: pinpoint, brassring, phenom, paylocity, taleo, gr8people, jobvite, rippling, workable, gem, teamtailor, adp | 12 | 12 |
| paycom, csod, kula, ukg (platform known, not verified) | 4 | 0 |
| unknown | 9 | 0 |

## Companies I could not verify (in the YAML with `verified: false`)
- **Firestorm Labs** (San Diego): firestormlabs.com now redirects to an unrelated site. No Greenhouse, Lever or Ashby board was found under the obvious names.
- **The Aerospace Corporation, SAIC, Edmunds, Masimo, Yardi:** their careers sites return HTTP 403 to scripts, and I couldn't identify the ATS. Masimo and Yardi each have a SmartRecruiters page, but only 1 job was posted, so it is probably not their real board.
- **Kratos, Seismic, Superhuman (formerly Grammarly):** jobs load client-side from a source I couldn't identify. Grammarly's old Greenhouse board (`grammarly`) now returns 404.
- **TrueCar:** Workday tenant `truecar` exists on wd1, but I couldn't find the site name.
- **Meta:** a GraphQL app that rejects scripted requests. **Tesla:** blocked by Akamai bot protection.
- **Platform found but not verified:**
  - FabFitFun (Paycom)
  - Invoca (Kula; the page uses a bearer token embedded in its JS, which I chose not to use)
  - Karma Automotive (UKG Ready)
  - Cornerstone OnDemand (its own CSOD site)

## Requested but left out of the YAML
- **Canoo:** filed for bankruptcy in January 2025. **Cruise:** wound down into GM in 2025.
- **Loop Media, Beyond Limits:** no openings or ATS found on their careers pages. **Clutch:** too ambiguous to identify.
- **Not SoCal and not step-up companies:** Archer Aviation, Joby (iCIMS), Sierra Space (Workday, Colorado), Stoke, Firefly, Reliable Robotics, Gecko Robotics (Ashby `gecko-robotics`), Overland AI (Rippling), Second Front (Ashby `Second-Front-Systems`), Govini (careers page now redirects to air.ai).
- **Other:**
  - Shopify and Aurora: custom sites, not resolved.
  - Flock Safety: Ashby `flock` is a different company (Flock Cover).
  - Deel: its Ashby board is empty.
  - Mistral: its Lever board is empty.
  - Edison International: SuccessFactors `C0003043182P`, not verified.

## Platform patterns noticed
- **The careers page is often a front end over the real ATS.** Follow the "Apply" link to find it:
  - Phenom over Workday: RTX, WBD, Adobe, Cisco, Thermo Fisher, LPL, First American, JPL, Blizzard, Activision.
  - Radancy (TalentBrew) over other systems: Disney (Workday), Intuit (Avature), Kaiser (Taleo), L3Harris (SuccessFactors on SAP's NS2 cloud), Molina (Oracle).
  - Jibe over iCIMS: Rivian, AMD, Viasat, Panasonic.
  - Phenom over BrassRing: BAE.
  - Phenom (`POST /widgets`), Radancy (`data-total-results`) and Jibe (`/api/jobs`) all return counts directly, which helps when the underlying ATS can't be reached.
- **Workday:**
  - Data centers now include wd12, wd108, wd115 and wd503, not just wd1, wd3 and wd5.
  - The tenant name in the API path can differ from the subdomain. Magnite's host is `osv-rubicon` but its tenant is `osv_rubicon`.
  - `total` is capped at 2000 (NVIDIA, Leidos, Booz Allen); summing a facet gives the real count.
  - For discovery: a POST to `/wday/cxs/{tenant}/bogus/jobs` returns 404 on the tenant's real data center and 422 everywhere else.
- **Microsoft Gaming consolidation:** Activision and Blizzard now post on the `xboxgaming` Workday tenant (sites `External`, `Blizzard_External_Careers`, `King_External_Careers`). The old `activision` tenant is dead.
- **Eightfold moved tenants to a new "PCSX" API.** The old `/api/apply/v2/jobs` now returns 403 "Not authorized for PCSX" for Northrop, Lockheed, PayPal, Qualcomm and Microsoft, so use `/api/pcsx/search`. Netflix still works on v2. Lockheed moved here from lockheedmartinjobs.com. These APIs rate-limit with HTTP 429, so space out requests.
- **Oracle Recruiting Cloud is spreading:** Uber moved off its custom API (`iaziqy.fa.ocs.oraclecloud.com`, site CX_1).
- **Slug gotchas:**
  - Lever slugs are case-sensitive: `MachinaLabs` works, `machinalabs` 404s.
  - Ashby slugs can be legal names with spaces or dots: `Grindr%20LLC`, `rivianvw.tech`, `apex-technology-inc`, `applied` (Applied Intuition).
  - Greenhouse tokens often carry a suffix: `castelioncorporation`, `k2spacecorporation`, `trueanomalyinc`, `doordashusa`, `wizinc`, `gleanwork`, `tubitv`, `vardaspace`, `nerostechnologies`.
- **Name collisions:** always check the board's company name.
  - Greenhouse: `figure` is Figure Lending, `archer` is a vet clinic, `apex` is Apex Eye, `fox` is a vet hospital, `asi` is ASI Hastings.
  - Ashby: `radiant` is a UK company (use `radiant-industries`), `runway` is cfo.ai (use `runway-ml`), `impulse` is Impulse Labs.
- **Empty legacy boards** sit next to live ones. Ashby boards with 0 jobs exist for ServiceTitan, Figma, Coinbase, Vercel, Reddit, Airtable, Wiz, Mercury, Bumble, Vast and Machina Labs; use the board that has jobs.
- **Ashby's posting API can be turned off while the hosted page still works.** Whatnot's API returns 404, but `jobs.ashbyhq.com/api/non-user-graphql` (`ApiJobBoardWithTeams`) does work.
- **Rebrands and mergers to map aliases for:**
  - CoreLogic is now Cotality (Workday wd115).
  - ABL Space Systems is now Long Wall.
  - Grammarly is now Superhuman.
  - Paramount is now Paramount Skydance.
  - L3Harris now includes Aerojet Rocketdyne (Canoga Park).
  - Tinder and Hinge post on Match Group's Lever board.
  - xAI's Greenhouse board is now named "SpaceXAI".
  - Ring and Twitch post on amazon.jobs.

## Caveats
- Open-job counts are totals across all locations and roles at check time, not just SWE roles.
- amazon.jobs caps `hits` at 10000.
- Google's LA and Irvine searches cover overlapping areas.
- Apple's count is US-only.
- Panasonic's count covers all of Panasonic North America.
- Teradata's count is the sum of its location facets.
- SoCal breakdowns come from the full board where the API returns one: Greenhouse, Lever, Ashby, SmartRecruiters, Workday facets, Jibe. For Eightfold, Oracle, Phenom, TikTok and Netflix they come from a sample.
- BrassRing (GA), Radancy-based counts (Kaiser, Intuit, L3Harris), EA, Apple and Atlassian give no location breakdown. Their SoCal offices come from company info.
