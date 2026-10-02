# Inner Breeze TODO

Marketing plan from 2026-10-02. Tick items off as they land and add a date or
link where it helps. Inner Breeze's edge: free, no ads, no account, offline,
open source, against breathing apps that charge $60–100 a year. It is also
visual (painted practice art, the Sun Salutation characters), so put effort
where those two things matter.

## Store listing

- [x] Rewrite the Play/F-Droid short and full descriptions around what people
  search for (Wim Hof breathing, box and 4-7-8 breathing, Sun Salutation,
  meditation timer, habit tracker, no ads, no account) in en-US, de-DE,
  es-ES, fr-FR and pt-BR. (2026-10-02)
- [x] Regenerate the store screenshots from the current app at real phone and
  tablet scale: painted practice cards, a Sun Salutation pose and showcase
  habits (`make screenshot`). (2026-10-02)
- [ ] Publish the new text and screenshots on Google Play. F-Droid reads them
  from this repo at the next release. `scripts/upload-play-screenshots.py`
  uploads images only; the text goes in through Play Console.
- [ ] Make a new 1024x500 feature graphic in the painted style. The current
  one is the old pixel art.
- [ ] Add a one-line caption to each store screenshot ("Wim Hof-style
  rounds", "Follow the Sun Salutation").
- [ ] Keep "Wim Hof" out of the app title and icon. Wim Hof Method is a
  registered trademark; a description that says "based on the Wim Hof
  Method" is fine.
- [ ] Fix the Portuguese app string "Saudacao ao sol" to "Saudação ao sol".
- [ ] Give each channel its own tagged Play link, for example
  `https://play.google.com/store/apps/details?id=xyz.waozi.inbe&referrer=utm_source%3Dreddit`,
  and check Play Console's acquisition report every month.

## Short vertical video (best reach for new users)

- [ ] Record 30–60 second "breathe with me" sessions: a Wim Hof round, box
  breathing, a Sun Salutation sequence.
- [ ] Post them on YouTube Shorts, TikTok and Instagram Reels. Reels can be
  posted by hand from the phone; the Meta API hold only blocks automation.
- [ ] Finish Social's YouTube path: approval in Telegram and a background
  upload worker (yuebot `plugins/social`).
- [ ] Optional: Pinterest pins for Sun Salutation and breathing technique
  guides, which keep bringing traffic for a long time.

## Reddit

Read each subreddit's self-promotion rules first. Post as the developer, show
the app, and stay to answer comments.

- [ ] For users: r/WimHofMethod, r/breathwork, r/Meditation, r/yoga
- [ ] For the free/open-source angle: r/androidapps, r/fossdroid,
  r/opensource, r/degoogle, r/linux

## Website (inbe.waozi.xyz)

- [ ] One page per technique with the `?mini` embed, so visitors practise on
  the page: box breathing timer, 4-7-8 breathing, Wim Hof-style breathing,
  Sun Salutation steps, meditation timer.
- [ ] Put the Play and F-Droid links under each embed.

## Directories and launches (one-time)

- [ ] AlternativeTo: list Inner Breeze as an alternative to Calm, Headspace,
  Breathwrk and Prana Breath.
- [ ] Flathub: check whether `packaging/flatpak/xyz.waozi.inbe.yml` is
  published, and submit it if not.
- [ ] Open-source app lists (awesome lists, F-Droid collections).
- [ ] Product Hunt launch.
- [ ] One Show HN about how it is built: the whole app in Ziran and Kryon,
  running on Android, web, Linux and Windows. This brings developers and
  GitHub stars, not meditators, so do it once.

## Channels to keep small

- Facebook and Threads Pages: the Meta API is on hold (no business
  verification). Social is moving Facebook to the ThinkPad's signed-in
  Chromium instead.
- X: the audience is mostly developers; keep it for Ziran and Kryon.
- Telegram @lotusinbe: keeps current users engaged but does not find new ones.
