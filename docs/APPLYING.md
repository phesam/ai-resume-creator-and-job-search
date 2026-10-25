# Applying: order, timing, referrals and forms

You apply yourself. The agent never submits an application, sends a message, or accepts terms for you.

## The order

1. **Referral roles first.** About 40% of referred candidates reach an interview against about 3% of cold
   applicants (Ashby). One referral is worth more than a dozen cold applications.
2. **Fresh postings that fit**, within a week of posting. Most applicants arrive in week one and recruiters review as
   applications come in.
3. **The rest of your apply list**, top to bottom. It is ordered by fit and what you want, not by age, so if you only
   send ten today, the ten you most want sent are the ones at the top.

`python3 -m jobhunt list` rebuilds `workspace/APPLY_LIST.md` and `workspace/apply_list.html` (open it in a browser;
tick roles as you send them, then press "Copy log commands for checked roles" and paste the commands to your agent).

## Referrals

- **A referral is someone who will actually submit you.** A LinkedIn connection who works there is not a referral;
  the case study built a "someone you know works there" table and it was useless.
- **Ask for one role, maybe two.** Nobody asks one friend for a dozen referrals; the apply list shows at most three
  per company, best first. Use the referral on the role you fit best, not on a stretch you'd never get cold.
- **Don't build plans that depend on the referrer knowing things.** A new-grad friend can submit a referral, but
  can't tell you whether a req is still hiring or whether the team would flex on years.
- **Check the form before you spend it.** If the required questions rule you out (years with a specific language,
  an active clearance), pick another role.
- **After a rejection with interviews,** companies usually expect about six months before a new application. Ask the
  referrer to check.
- **Give the referrer what they need:** the posting link, the job ID, your resume, and two sentences on why you fit.

A short message you can adapt (you send it; nothing is ever sent for you):

> Hi <name>, I'm applying to <role> (job <ID>, <link>). It lines up with <one specific thing from the posting> and my
> <most relevant work, e.g. the scheduling service I built at Brightline>. Would you be up for referring me? My resume
> is attached. Totally fine if not. Thanks!

## Application forms

- **The form is where most automatic rejections happen**, not the resume parser: work authorization, location,
  clearance, and "Do you have N+ years of X?" yes/no questions. `python3 -m jobhunt fresh show "<Company>" <id>`
  prints a Greenhouse or Ashby posting's required questions.
- **Answer truthfully.** If you'd have to stretch an answer, the role isn't one to apply to.
- **Years questions:** count what the question counts. "Professional experience" usually means full-time; internships
  may or may not count; when the question is ambiguous, answer the honest reading.
- **Essay questions** ("Describe your most impressive accomplishment", "Three bullets of exceptional ability"): ask
  the agent which inventory items to talk about, then write the answer yourself in your own voice. Short and specific
  beats long.
- **"Have you applied before?"** Your `applications.csv` knows.
- **Greenhouse "Dream Job":** one application a month can be marked as your top choice. Use it on your best match.

## How many

Spread applications across companies instead of sending a dozen to one (`per_company_max`, default 8, minus what you
sent there in the last 90 days). Recruiters see all your applications on one profile, and in Huntr's data each extra
application to the same company converted worse. A brand-new posting that fits clearly better than what you already
sent is still worth sending.

## After you apply

- Log it: `python3 -m jobhunt applied add --company "<Company>" --title "<Title>" --url <link> --resume general`.
- Every week or two, have the agent rebuild your history from email (read-only): confirmations, rejections and
  interview invites. That keeps the duplicate check honest.
- `python3 -m jobhunt applied stats` shows your own funnel: applications, interviews, by resume variant and source.
- When you hear back, update the status (`--status interview`), and start interview prep from the inventory: the
  same facts that wrote your resume are your answers.
