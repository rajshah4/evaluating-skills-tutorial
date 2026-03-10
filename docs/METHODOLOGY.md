# Skill Evaluation Methodology

This page is about how to think about evaluating a skill.

It is not a description of this repo's internal structure. It is a lightweight methodology you can reuse for your own skills.

## What a skill evaluation is

A skill evaluation asks a simple question:

`Does this skill improve agent performance on a bounded task?`

That sounds obvious, but it rules out a lot of vague evaluation habits.

You are not trying to answer:

- is the skill interesting?
- is the skill well written?
- does the trace look impressive?
- did the agent say something reasonable?

You are trying to answer:

- did the skill change the outcome?
- did it change the procedure?
- did it improve reliability, speed, or both?

## The unit of measurement

The unit of measurement is one task run under one condition.

A condition is usually one of:

- `no-skill`
- `skill enabled`
- `skill A`
- `skill B`

If you cannot compare at least two conditions on the same task, you are not really measuring the value of the skill.

## What makes a task evaluable

Not every task is good for skill evaluation.

The best tasks have three properties:

- bounded scope
- deterministic verification
- a real procedural gap

### Bounded scope

The task should be small enough that:

- the agent can finish it in one run
- a human can understand what success looks like
- failures are diagnosable

### Deterministic verification

You need a verifier that can say pass or fail without subjective judgment.

Good examples:

- exact or normalized JSON match
- expected findings present
- expected numbers within tolerance
- expected file or worksheet exists

Bad examples:

- "the answer feels good"
- "the review seems useful"
- "the summary is well written"

### Real procedural gap

The task should reward having the right workflow, not just having general knowledge.

That is where skills matter most.

Examples:

- using the right offline security scan workflow
- extracting metrics in the correct order from multiple files
- following a reliable PR review checklist
- using the right transformation steps before writing an output artifact

## How skills should be measured

A skill should be measured against outcomes first, not prose quality.

The most useful primary metric is:

- pass/fail

Secondary metrics:

- runtime
- number of steps or turns
- number of tool calls or events

Those secondary metrics matter because two skills may both pass, but one may:

- finish faster
- use fewer steps
- take a cleaner path
- fail less often across reruns

## The baseline matters

Always run `no-skill`.

Without a baseline, you cannot tell whether:

- the task is already easy for the base model
- the skill actually improved anything
- the skill made things worse

This is the most common evaluation mistake: people run only the skill-enabled version and then assume success means the skill was valuable.

It does not.

If `no-skill` also passes just as easily, your skill may still be useful, but it is solving a different problem:

- efficiency
- consistency
- explainability
- tool selection

That is still valid, but it is a different claim than "the skill improved task success."

## What to compare

For each task, compare at least:

- `no-skill`
- `skill enabled`

If you are iterating on a skill, compare:

- `baseline-skill`
- `improved-skill`

If you are deciding between competing approaches, compare:

- `skill A`
- `skill B`

The important point is that the task and verifier stay the same while the condition changes.

## What a verifier should check

A good verifier should be narrow and boring.

It should check:

- required fields exist
- required values match
- numeric tolerances if needed
- expected output structure

It should avoid:

- overfitting to one exact sentence unless that sentence truly matters
- judging style when only correctness matters
- validating unnecessary internal mechanics when the output is what counts

This matters because an overly strict verifier can make a good skill look bad for the wrong reason.

## What traces are for

Traces are explanatory, not authoritative.

Use them to understand:

- whether the skill changed the workflow
- which tools the agent used
- where time was spent
- why a failing run failed

Do not use traces as the ground truth for success.

The verifier decides correctness.
The trace helps explain behavior.

## How to interpret different outcomes

### 1. `no-skill` fails, `skill` passes

This is the clearest sign that the skill encoded a missing procedure or constraint.

### 2. both pass, but `skill` is faster or cleaner

This means the task may already be solvable without the skill, but the skill still improves execution quality.

### 3. both pass with little difference

This means either:

- the task is too easy
- the skill is not adding much
- the skill's value may show up on harder tasks instead

This is still useful information.

### 4. both fail

This usually means one of:

- the task is too hard or underspecified
- the skill is too vague
- the verifier is misaligned with the task

### 5. `no-skill` outperforms `skill`

This often means the skill is:

- overconstraining
- noisy
- conflicting with the task
- pushing the agent into a brittle procedure

That is a valuable result. A skill can be harmful.

In this tutorial repo, `sales-pivot-analysis` is a concrete example of that pattern.

- After aligning the verifier to the intended task contract, most saved sales runs passed.
- But `openhands/gemini-3-pro-preview` still passed `no-skill` and failed `improved-skill`.
- The likely explanation is not that the model cannot solve the task. It is that the current "improved" sales skill nudges the model into a more brittle workbook-construction path.

That is exactly the kind of finding a skill evaluation should surface. "Improved" is only a hypothesis until it is measured.

## How to design a good skill evaluation

Use this sequence:

1. choose a bounded task
2. define the output contract
3. write the verifier
4. run `no-skill`
5. inspect the failure modes or baseline behavior
6. write or refine the skill
7. rerun with the skill enabled
8. compare outcomes first, traces second

That order matters.

If you start by writing a long skill and only later decide how to measure it, you are likely to overfit to anecdotes instead of outcomes.

## What makes a skill likely to help

Skills tend to help when they encode:

- a specific workflow
- tool usage guidance
- prioritization rules
- fallback rules
- output constraints
- error-avoidance heuristics

Skills tend to help less when they are just:

- generic advice
- broad documentation dumps
- reminders to be careful
- duplicated knowledge the model already has

The more procedural the task, the more likely a focused skill will matter.

## How many tasks you need

One task can be a good tutorial.
It is not enough to support a broad claim about skill quality.

A better pattern is:

- one task that shows a strong skill effect
- one task where the effect is small
- eventually, a small set of task types

That gives you a more honest picture:

- some skills matter a lot on some tasks
- some skills do not move much on easier tasks
- skill quality is task-dependent

## A practical rubric

Before claiming you have evaluated a skill, ask:

- Did I compare against `no-skill`?
- Did I keep the task fixed across conditions?
- Did I use a deterministic verifier?
- Did I measure pass/fail first?
- Did I look at runtime or step count as secondary metrics?
- Did I inspect traces only to explain behavior, not to define success?
- Did I test on more than one task type if I am making a general claim?

If the answer to several of those is no, the evaluation is probably too weak.

## The main takeaway

Skill evaluation does not need to be complicated.

A useful methodology is:

- one bounded task
- one verifier
- two or more conditions
- simple metrics
- traces for explanation

The point is not to create a perfect benchmark.

The point is to make it easy enough for people to test whether their skills are actually helping.
