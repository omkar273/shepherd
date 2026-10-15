# Simplified Technical English

Write all prose in ASD-STE100 Simplified Technical English (STE). STE uses
short sentences, one meaning for each word, and a fixed word order. A reader,
human or agent, gets the same meaning on the first read.

## Scope

Write these in STE: docs, skill files, `AGENTS.md` and `CLAUDE.md` text, code
comments, commit messages, PR bodies, review findings, and reports.

Keep these as they are:

- Code, commands, file paths, identifiers, and error text.
- Quoted text, and cue words that match what a user types.
- A format that the repo or a tool sets, for example a commit prefix or a
  PR template. Write the prose inside the format in STE.

## Words

- Use one word for one meaning. Use the same word each time. Do not change
  to a synonym.
- Use the plain, common word: "use", not "utilize". "Start", not "commence".
  "Make sure", not "ensure". "Before", not "prior to". "To", not "in order to".
- Use the technical name of a thing (a file, a command, a type) exactly.
- Define a term that is not common English the first time you use it.
- Use no more than three nouns in a cluster. Break a longer cluster with
  "of", "for", or a verb.
- Keep the articles ("a", "an", "the"), the subject, and the verb. Do not
  drop words or use contractions to make a sentence shorter: write "do not",
  not "don't".

## Verbs

- Use only these forms: the imperative, the infinitive, the simple present,
  the simple past, and the future with "will".
- Use the past participle only as an adjective: "the changed file".
- Do not use the perfect or the progressive ("has run", "is running").
- Use an "-ing" word only as a noun or as part of a technical name.
- Use the active voice. Name the actor. In a description, use the passive
  only when the actor is not known or not important.
- Use "must" for a rule and "can" for an ability. Do not chain modal verbs.
  Write an uncertainty as a separate, plain sentence.

## Sentences

- Write an instruction in 20 words or fewer. Write a description in 25 words
  or fewer.
- Write an instruction as a command (the imperative).
- Write one instruction in each sentence. Join two actions only when the
  reader does them at the same time.
- If an instruction has a condition, put the condition first: "If the test
  fails, read the log."
- Put the main clause first. Put the key information at the start.
- Do not use semicolons. Write two sentences or a list.
- Use a vertical list for three or more steps, items, or conditions. Number
  the steps that have an order.

## Paragraphs

- Write one topic in each paragraph. Put the topic sentence first.
- Write no more than six sentences in a paragraph.

## Warnings

Start a warning with a short command. Then give the risk in one sentence:
"Keep the tenant check. Without it, a user can read data from a different
tenant."

## Before you say done

1. Run `python3 <shepherd>/scripts/ste_lint.py <file>...` on each markdown
   file that you changed. For a commit message or a PR body, send the text to
   stdin and pass `-`. Fix each finding.
2. Read each sentence that you wrote. The script cannot check voice, noun
   clusters, or one meaning for each word.
2. Count the words in each long sentence. Split each sentence that is over
   the limit. Keep every fact, condition, and limit of scope when you split.
3. Replace each semicolon, each perfect or progressive verb, and each passive
   verb that has a known actor.
