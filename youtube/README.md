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
- **Connection and permission are separate.** The current Connect button obtains
  API access. Permission to search does not grant permission to publish.
- **On the watching side, it keeps channels, not videos.** And only ones you
  come back to.

## How it works

It implements the Cosmos `plugin/v1` contract. The agent, translations and
dedicated HTML workspace ship together in this folder. Cosmos 0.3.0 or later
supports the interactive workspace; older cores retain the read-only view.

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

The development version declares permissions per action: search, info, summarize
and trending require `network` + `memory`; play also requires `browser`; upload
requires `network` + `memory` + `media.publish`. The saved workspace requires
`memory`. The underlying browser tool applies its own permissions when opening a
video. On a core supporting this new contract, disabling publication keeps reading
available and reading does not ask for publication approval. Existing released cores
still check the complete agent permission set; this change has not been released.

Account integration and upload verification are deferred until the final integration
stage. Working together in a signed-in website, one-time API authorization for
background work, and a combination of both remain options to evaluate. The current
implementation uses the API; automated Studio uploads are not implemented.

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
- **It does not claim to have watched a video.** This agent does not retrieve
  captions, so when it summarizes it says plainly that it is
  working from the title and description — and when there is no description it
  says it cannot summarize rather than inventing one.

## Data and privacy

**Saved in your Cosmos account.** Uploads (title, tags, privacy, when), explicit
lookups and opening requests use your configured Cosmos brain. Local installations
use local storage; hosted accounts use their configured service storage.
The latest search or summary replaces the previous workspace results in user-scoped
agent state, not an interest graph. Opening a URL is never recorded as watching.
Repeated channel lookups count distinct videos per day, not repeated details/summary
calls for the same video. This is not a watch-time or preference score.

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
- **Summaries come from the title and description only.** Captions are not
  retrieved by this agent, so a video whose description says nothing cannot be
  summarized — and it will say so rather than guess.
- **It reads your own uploads from what it recorded**, not from YouTube. Videos
  you published some other way are not in the list.
- **An interrupted upload has an uncertain outcome.** Check the YouTube channel
  before retrying. Automatic resumable-session recovery is not implemented.
- **Permissions are currently agent-wide in Cosmos.** Disabling a declared
  capability can block the whole agent, including read actions. Action-specific
  publishing permission separation remains follow-up work.

## Interactive workspace

On Cosmos 0.3.0+, open this agent's view in the main screen or its own window.
The publication timeline stays beside a reference desk: search, select a video,
load details, summarize its description or open it through Cosmos's browser tool.
The view reads stored results without making background YouTube API calls. State
updates preserve your search draft. Motion follows reduced-motion preferences.
Uploads are requested in Cosmos chat with a file, title and privacy; the workspace
does not automatically publish or imply that a summary used the video's content.

YouTube's captions API exists, but downloading a track requires authorization and
sufficient permissions: [official reference](https://developers.google.com/youtube/v3/docs/captions/download).

## Development verification

Use a temporary `COSMOS_HOME` for tests; do not point it at a real user's data.
Run `python -m pytest youtube/tests -q` from the parent repository. For UI checks,
run `python youtube/scripts/preview_workspace.py` and then
`node youtube/scripts/check_workspace_ui.mjs` with Playwright installed (or set
`YOUTUBE_PLAYWRIGHT_MODULE` to its module path). The preview uses synthetic data,
the real Cosmos renderer/CSP and isolated storage; it cannot publish a video.

## Setup

Open the settings and press **Connect**. That is all — the same click covers
searching and uploading.

If the button says the connection is not switched on in this build, the app
registration is missing on our side, not yours. See
[`docs/OAUTH_REGISTRATION.md`](https://github.com/honeyground-org/cosmos-billy/blob/main/docs/OAUTH_REGISTRATION.md).

## Support

Open an issue at
<https://github.com/honeyground-org/cosmos-agents/issues>.

### Visual workspace follow-up (2026-09-09, unreleased)

Search/details retain API-provided thumbnails and use the new `prepare_agent_images`
context contract to deliver bounded raster data. Images stay in the account workspace;
view refreshes make no external requests. Failed/missing thumbnails use a labeled fallback.
The new image contract is not included in the previously published core.

The publication chart counts the latest 12 uploads already recorded by Cosmos, by date
and visibility. It is not a view-count or channel-performance chart. Motion can be paused
and respects reduced-motion/hidden-view state. This pass has 110 passing agent tests.

### Independent display follow-up (2026-09-11, unreleased)

Choose **Channel and references** or **Focus on research** inside the agent's own
workspace. Research puts the results beside the selected video's image, details
and description-based summary. Layout is saved per user and restored on reopening.
The original window keeps its draft; a new window restores saved results and layout.

On the matching development core and Electron shell, display placement can be
`screen`, `window` or `browser`: integrated Cosmos, a separate app window, or the
OS browser. On web, both separate destinations use browser windows/tabs.
Cosmos hosts and authenticates the view; this agent owns its HTML/CSS and interaction.
A local app can authorize a browser with a short-lived one-use link. Google account
integration remains separate and deferred; the setup section above describes the
existing combined connection, whose read/upload scope separation is still pending.

117 agent tests and isolated installation/display checks pass. Real Google accounts,
packaged-app OS browser launch and published updates remain unverified.
