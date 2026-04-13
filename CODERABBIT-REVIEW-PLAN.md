# CodeRabbit Full Codebase Review Plan

**Purpose:** Get the entire codebase reviewed by CodeRabbit after Phase 6 is complete.
CodeRabbit tier limit: 150 files/PR. Target: ≤120 files per PR with headroom.

**When to run:** After Phase 6 is merged to master and all tests pass.

---

## Phase commit file counts (reference)

| Commit | Description | Files changed |
|--------|-------------|---------------|
| 722d071 | Phase 1 — Foundation | 93 |
| 0ba314c | Phase 2 — Events & Calendar | 21 |
| 675881c | Phase 3 — Org Onboarding & Service Taxonomy | 25 |
| ffcf711 | Phase 4 — Referrals & No-Loss Delivery | 21 |
| 5a3d995 | Security hardening | 17 |
| 2ff55cd | Docs (ROADMAP, STATE, REQUIREMENTS, CLAUDE.md) | ~5 |
| 275d509 | Phase 5 — Pathways + Design System | 48 |
| Phase 6 | AI Assistant (TBD) | ~60–80 est. |

All individual phase commits are well under 120 files. Each gets its own PR.

---

## Step-by-step plan

### 1. Create the review base branch

```bash
# Create a clean base branch at the initial commit
git checkout 7194eb1
git checkout -b review/base
git push -u origin review/base
```

### 2. Create PR for each phase

For each phase, create a branch at that commit and open a PR against the previous phase:

```bash
# PR 1 — Phase 1 Foundation (93 files)
git checkout 722d071
git checkout -b review/phase-1-foundation
git push -u origin review/phase-1-foundation
gh pr create \
  --base review/base \
  --head review/phase-1-foundation \
  --title "Review: Phase 1 — Foundation (auth, orgs, i18n, seed data)" \
  --body "CodeRabbit review of Phase 1. 93 files. Django project setup, custom User model, Organization models, public views, i18n, seed data."

# PR 2 — Phase 2 Events & Calendar (21 files)
git checkout 0ba314c
git checkout -b review/phase-2-events
git push -u origin review/phase-2-events
gh pr create \
  --base review/phase-1-foundation \
  --head review/phase-2-events \
  --title "Review: Phase 2 — Events & Calendar (RFC 5545 recurrence, iCal, HTMX)" \
  --body "CodeRabbit review of Phase 2. 21 files. Event/Occurrence models, Celery tasks, public calendar, org portal CRUD."

# PR 3 — Phase 3 Org Onboarding & Service Taxonomy (25 files)
git checkout 675881c
git checkout -b review/phase-3-onboarding
git push -u origin review/phase-3-onboarding
gh pr create \
  --base review/phase-2-events \
  --head review/phase-3-onboarding \
  --title "Review: Phase 3 — Org Onboarding & Service Taxonomy" \
  --body "CodeRabbit review of Phase 3. 25 files. OrgOnboardingState wizard, ServiceCategory model, portal dashboard, completeness score."

# PR 4 — Phase 4 Referrals + Security hardening (21 + 17 = 38 files)
git checkout 5a3d995
git checkout -b review/phase-4-referrals
git push -u origin review/phase-4-referrals
gh pr create \
  --base review/phase-3-onboarding \
  --head review/phase-4-referrals \
  --title "Review: Phase 4 — Referrals, Encrypted PII, Audit Chain + Security Hardening" \
  --body "CodeRabbit review of Phase 4. 38 files. Referral/ReferralFormField/ReferralDelivery models, Fernet encryption, AuditEntry hash chain, Celery delivery engine, security hardening."

# PR 5 — Phase 5 Pathways + Design System (48 files, includes docs)
git checkout 275d509
git checkout -b review/phase-5-pathways
git push -u origin review/phase-5-pathways
gh pr create \
  --base review/phase-4-referrals \
  --head review/phase-5-pathways \
  --title "Review: Phase 5 — Pathways + Design System Rectification" \
  --body "CodeRabbit review of Phase 5. 48 files. Pathway/PathwaySection/PathwayGuideItem models, prison leavers & homeless portal, design system overhaul (Figtree, Heroicons, WCAG AAA, amber CTAs)."

# PR 6 — Phase 6 AI Assistant (run after Phase 6 complete)
git checkout master  # or the Phase 6 commit hash
git checkout -b review/phase-6-ai-assistant
git push -u origin review/phase-6-ai-assistant
gh pr create \
  --base review/phase-5-pathways \
  --head review/phase-6-ai-assistant \
  --title "Review: Phase 6 — AI Assistant (RAG-Anything, pgvector, Gemini 2.5 Flash)" \
  --body "CodeRabbit review of Phase 6. AI chat assistant, RAG-Anything PDF processing, Obsidian vault sync, HTMX streaming, crisis detection."
```

### 3. Let CodeRabbit run on each PR

- Open each PR in GitHub
- Wait for CodeRabbit to post its review
- Address any HIGH or CRITICAL findings
- Close PRs once reviewed (do NOT merge — these are review-only branches)

### 4. Clean up review branches after

```bash
git push origin --delete review/base
git push origin --delete review/phase-1-foundation
git push origin --delete review/phase-2-events
git push origin --delete review/phase-3-onboarding
git push origin --delete review/phase-4-referrals
git push origin --delete review/phase-5-pathways
git push origin --delete review/phase-6-ai-assistant
```

---

## Notes

- These PRs are **review-only** — never merge them into master
- Each PR shows exactly the diff for that phase, not cumulative changes
- PRs are chained (each targets the previous phase branch as base) so CodeRabbit sees only the new files in each PR
- After CodeRabbit reviews, prioritise fixing any security or data-handling findings in apps/referrals/, apps/audit/, and apps/accounts/
