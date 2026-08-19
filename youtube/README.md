# YouTube

For people who **publish**, not just watch.

> *"You published six days ago. Last time you tagged with books, essay, comfort."*

## What it does

A channel is made over weeks, and almost nothing about that survives on its own.
What did you call the last one? What did you tag it with? How long has it been?
You end up scrolling your own uploads to answer questions about your own work.

This keeps that part.

- **Your channel is the screen.** What you published, who can see each one, the
  tags you have used, and how long since the last one. It reads entirely from
  memory, so ★it works before you connect anything★ — and when you have not
  connected, the first line tells you what to do about it.
- **The next upload knows about the last one.** Publish without tags and it says
  what you tagged with before. It does not attach them quietly: uploading cannot
  be undone, and the tags are that video's face.
- **Privacy is fail-closed.** Anything not exactly `unlisted` or `public`
  becomes `private`, and if what you asked for was not recognised it says so in
  the answer. Nothing goes public by a typo.
- **One click connects everything.** The same button covers searching and
  uploading — one allow screen, not two, and nothing to paste anywhere.
- **On the watching side, it keeps channels, not videos.** And only ones you
  come back to.

## How it works

It implements the Cosmos `plugin/v1` contract as a single file
(`youtube_scout.py`) with its translations alongside (`youtube_i18n.py`).

Reading and uploading both go through the YouTube Data API. Reading accepts
either an OAuth token or an API key, so the Connect button is enough; the API
key field is left in place as an option for people who would rather use their
own quota.

Uploads go through the resumable upload endpoint with a long timeout — a short
one would report failure while the video was in fact going up, which is the
worst possible thing to be wrong about.

★Every judgement is our own code and is plain to read★: what is missing before
an action can run, what privacy a request resolves to, whether a video has been
seen before, and whether a channel counts as a regular. None of that is asked of
a model, because a model gives a different answer each time and cannot explain
any of them.

## What it needs

| Permission | Why |
|---|---|
| `network` | To reach the YouTube API. |
| `media.publish` | ★The one that matters.★ Everything else reads other people's things; this one puts something into the world under your name. |
| `browser` | To open a video when you ask it to play one. It hands that to Cosmos's own browser tool rather than opening things itself. |
| `memory` | Without it there is no point to any of this — every publish would be the first publish. |

## What it does NOT do

- **It never makes a video title into a fact about you.** A title is what
  someone wrote to get a click that afternoon — measured on one real machine,
  55% of the interest nodes already in the graph were page titles carrying site
  tags and clickbait. Adding one per video watched makes recall worse, not
  better. What it keeps instead is the channel, and only after you return to it.
- **It does not store view or subscriber counts.** Those are true for one
  instant. A number that is already wrong is worse than no number.
- **It does not decide that you are a regular after one video.** Once is an
  event; a taste needs repetition.
- **It does not publish anything you did not ask it to publish**, and it never
  widens privacy on its own.
- **It does not claim to have watched a video.** YouTube does not hand out
  captions through the API, so when it summarizes it says plainly that it is
  working from the title and description — and when there is no description it
  says it cannot summarize rather than inventing one.

## Data and privacy

**Stays on your machine.** Your uploads (title, tags, privacy, when), and which
channels you come back to, live in your Cosmos brain on your own disk.

**Leaves your machine:** what you ask it to search for, and the video's title
and description when you ask for a summary (sent to the model you configured).
Uploads go to YouTube, which is the point of an upload.

**Never leaves:** your Google password — Cosmos never sees it. The token from
connecting goes straight into the vault and is never shown on screen or included
in an answer.

Ask *"what have I uploaded?"* to see everything it kept.

## Limits

- **Search quota is shared** when you use the Connect button, because the app
  registration is ours. Heavy users can paste their own API key in the settings
  and spend their own quota instead.
- **Summaries come from the title and description only.** There are no captions
  available through the API, so a video whose description says nothing cannot be
  summarized — and it will say so rather than guess.
- **It reads your own uploads from what it recorded**, not from YouTube. Videos
  you published some other way are not in the list.

## Setup

Open the settings and press **Connect**. That is all — the same click covers
searching and uploading.

If the button says the connection is not switched on in this build, the app
registration is missing on our side, not yours. See
[`docs/OAUTH_REGISTRATION.md`](https://github.com/honeyground-org/cosmos-billy/blob/main/docs/OAUTH_REGISTRATION.md).

## Support

Open an issue at
<https://github.com/honeyground-org/cosmos-agents/issues>.
