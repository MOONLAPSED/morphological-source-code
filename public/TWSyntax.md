---
subject: TiddlyWiki syntax (in markdown, for wikilinks)
copyright: "© 2026 Morphological Source Code & Quineic Statistical Dynamics"
license-doc(s)+dist: CC BY-ND 4.0
license-code+file(s): BSD 3-Clause
  © 2023-26 Moonlapsed https://github.com/MOONLAPSED/Cognosis CC BY
copyright2: |
  © 2025-26 Phovos https://github.com/Phovos/Morphological-Source-Code CC ND
version: 0.30.8
aliases: |
  - feather wiki
  - tiddly wiki
  - fossil
---

# TiddlyWiki 5 (v5.4.0) WikiText Syntax Cheatsheet

> For users coming from Obsidian, Emacs/Org-mode, or Markdown. TiddlyWiki uses **WikiText**  a markup language that sits on top of JavaScript (you don't need to know JS to use it).

---

## 1. BASIC TEXT FORMATTING

| Effect | WikiText | Notes |
|--------|----------|-------|
| **Bold** | `''bold''` | Two single quotes |
| //Italics// | `//italics//` | Double slashes |
| **//Bold Italics//** | `''//bold italics//''` | Combine both |
| __Underline__ | `__underline__` | Double underscores |
| ~~Strikethrough~~ | `--strikethrough--` | Double dashes |
| ^^Superscript^^ | `super^^script^^` | Double carets |
| ~~Subscript~~ | `sub~~script~~` | Double tildes |
| @@Highlight@@ | `@@highlight@@` | Double at-signs |
| Em dash | `foo -- bar` | Two dashes become em dash |

---

## 2. HEADINGS

```
! Heading 1
!! Heading 2
!!! Heading 3
!!!! Heading 4
!!!!! Heading 5
```

---

## 3. LISTS

### Unordered (Bullet)
```
* Item one
* Item two
** Nested item
*** Deeper nested
```

### Ordered (Numbered)
```
# First item
# Second item
## Nested numbered
### Deeper
```

### Definition List
```
; Term
: Definition
```

### Mixed Lists
```
# Ordered
#* Unordered nested
#*; Term
#*: Definition
```

---

## 4. LINKS

### Internal Links (Tiddlers)

| Type | Syntax | Example |
|------|--------|---------|
| WikiWord (auto-link) | `WikiWord` | `CamelCase` auto-links |
| Prevent auto-link | `~WikiWord` | `~NoLink` |
| Explicit link | `[[Tiddler Title]]` | `[[My Notes]]` |
| Pretty link (alias) | `[[Display Text&#124;Tiddler Title]]` | `[[Click here&#124;Target Tiddler]]` |

### External Links

| Type | Syntax | Example |
|------|--------|---------|
| Raw URL | `http://example.com` | Auto-links |
| Pretty external | `[[Text&#124;http://example.com]]` | `[[Visit&#124;http://example.com]]` |

### Special Characters in Tiddler Titles / URL Encoding

**CRITICAL:** Tiddler titles with special characters (`#`, `[`, `]`, `|`, etc.) need special handling.

| Character | URL Encoding | In Links |
|-----------|--------------|----------|
| Space | `%20` | Use `[[Title With Space]]` |
| `[` | `%5B` | Use `[[Title]]` or widget syntax |
| `]` | `%5D` | Use `[[Title]]` or widget syntax |
| &#124; | `%7C` | Use HTML entity `&#124;` in pretty links |
| `#` | `%23` | **SEE BELOW** |

---

## 5. THE `#` PROBLEM  Tiddlers Named "#something"

This is the core of your issue. TiddlyWiki uses `#` in URLs for **two different things**:

1. **URL hash fragment**: `https://wiki.html#TiddlerName`  opens a tiddler
2. **Actual tiddler title**: A tiddler literally named `#outline`

### The Conflict

When you have a tiddler named `#outline`:
- The **permalink** button generates: `https://wiki.html#%23outline` (URL-encoded `#` = `%23`)
- But if you try to link to it with `[[#outline]]`, TiddlyWiki may interpret the `#` as an HTML anchor or list marker

### Solutions

#### A. Use the Transclude Widget (Recommended for Special Characters)

Instead of wikitext syntax, use the HTML-like widget syntax:

```wikitext
<$link to="#outline">Click me</$link>
```

Or to transclude:
```wikitext
<$transclude tiddler="#outline"/>
```

#### B. URL-Encode in Permalinks

For the **permanent link** button, the URL should be:
```
https://yourwiki.html#%23outline
```

Where `%23` is the URL-encoded `#`.

#### C. Link Syntax with Escaping

In wikitext, try:
```wikitext
[[#outline]]
```

If that doesn't work (because `#` starts an ordered list in some contexts), use:
```wikitext
<$link to="#outline">#outline</$link>
```

#### D. Avoid `#` in Tiddler Names (Practical Advice)

The `#` character is problematic because:
- It conflicts with URL hash fragments
- It conflicts with ordered list syntax (`# item`)
- It conflicts with HTML anchor links

**Better alternatives:**
- Rename to `outline` (without `#`)
- Rename to `tag-outline` or `hash-outline`
- Use a prefix like `meta-outline`

---

## 6. TRANSCLUSION (Embedding One Tiddler in Another)

### Basic Transclusion

```wikitext
{{TiddlerName}}           -- Transclude entire tiddler
{{TiddlerName!!field}}    -- Transclude specific field
{{!!field}}               -- Transclude field of current tiddler
{{TiddlerName##index}}    -- Transclude data tiddler index
```

### Template Transclusion

```wikitext
{{TiddlerName||TemplateTiddler}}   -- Render through template
{{||TemplateTiddler}}              -- Template only, no tiddler
```

### Parameterized Transclusion (v5.4.0+)

```wikitext
{{TiddlerName|param1|param2}}
{{TiddlerName||Template|param1|param2}}
```

### Filtered Transclusion (List Results)

```wikitext
{{{ [tag[meeting]] }}}                    -- List all tagged "meeting"
{{{ [tag[meeting]]||TemplateTiddler }}}  -- Through template
```

### Widget Syntax (For Special Characters in Titles)

When tiddler titles contain `||`, `!!`, or other special sequences that break the `{{}}` syntax:

```wikitext
<$transclude tiddler="title||template"/>
<$transclude tiddler="#outline"/>
<$transclude $tiddler="Sn:Hi" interlocutor="Alice" speaker="Bob"/>
```

---

## 7. IMAGES

```wikitext
[img[http://example.com/image.png]]           -- Basic image
[>img[image.png]]                            -- Align right
[<img[image.png]]                            -- Align left
[img[image.png][TiddlerName]]               -- Image links to tiddler
[img[image.png][http://example.com]]         -- Image links externally
```

---

## 8. TABLES

```wikitext
|!Header 1|!Header 2|!Header 3|h
|Cell 1|Cell 2|Cell 3|
|Cell 4|Cell 5|Cell 6|
|>|Span two columns||
|~|Span two rows|Data|
|~|~|More data|
```

- `|h` — header row
- `|>` — column span
- `|~` — row span
- `|!` — header cell

**IMPORTANT:** TiddlyWiki has NO escape mechanism for the pipe character `|` inside table cells. If you need to show a pipe in a cell, use the HTML entity `&#124;` or use an HTML table instead.

---

## 9. BLOCKQUOTES

### Single-line
```wikitext
> Quote text
>> Nested quote
>>> Deeper nested
```

### Multi-line
```wikitext
<<<
Multi-line
blockquote
<<<
```

### With Citation
```wikitext
<<<
Quote text
<<< Author Name
```

---

## 10. CODE / MONOSPACE

| Type | Syntax |
|------|--------|
| Inline code | `{{{monospace}}}` |
| Code block | `{{{` followed by lines, then `}}}` |
| No-wiki (raw) | `<nowiki>raw text</nowiki>` |
| Triple-quote escape | backtick-backtick-backtick raw text backtick-backtick-backtick |

---

## 11. HORIZONTAL RULE

```wikitext
----
---
***
___
```

---

## 12. MACROS / PROCEDURES

### Define a Procedure

```wikitext
\define mymacro(param1, param2)
Hello, $param1$ and $param2$!
\end

<<mymacro "Alice" "Bob">>
```

### Dynamic Parameters (v5.4.0+)

```wikitext
<<mymacro param={{Something}}>>
<<mymacro param={{{ [<myvar>addprefix[https:] }}}>>
```

---

## 13. VARIABLES & TEXT REFERENCES

```wikitext
<<variableName>>              -- Transclude variable
{{tiddlerTitle!!field}}       -- Field reference
{{tiddlerTitle##index}}       -- Data tiddler index
```

---

## 14. TAGS

```wikitext
<<tag "myTag">>               -- Display tag pill
<<list-links "[tag[myTag]]">> -- List tagged tiddlers
```

---

## 15. HTML IN WIKITEXT

You can embed raw HTML:

```wikitext
<html>
  <div class="custom">
    <p>Any valid HTML</p>
  </div>
</html>
```

---

## 16. ANCHOR LINKS (Within a Tiddler)

```wikitext
! Heading Title

<a id="#Bottom_of_tiddler">Target</a>

[[Go to bottom|##Bottom_of_tiddler]]
```

**Note:** TiddlyWiki anchors use `#` in `id` and `##` in `href`.

---

## 17. SHADOW TIDDlERS

System tiddlers start with `$:/`:
- `$:/core/ui/ViewTemplate/title`
- `$:/tags/ViewTemplate`

To override: Create a tiddler with the same name.

---

## 18. OBSIDIAN TO TIDDLYWIKI MAPPING

Since TiddlyWiki has no escape mechanism for `|` inside tables, this section uses a definition list instead:

; `[[Link]]` in Obsidian
: `[[Link]]` or `WikiWord` in TiddlyWiki. `CamelCase` auto-links.

; `[[Link|Alias]]` in Obsidian
: `[[Alias|Link]]` in TiddlyWiki: **pipe order is reversed!**

; `![[Embed]]` in Obsidian
: `{{TiddlerName}}` in TiddlyWiki: transclusion

; `# Heading` in Obsidian
: `! Heading` in TiddlyWiki

; `- item` in Obsidian
: `* item` in TiddlyWiki: bullet list

; `1. item` in Obsidian
: `# item` in TiddlyWiki: numbered list (conflicts with `#tag`!)

; `> quote` in Obsidian
: `> quote` in TiddlyWiki: same syntax

; backtick-code-backtick in Obsidian
: `{{{code}}}` in TiddlyWiki: inline code

; Code blocks in Obsidian
: `{{{` block `}}}` in TiddlyWiki: triple braces

; `[[#tag]]` in Obsidian
: `[[#tag]]` in TiddlyWiki  but problematic, use widgets instead

; `![[image.png]]` in Obsidian
: `[img[image.png]]` in TiddlyWiki

; Frontmatter in Obsidian
: Tiddler fields (metadata) in TiddlyWiki

; YAML tags in Obsidian
: `tags: tag1 tag2` field in TiddlyWiki

---

## 19. SPECIAL CHARACTERS SUMMARY

| Character | Issue | Solution |
|-----------|-------|----------|
| `#` | URL hash, list syntax | URL-encode as `%23`, use widgets |
| &#124; | Pretty link separator | Use HTML entity `&#124;` in tables, or widgets |
| `[[` / `]]` | Link syntax | Use widgets if in title |
| `{{` / `}}` | Transclusion syntax | Use widgets if in title |
| `!!` | Field separator | Use widgets if in title |
| `||` | Template separator | Use widgets if in title |
| `%` | URL encoding | Avoid in anchors (browser bug) |

---

## Resources

- Official docs: https://tiddlywiki.com/static/WikiText.html
- TiddlyWiki 5.4.0 Release: https://tiddlywiki.com/static/Releases.html
- GitHub: https://github.com/TiddlyWiki/TiddlyWiki5

---

*Generated for TiddlyWiki 5.4.0 (April 2026)*
