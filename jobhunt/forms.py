"""Required application-form questions for a posting, where the hiring system publishes them.

These questions are often the real screen. A form that asks "Do you have 3+ years of professional experience with
a JVM language? Yes / No" filters out anyone who answers No, however good the resume is; a resume never gets read.
Check them before you apply, and before you spend a referral on a role. Answer them truthfully.

Greenhouse and Ashby publish their forms; most other systems only show them inside the application.
"""

from __future__ import annotations

from .common import get_json, post_json

# Standard fields every form has; they say nothing about eligibility.
_STANDARD = {"first name", "last name", "preferred first name", "email", "phone", "phone number", "resume/cv", "cover letter",
             "resume", "linkedin", "linkedin profile", "linkedin url", "website", "location (city)", "country", "name",
             "location", "pronouns", "how did you hear about this job?", "how did you hear about us?"}

_ASHBY_QUERY = """query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) {
  jobPosting(organizationHostedJobsPageName: $organizationHostedJobsPageName, jobPostingId: $jobPostingId) {
    id title applicationForm { sections { title fieldEntries { ... on FormFieldEntry { isRequired field } } } }
  }
}"""


def _options(values) -> str:
    labels = [v.get("label") or v.get("value") for v in values or [] if isinstance(v, dict)]
    labels = [str(x) for x in labels if x]
    return f" [{' / '.join(labels[:8])}{' / …' if len(labels) > 8 else ''}]" if labels else ""


def form_questions(job: dict, cfg: dict) -> list[str] | None:
    """Required, non-standard questions as text, [] when there are none, None when this system doesn't say."""
    try:
        if job.get("ats") == "greenhouse" and cfg.get("token"):
            d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{cfg['token']}/jobs/{job['id']}?questions=true")
            out = []
            for q in d.get("questions") or []:
                label = (q.get("label") or "").strip()
                if not q.get("required") or label.lower().rstrip("*") in _STANDARD:
                    continue
                vals = [v for f in q.get("fields") or [] for v in (f.get("values") or [])]
                out.append(label + _options(vals))
            return out
        if job.get("ats") == "ashby" and cfg.get("token"):
            d = post_json("https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting",
                          {"operationName": "ApiJobPosting", "query": _ASHBY_QUERY,
                           "variables": {"organizationHostedJobsPageName": cfg["token"], "jobPostingId": job["id"]}})
            form = ((d.get("data") or {}).get("jobPosting") or {}).get("applicationForm") or {}
            out = []
            for sec in form.get("sections") or []:
                for e in sec.get("fieldEntries") or []:
                    f = e.get("field") or {}
                    label = (f.get("title") or "").strip()
                    if not e.get("isRequired") or label.lower() in _STANDARD:
                        continue
                    out.append(label + _options(f.get("selectableValues")))
            return out
    except Exception as e:  # noqa: BLE001
        return [f"(could not read the form: {str(e)[:120]})"]
    return None
