# Human–AI Research Alignment & Provenance

A usable, local-first CLI and reusable agent Skill for maintaining research intent and reviewing explicitly recorded AI involvement. Python 3.9+ and Git; no runtime packages, accounts or model API required.

This MVP separates **human approval** from **empirical validation**. Accepting a hypothesis never proves it. It supports a new project, adoption midway through existing work, and resuming a tracked project.

## Install and try

```sh
python3 -m pip install .
harp --help
# Or, directly from this checkout:
python3 -m harp --root /path/to/research init --mode new
python3 -m harp --root /path/to/research interview
python3 -m harp --root /path/to/research resume
```

`interview` asks about missing approved categories, saves exact answers as private unverified proposals, and asks for an explicit confirmation and reviewer. Empty answers defer a question. `questions` provides machine-readable prompts, including pending reviews and hypothesis falsification prompts. It is deterministic and state-adaptive, not a language model. The accompanying Skill supplies conversational extraction and context-dependent follow-ups when used in a capable agent. No provider credentials or calls are hidden in the CLI.

For agent installation, place this complete project folder in your agent's supported skills location, or point the agent to `SKILL.md`. The CLI remains usable independently. The repository must stay available for module execution; do not install just the Markdown file.

## Three entry points

```sh
harp --root /path/to/new-research init --mode new
harp --root /path/to/existing-research init --mode existing
harp --root /path/to/tracked-research resume
```

Initialization never overwrites a ledger. Mid-project adoption timestamps the tracking boundary and captures a Git baseline if available; it does not scan existing papers, replay history, or claim past AI activity was observed. Supply extracted information as proposals with source references. Resuming shows active accepted items, missing-field questions, and structural drift flags.

## Research state and review

Eight kinds: `goals`, `consensus`, `priors`, `hypotheses`, `evidence`, `findings`, `open_questions`, `decisions`. Each record has source, visibility, evidence links, validation state and optional superseded ID. Text and source are provided by the human or an agent, not inferred from Git.

```sh
harp propose goals 'Estimate the effect of adaptation on original-work demand' --source 'Researcher interview'
# Commands return IDs. Substitute the actual ID from the preceding output.
harp status
harp review GOAL_ID --verdict accept --reviewer 'Researcher' --reason 'Matches the intended estimand' --confirm
harp propose priors 'The effect may be positive' --source 'Researcher expectation'
harp propose hypotheses 'Adaptation increases weekly demand' --source 'Planning discussion'
harp propose evidence 'Synthetic table: demand increases by 2 units' --source 'examples/synthetic-results.csv'
harp review EVIDENCE_ID --verdict accept --reviewer 'Researcher' --reason 'Inspected synthetic table' --confirm
harp propose findings 'The toy estimate is positive' --source 'Toy calculation' --evidence EVIDENCE_ID --validation preliminary
harp propose goals 'Estimate heterogeneous effects by genre' --source 'Scope revision' --supersedes GOAL_ID
harp diff NEW_GOAL_ID
harp check
```

Human reviews use `accept` or `reject`; prior reviews remain in the event history. Accepted replacements supersede old items, while pending replacements leave the previous shared state active. Replacements must target an active accepted item of the same kind. Rejection can revoke an earlier acceptance. Reviewer identities and `verified` labels are local assertions, not authentication or scientific certification. Do not let agents autonomously approve their own proposals. Verified findings require at least one reviewed evidence link. A later rejected/superseded evidence item triggers an unsupported-finding warning.

## Git and session provenance

```sh
harp session --provider 'OpenAI' --model 'unknown' --summary 'Assisted with a synthetic analysis plan'
# Use --origin imported for user-supplied historical session metadata.
harp capture --session SESSION_ID --items GOAL_ID HYPOTHESIS_ID
harp status
harp review CAPTURE_ID --verdict accept --reviewer 'Researcher' --reason 'Inspected Git diff and session association' --confirm
harp check
```

Captures link an explicit session ID and research IDs to HEAD, a tracked working-tree diff hash and a Git status hash. This includes staged and unstaged tracked changes relative to HEAD. Untracked file contents are excluded; their status entries affect the status hash. In an unborn repository only the staged diff can be hashed. Git captures do not commit, install hooks, send telemetry, collect author emails/remote URLs, or retain patches. Review the actual diff with Git before accepting a capture. Git must run successfully; non-Git projects can use state/session tracking but not `capture`.

`check` flags pending proposals, pending/rejected capture reviews, proposed replacements, unsupported findings, and Git drift from the last capture (or initialization). A capture is a checkpoint even before review; its pending status remains flagged. `diff` compares an explicit research replacement with its predecessor. These are structural checks: no semantic contradiction detector, goal-distance score, causal inference validator, automatic code attribution or line-level provenance is claimed. Two identical texts are not proof of alignment. A changed untracked file may evade detection if its status entry is unchanged.

## Disclosure and privacy

```sh
harp export --output disclosure-private-text-withheld.md
# Only after deliberately marking selected proposals --visibility shareable:
harp export --include-shareable --output disclosure-selected-text.md
```

Exports refuse to overwrite existing files. Default output withholds all research text, sources, summaries, reviewer names and provider/model names. It retains record IDs, categories, validation/review status, times, Git hashes, session origin and counts. These are potentially linkable metadata: inspect every report before sharing. The opt-in export includes shareable proposal text and provider/model names; private proposal text stays withheld. A Markdown export is a disclosure aid, not a journal-specific compliance certificate. Generated reports should be stored inside the ignored directory until deliberately shared.

`.ai-research/ledger.json` stores the private local record and is added to `.gitignore` at initialization. The directory is created with mode 0700 and ledger writes use mode 0600, atomic replacement and fsync. Existing directory permissions, filesystem backups, disk encryption and already tracked files remain the operator's responsibility. Git ignore is not encryption or access control. **No automatic capture of ChatGPT, Claude, IDE or other third-party conversations is implemented.** Session entries are explicit, self-reported metadata. No prompt transcript or hidden reasoning is collected. No model-derived secrets filter is promised.

## Storage and limits

Schema v1 uses an ordered event ledger: proposal, review, session and capture events. Events include UTC timestamps and a SHA-256 previous-event chain. State is derived from events; no destructive edit command exists. The chain detects accidental event edits, not malicious rewriting, event-tail deletion, unsigned baseline changes or clock manipulation. There is no external anchor, authenticated reviewer, multi-user access control, database migration or concurrent-writer protection. Run one mutating CLI at a time. Keep separate secure backups; do not edit the JSON manually. Imported sources are labels, not fetched or cryptographically validated source documents.

Session metadata and capture links do not prove which changes AI produced. Unknown model versions should remain unknown. Only the explicitly entered records since initialization are covered; completeness cannot be inferred. The entire CLI runs offline and never uploads anything. Publication of this software does not publish the user's research ledger.

## Test and example

```sh
python3 -m unittest discover -s tests -v
python3 examples/demo.py
```

The demo creates a temporary Git project with synthetic data, exercises review/replacement/session/capture/export/resume, and prints the disclosure. It does not affect a real research project. Tests cover lifecycle, approval/validation separation, evidence revocation, privacy export, Git drift, adaptive prompts and accidental tampering. See `SKILL.md` for the agent workflow.
