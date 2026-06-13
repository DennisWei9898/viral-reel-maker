# 🎬 Viral Reel Maker（爆款短影音製作 Agent）

[English](README.md) · **繁體中文**

把一支長影片——直播、演講、訪談、Podcast——變成一批**品牌化的 9:16 直式短影音**，
適用 Instagram / TikTok / YouTube Shorts / Facebook。

這是一個 AI agent（為 [Claude Code](https://claude.com/claude-code) 及相容的 agent
runtime 打造）。你給它一支長影片，再給一張**你想要的風格參考圖**；它會訪談你、
學會你的風格，然後自動產出：

- 🔎 **自動找出爆點片段**——在完整語意邊界切割（絕不斷在句中），並用短影音爆款 rubric 評分
- ✍️ **襯線標題卡**，支援 `==高光==` 與 `**重點色**` 關鍵字標記
- 🗣️ **講者人臉 PIP**——從原片裁出會動的 webcam 視窗，放在右下角
- 💬 **燒入字幕**（自動換行、不吃滿寬）＋ 留言關鍵字的 **CTA 結尾卡**
- 🎞️ **1–3 分鐘合成版**，含 cold-open ＋ 多段 re-hook，做更長的敘事弧
- 📣 **發佈 metadata**：依「平台搜尋 SEO ／ GEO 被 AI 引用 ／ 社群演算法」三層，
  產出分平台的標題與內文

**風格不是寫死的。** 引擎只讀一個*風格包*（`bg.png` ＋ `style.json`）——換風格包就換整套品牌。
用 `/huashu-design` 從參考圖即時生成，或手改 `styles/default/` 的中性起手包。

---

## 安裝

```bash
git clone https://github.com/DennisWei9898/viral-reel-maker.git
cd viral-reel-maker
./install.sh
```

安裝器會把引擎 ＋ 風格包裝到 `~/.claude/viral-reel-maker/`，並把 agent 註冊到
`~/.claude/agents/viral-reel-maker.md`。重啟你的 agent runtime，然後直接說：
**「幫我把這支影片做成 reels」**，給它一支長影片 ＋ 一張風格參考圖即可。

**環境需求**（macOS）：`ffmpeg`（完整版，`brew install ffmpeg`）、Google Chrome、
Python 3.9+、Node/Playwright（用於重新產生背景圖）。詳見 [`SETUP.md`](SETUP.md)。

---

## 運作方式

```
階段 1  訪談    → 平台、內容、調性
階段 2  參考    → 你給一張參考 reel/圖 →
                  /huashu-design 生成你的風格包（bg.png ＋ style.json）
階段 3  製作    → 轉錄 → 切段 → 評分 → 標題 → 渲染 → CTA → 驗證
階段 4  發佈文案 → 分平台標題＋內文（SEO／GEO／社群演算法三層）
```

引擎 100% 由風格包驅動，**不含任何專有模板、評分權重或資料**——`styles/default/`
是中性、去品牌的起手包。帶上你自己的風格與素材即可。

---

## 聯絡

由 **Dennis Wei** 製作。如果你對完整 pipeline、客製風格系統，或想一起合作
AI 驅動的內容生產有興趣，歡迎聯絡：

- 💼 LinkedIn：https://www.linkedin.com/in/dennis-wei-47393a14a/
- ✉️ Email：dennis.xd.wei@gmail.com

---

## 授權

[MIT](LICENSE) © Dennis Wei。自由使用、fork、做出你自己的 reels。
