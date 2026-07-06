<!--suppress HtmlDeprecatedAttribute, HtmlUnknownTarget -->
<div align="center">
  <h1>Assets</h1>
  <p>Supplementary (non-build) assets for this font project</p>
  <h6>
    <a rel="noopener noreferrer" href="../README.md"><- Back to main README</a>
    &nbsp;·&nbsp;
    <a rel="noopener noreferrer" href="docs/README.md">Full Documentation</a>
    &nbsp;·&nbsp;
    <a rel="noopener noreferrer" href="LICENSE-MIT.md">License MIT</a>
    &nbsp;·&nbsp;
    <a rel="noopener noreferrer" href="LICENSE-OFL.md">License OFL</a>
  </h6>
</div>

<div align="center">
  <h2>What's inside</h2>
</div>

```
assets/
├── README.md        <- This reference guide
├── telegram-emoji/  <- Custom emoji pack, exported from the font sources
│   └── *.png
└── logo/            <- Brand logo, source + exports
    ├── ai/             <- Adobe Illustrator source files
    ├── svg/            <- Vector exports
    └── png/            <- Raster exports
```

> [!NOTE]
> This folder holds finished, ready-to-use assets. Anything consumed during the
> build process (UFO/glyphs/designspace sources) lives in [`sources/`](../sources)
> instead.

<div align="center">
  <h2><code>telegram-emoji/</code></h2>
</div>

A [custom emoji pack](https://core.telegram.org/stickers) built from glyphs of
this font, published via `@Stickers` (`/newemojipack`).

#### Format requirements (static emoji)

| Property   | Requirement                               |
|------------|-------------------------------------------|
| Format     | PNG (or WEBP)                             |
| Dimensions | Exactly `100x100` px                      |
| Background | Transparent                               |
| Upload as  | File (not Photo), one base emoji per file |

> [!IMPORTANT]
> Telegram enforces the `100x100` canvas strictly - anything else will be
> rejected on upload. Keep strokes bold and contrast high; emoji render tiny
> in the chat list and in text.

Animated variants are out of scope for this pack, but for reference: Telegram
also accepts `.TGS` (Lottie, 512x512 canvas, ≤64 KB) and `.WEBM` (VP9, 100x100,
≤3s, ≤256 KB, no audio) for animated custom emoji.

<div align="center">
  <h2><code>logo/</code></h2>
</div>

Font logo assets in source and export formats.

- **`ai/`** - Adobe Illustrator source. Edit here first, then re-export.
- **`svg/`** - Vector export for web use.
- **`png/`** - Raster export(s) for contexts that don't support SVG.

> [!TIP]
> Keep `ai/` as the single source of truth; `svg/` and `png/` should always be
> regenerated from it rather than edited independently, to avoid drift between
> formats.

<div align="center">
  <!--
  =====================
         FOOTER
  =====================
  -->
  <h1></h1>
  <br />
  <!-- OctalMesh Logo -->
  <a rel="noopener noreferrer" target="_blank" href="https://octalmesh.com">
    <picture>
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/logo/svg/octal_mesh_center.svg" />
      <img alt="OctalMesh" src="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/logo/svg/octal_mesh_center_white.svg" height="48" />
    </picture>
  </a>
  <br /><br />
  <!-- Socials -->
  <div>
    <!-- Telegram Badge -->
    <a rel="noopener noreferrer" target="_blank" href="https://octalmesh.com/telegram">
      <picture>
        <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/telegram.svg" />
        <img alt="Telegram" src="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/telegram_white.svg" width="48" />
      </picture>
    </a>
    &nbsp;
    <!-- YouTube Badge -->
    <a rel="noopener noreferrer" target="_blank" href="https://octalmesh.com/youtube">
      <picture>
        <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/youtube.svg" />
        <img alt="YouTube" src="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/youtube_white.svg" width="48" />
      </picture>
    </a>
    &nbsp;
    <!-- TikTok Badge -->
    <a rel="noopener noreferrer" target="_blank" href="https://octalmesh.com/tiktok">
      <picture>
        <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/tiktok.svg" />
        <img alt="TikTok" src="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/tiktok_white.svg" width="48" />
      </picture>
    </a>
    &nbsp;
    <!-- Instagram Badge -->
    <a rel="noopener noreferrer" target="_blank" href="https://octalmesh.com/instagram">
      <picture>
        <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/instagram.svg" />
        <img alt="Instagram" src="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/instagram_white.svg" width="48" />
      </picture>
    </a>
    &nbsp;
    <!-- X Badge -->
    <a rel="noopener noreferrer" target="_blank" href="https://octalmesh.com/x">
      <picture>
        <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/x.svg" />
        <img alt="X" src="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/x_white.svg" width="48" />
      </picture>
    </a>
    &nbsp;
    <!-- Reddit Badge -->
    <a rel="noopener noreferrer" target="_blank" href="https://octalmesh.com/reddit">
      <picture>
        <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/reddit.svg" />
        <img alt="Reddit" src="https://raw.githubusercontent.com/OctalMesh/OctalDesign/release/assets/icon/svg/reddit_white.svg" width="48" />
      </picture>
    </a>
  </div>
</div>
<h6>
  <div align="center">
    • • •
    <br /><br />
    This project is dual-licensed under the <a rel="noopener noreferrer" href="LICENSE-MIT.md">MIT License</a> (code)
    and the <a rel="noopener noreferrer" href="LICENSE-OFL.md">SIL Open Font License (OFL)</a> (font).
    <br /><br />
  </div>
  <div align="justify">
    <ul>
      <li>You may freely use, modify, and distribute the code under the MIT License.</li>
      <li>The font is licensed under the SIL OFL, allowing use, modification, and embedding, provided the license and attribution are retained.</li>
      <li>Modified versions of the font must be renamed to avoid confusion with the original OctalFont.</li>
      <li>Both code and font are provided "as is" without warranties.</li>
    </ul>
  </div>
</h6>
