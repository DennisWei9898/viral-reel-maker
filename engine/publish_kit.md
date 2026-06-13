# publish_kit — short-video publishing metadata (title + caption + hashtags)

How to title and write the post so a reel gets **found** (platform + Google
search), **cited** (AI engines), and **recommended** (IG/TikTok/FB algorithms).
Used by the agent's "Publish metadata" phase, after `publish_meta.py` scaffolds
a per-platform worksheet.

> Source-confidence markers (keep them when you cite a claim):
> **[OFFICIAL]** platform statement · **[STUDY]** third-party data · **[INDUSTRY]**
> creator/SEO experience. Most numeric specifics below are [INDUSTRY] — treat as
> defaults and A/B against your own data.

## The 3 layers (every post serves all three)

| Layer | Audience | Question | The lever |
|---|---|---|---|
| **Search SEO** | platform search + Google | can it be found? | keywords in the first words of the caption + on-screen text + voiceover (platforms index all three) |
| **GEO** | ChatGPT / Perplexity / AI Overview | can it enter the AI answer? | **AI reads text, not video** — write the point as a citable answer + name the entity/brand; host the video on your site with a full transcript |
| **Social algo** | IG / TikTok / FB feed | will it be pushed? | completion rate, **sends/saves**, watch time — hook in line 1, CTA to save/share |

Universal rules:
- **AI only reads text.** The caption / on-screen text / transcript must carry the
  point — the pixels don't count for search or GEO. [INDUSTRY][STUDY]
- **Don't paste one caption across all four platforms**; re-watermarked reposts get
  down-ranked. Keep the core message, rewrite hook/caption/hashtags/audio per platform. [INDUSTRY]
- A few precise hashtags (3-5) beat 20+. [OFFICIAL for IG/FB · INDUSTRY for TikTok]

## Per-platform templates

### Instagram Reels
- **Caption**: main keyword in the first 1-2 lines (real spoken search terms, not
  stuffing). Mosseri: caption is a ranking signal and keywords beat hashtags for
  search. [OFFICIAL via Hootsuite/Buffer]
- **Hashtags**: 3-5 relevant. Mosseri: hashtags don't add reach or follows. [OFFICIAL]
- **Alt text**: write it manually (Accessibility menu) with a keyword. [INDUSTRY]
- **First comment**: supplementary keywords / link (caption body is the index driver).
- **Signals**: completion rate is the strongest single reach signal; watch time,
  likes/reach, **sends/reach** are top three. CTA "save / send to a friend" > "follow". [OFFICIAL]
- Template: `[pain-point or curiosity keyword]。[one-line answer]。Save it 👇 #topic #subtopic #context`

### TikTok
- **4-layer keyword**: same keyword in caption + on-screen text + spoken voiceover
  + hashtag, keyword front-loaded (caption opening has highest weight). [INDUSTRY, multi-source]
- **Hashtags**: 3-5 focused (20+ broad tags can trip spam filters). [INDUSTRY]
- **Search intent**: ~65% of Gen Z use TikTok as a search engine → question-style
  keywords. [STUDY]
- **Signals**: completion, engagement, search-intent match; hook in 2s, high energy.
- Template: `[search-style question keyword]｜[answer point] #mainkeyword #longtail`

### YouTube Shorts (the one place to do title SEO)
- **Title**: main keyword front-loaded within ~60 chars; promise the payoff, plain
  not clickbait. [INDUSTRY]
- **Description**: main keyword in the first sentence (~150 chars); 300-500 words
  feeds both YouTube and Google. [INDUSTRY]
- **Google indexing**: title/description/thumbnail/transcript are all analysed.
  When embedding on a site, add VideoObject schema (name, description, thumbnailUrl,
  uploadDate, duration, contentUrl) + a video sitemap (can save 3-7 days to index). [INDUSTRY]
- Hook must read silently (homepage feed autoplays muted). [INDUSTRY]

### Facebook Reels
- **Caption**: NLP scans long captions for relevance; keyword context > hashtags. [INDUSTRY]
- **Meta**: captions with no link, little ALL-CAPS, and **≤5 hashtags** perform better. [OFFICIAL via multi-source]
- **Pinned first comment**: FB weights a 10+ word substantive threaded reply heavily
  → pin a real comment that invites discussion. [INDUSTRY]
- **Signals**: watch time strongest; completion/rewatch/engagement → wider push.

## GEO note (getting cited by AI)
Short video is **discovery, not citation fuel**. To get cited: put the point as a
clear answer + explicit brand/entity mention in the caption/pinned comment, and
**embed the video on your own page with a corrected full transcript + summary** so
AI engines can read the text. Auto-captions aren't enough — fix names/terms.
A 10-20 min Q&A transcript (~1.5-2k words) is far more citable than a 30s clip. [INDUSTRY]

## Title: same across platforms?
**No.** YouTube = a search engine → keyword-loaded title. IG/TikTok = hook-style
title (curiosity gap / question), keywords folded into the caption instead. One
video, per-platform: keep the message, swap hook + caption + hashtags + audio. [INDUSTRY]

## Post-publish flywheel
- Distill the reel's point into an 80-120 word text post (FB/Threads/blog) so AI
  engines can read it (they can't read the video).
- Track: platform search impressions, Google video indexing, whether AI engines
  mention/cite the brand.

## Sources
Hootsuite IG algorithm · Buffer IG · Later IG SEO · SEOSherpa TikTok SEO ·
VdoCipher / Levitate video SEO · SocialChamp FB · Meta original-content rules ·
Arfadia GEO-for-YouTube · Averi GEO guide · The Social Skinny cross-platform.
(2026; verify platform-official claims at the source before relying on them.)
