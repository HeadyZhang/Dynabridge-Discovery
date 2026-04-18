# 8 Sample PPT Visual Layout Deep Analysis

Based on slide-by-slide parsing of 864 slides across 8 brand discovery decks.

---

## 1. Universal Section Structure

All 7 discovery PPTs (excluding EcoBags which is a research report) follow the **same macro structure**:

| Section | Typical Slide Range | Avg Slides |
|---------|-------------------|------------|
| Cover | 1 | 1 |
| Process Overview | 2-4 | 2-3 |
| **Capabilities** ("A closer look at the brand") | 5-~12 | 6-8 |
| **Competition** ("A closer look at the competition") | ~10-~35 | 8-28 |
| **Consumer Transition** ("A closer look at the consumer") | divider only | 1 |
| Demographics & Background | varies | 4-6 |
| Shopping Habits, Usage, Attitude | varies | 8-14 |
| Brand Evaluation & Competitor Analysis | varies | 5-8 |
| **Market Segmentation** | varies | 30-40 |
| Thank You | 1 | 1 |
| Research Appendix | varies | 10-20 |

### Section Divider Pattern (CONSISTENT across all 7):
- Uses "Overview Slide" or "Divider Slide" layout
- Contains 4 text boxes: title + "Capabilities" / "Competition" / "Consumer" breadcrumb
- 1 group shape (the visual breadcrumb indicator showing which section is active)
- Always formatted as: "A closer look at the [section name]"
- ZERO images, ZERO charts — purely typographic

---

## 2. Layout Pattern Distribution (across all 8 decks)

| Pattern | Avg % | Description |
|---------|-------|-------------|
| **CHART** | 22% | Chart-focused slides (bar, donut, stacked bar) |
| **TEXT+RIGHT-IMG** | 14% | Text left, image right (~45% width) |
| **IMG+TEXT** | 12% | Mixed image+text, various positions |
| **TABLE** | 16% | Table-focused (mostly appendix/research data) |
| **LEFT-IMG+TEXT** | 10% | Image left, text right |
| **DIVIDER** | 8% | Section dividers, minimal content |
| **GROUP-BASED** | 6% | Complex layouts built with grouped shapes |
| **FULL-BG** | 5% | Full-bleed background image with text overlay |
| **TEXT-HEAVY** | 5% | 5+ text boxes, no images |
| **MULTI-IMG** | 4% | 3+ images (competitor logos, product grids) |

### Key Insight: Discovery decks are NOT image-heavy
- Average only **1.3 images per slide**
- Average **4.7 text boxes per slide**
- Average **330 characters per slide**
- Most visual richness comes from **charts** and **grouped shapes**, not photos

---

## 3. Competitor Section Layout Patterns

### Structure per competitor (consistent across all decks):
Each competitor gets **2-4 slides** in this pattern:

#### Slide A: "Competitor Banner" (Overview Slide)
- Layout: "Overview Slide" — dark/colored background
- Content: Just the competitor name: "A closer look at [Brand Name]"
- 0 images, 1 text box, 0 groups
- Acts as a breathing room divider

#### Slide B: "Positioning Theme" 
- Layout: "Blank" or "Text Slide"
- Title: ALL-CAPS strategic theme (e.g., "VISUAL IDENTITY ALIGNED WITH INCLUSIVITY")
- 1-2 text boxes with strategic paragraph (150-250 chars)
- Sometimes 1 supporting image or group shape
- Examples from RSLove:
  - Slide 14: "VISUAL IDENTITY ALIGNED WITH INCLUSIVITY"
  - Slide 18: "INCLUSIVITY IN ACTION, NOT JUST ON PAPER"
  - Slide 21: "DEMOCRATIZING SEXY WITH SUBSCRIPTION ACCESS"

#### Slide C: "Positioning & Key Learnings" (GOATClean/CozyFit style)
- Layout: "Blank" — 2-3 images + 3 text boxes
- Left side: competitor logo/product image
- Right side: Two sections with bold headers:
  - "POSITIONING" — 3 strategic themes as bold-label:detail bullets
  - "KEY LEARNINGS" — 3 takeaways for the target brand
- ~600 chars total
- Example (GOATClean Slide 18): "STEAMFAST — POSITIONING & KEY LEARNINGS"

#### Slide D: "Competitor Grid Overview" (appears once per section)
- Layout: "Blank" — multiple brand logos/images (6-12 images)
- Title: "WE LOOKED AT MANY [CATEGORY] BRANDS"
- Subtitle: strategic framing of competitive review purpose
- Example: RSLove Slide 9 (12 images), CozyFit Slide 17 (9 images)

### Two competitor layout styles across decks:
1. **RSLove style**: Each competitor gets a banner slide + 2-3 theme slides (verbose, narrative)
2. **GOATClean/GlacierFresh style**: Each competitor gets a single "Positioning & Key Learnings" slide (compact, structured)

---

## 4. Consumer Segment Section Layout (THE most systematic pattern)

### Each segment gets exactly 6 slides in this order:

#### Slide 1: FULL-BG INTRO (the "Meet the..." slide)
- Full-bleed background image (100% coverage)
- Segment name as overlay text
- Summary narrative paragraph (800-1500 chars)
- Quote/persona statement in first person
- Example (GOATClean Slide 55): "Summary: Smart Shoppers are value-driven pragmatists..."
  - Has segment name "SMART SHOPPER"
  - First-person quote: "I compare prices carefully and focus on reliable products..."

#### Slide 2: RESPONDENT PROFILE (demographic breakdown)
- 7 images (small icons) + ~20 text boxes + 0 groups
- Gender split, generation, race/ethnicity charts
- Small icon images at ~0.6x0.6in positions
- Title: "[SEGMENT NAME] - RESPONDENT PROFILE"

#### Slide 3: A CLOSER LOOK - DATA (group-based layout)
- 1 image + 3 text boxes + **7 group shapes**
- The 7 groups contain: donut charts, stat callouts, data visualizations
- Key data: willingness to pay, premium definition, color/style preferences
- Title: "[SEGMENT NAME] – A CLOSER LOOK"
- Base n = XXX notation

#### Slide 4: A CLOSER LOOK - PURCHASE DRIVERS
- 0 images + 10-12 text boxes + 0 groups
- Top 3/5 purchase factors with percentages
- Brand awareness data
- Verbatim consumer quotes
- Dense text layout — highest text count per slide (~700-1000 chars)

#### Slide 5: A CLOSER LOOK - BEHAVIORAL SUMMARY
- 0 images + 5 text boxes + 0 groups
- Four labeled columns: "Social Media Usage" | "Purchase Drivers" | "Pain Points" | "Pre-Purchase Activities"
- Segment name as header
- Summary text in each column

#### Slide 6: SOCIAL MEDIA & LIFESTYLE
- 4 images + 5 text boxes + 0 groups
- Social media platform usage with percentages
- Music preferences (e.g., "45% like Hip-Hop / R&B")
- Lifestyle/cultural signals
- Images are social media platform icons/screenshots

### After all segments:

#### Target Recommendation Slide:
- "SECONDARY TARGET: [SEGMENT NAME]"
- "Why We Expand to Them Next:" with strategic reasoning
- ~700 chars

#### De-prioritization Slide:
- "WHY WE'RE DE-PRIORITIZING OTHER SEGMENTS (FOR NOW)"
- Each de-prioritized segment gets a paragraph of reasoning
- Highest char count slides (~1100-1800 chars)
- Pure text, no images

---

## 5. Capabilities Section Layout

Slides 5-12 typically, containing:

### Brand Overview slides:
- **Process slide** (Slide 2-3): 
  - "OUR BRAND BUILDING PROCESS" 
  - 2 images + 8-9 text boxes + 2 groups
  - Three-step flow: Capabilities → Strategy → Identity

### Capability detail slides:
- Mix of LEFT-IMG+TEXT and TEXT-HEAVY patterns
- Product screenshots, Amazon listings, website captures
- Strategic summary with "Capabilities Insight:" callout
- ~760 chars on summary slides

### Capability Summary slide:
- TEXT-HEAVY (0 images, 3 text boxes)
- Bullet-point strengths and weaknesses
- "CAPABILITIES – SUMMARY" header
- Strategic insight paragraph at bottom

---

## 6. Chart Usage Patterns

Charts appear in **22% of all slides** — the dominant visual element.

### By section:
| Section | Chart Types Used |
|---------|-----------------|
| Demographics | Donut (gender), Stacked bar (generation, ethnicity) |
| Shopping Habits | Horizontal bar (frequency, channel), Stacked bar (satisfaction) |
| Brand Insights | Bar chart (awareness, favorability), Table (detailed scores) |
| Purchase Drivers | Horizontal bar with % labels |
| Segmentation | Donut (segment size), Grouped shapes with embedded charts |

### Chart positioning:
- Most charts: full-width or right-aligned (~60% of slide width)
- Demographics charts: paired (gender donut left + generation bar right)
- Purchase driver charts: stacked vertically with labels

---

## 7. Image Usage Patterns

### Full-bleed backgrounds (5% of slides):
- Used for: segment intro slides, section transitions
- Always 13.3x7.5in (exact slide dimensions)
- Text overlaid in white or dark with semi-transparent backing
- Each segment gets 1 full-bleed intro

### Inset product/brand images:
- Typically 2.0-3.0in wide, positioned left at (0.5-1.5, 1.5-3.0)
- Used for: brand logos, product shots, competitor logos
- Competitor grid slides: 6-12 small logos at ~2.8x0.5in each

### Icon images:
- Small, 0.5-0.7in, used for:
  - Social media platform icons (Slide 5 pattern: marital status icons)
  - Lifestyle/demographic icons
  - Positioned in clusters at bottom or right side

### Social media screenshots:
- 4 images per segment lifestyle slide
- Positioned as a 2x2 or horizontal strip

---

## 8. Rhythm and Pacing

### The "breathing" pattern:
```
DIVIDER (sparse) → OVERVIEW (moderate) → DATA (dense) → DATA → DATA → FULL-BG (breathing) → DATA → DATA → ...
```

### Dense vs. sparse alternation:
- **Every 4-6 dense data slides** are interrupted by either:
  - A full-bleed image slide
  - A divider slide
  - A segment banner (Overview Slide)
- This prevents "wall of data" fatigue

### Character count rhythm (typical segment block):
```
Slide 1 (FULL-BG):    800-1500 chars  ← narrative hook
Slide 2 (PROFILE):     200-300 chars  ← visual demographics
Slide 3 (A CLOSER):    100-200 chars  ← group-based data viz
Slide 4 (DRIVERS):     700-1000 chars ← densest data
Slide 5 (SUMMARY):      80-100 chars  ← column headers only
Slide 6 (SOCIAL):      200-400 chars  ← lifestyle data
```

### Appendix pacing:
- Table after table after table — no breathing room needed
- Average 80-150 chars per appendix slide
- Pure data reference, not meant to be presented

---

## 9. Unique Visual Techniques

### Group shapes as data containers:
- **7 group shapes per "A Closer Look" slide** — each group contains embedded mini-charts, stat callouts, and formatted data
- This is the most complex visual pattern and cannot be recreated with simple text+image layouts

### Breadcrumb navigation:
- Section dividers show "Capabilities | Competition | Consumer" with the active section highlighted
- Implemented as a group shape with colored indicators

### Dual-column summary format:
- Behavioral summary slides use 4 equal columns: "Social Media Usage | Purchase Drivers | Pain Points | Pre-Purchase Activities"
- Headers are orange/teal, content is black text below

### Segment intro first-person quotes:
- Every segment's full-bleed intro includes a first-person statement:
  - "I compare prices carefully and focus on reliable products that meet my needs"
  - Used as an empathy device — the reader "meets" the persona

### Strategic ALL-CAPS headers:
- Competitor positioning themes always use ALL-CAPS for the strategic hook
- Creates visual hierarchy: ALL-CAPS theme → normal-case detail paragraph

---

## 10. Implications for ppt_generator.py

### Currently missing in our generator:
1. **6-slide segment block pattern** — we don't systematically produce this sequence
2. **Group shapes** — we generate simple text+chart, but samples use complex grouped data vizualizations
3. **Breadcrumb navigation** on section dividers
4. **Full-bleed persona intros** with first-person quotes
5. **Dual-format competitor slides** (banner + positioning/learnings)
6. **4-column behavioral summary** layout
7. **Social media lifestyle slides** with platform icons

### What we do well:
1. Section divider structure (matching)
2. Chart generation (donut, bar, word cloud)
3. Text-heavy insight slides
4. Demographics breakdown

### Priority improvements:
1. Implement the 6-slide segment block as a repeating template
2. Add full-bleed background image support for segment intros
3. Create competitor "Positioning & Key Learnings" dual-panel layout
4. Add behavioral summary 4-column layout
5. Integrate social media/lifestyle data slides with icon images
