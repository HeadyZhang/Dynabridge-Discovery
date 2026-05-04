# DynaBridge Pipeline 进展汇报

**日期**: 2026年4月27日

---

## 一、系统现在能做什么

大家好，我先同步一下 DynaBridge 自动化品牌发现系统目前的能力。

一句话总结：**输入一个品牌名字，不需要任何客户素材，系统全自动输出一套交付级的 PPT 和 PDF 报告。**

> In one sentence: input a brand name with zero client materials, and the system autonomously outputs a delivery-ready PPT and PDF report.

具体来说：

### 1. 全品类通用

之前系统只能跑水壶（Owala）这一个品类，很多逻辑是写死的。现在已经全面泛化，美妆、食品、科技、家居、服装、运动——任何品类的品牌丢进去都能跑。系统会自动识别品类，自动调整分析框架、问卷内容、和报告结构。

> Previously locked to one category (water bottles). Now fully generalized — beauty, food, tech, home, apparel, sports — any category. The system auto-detects the category and adapts the entire analysis framework accordingly.

### 2. 自主研究能力

系统会自动执行 60-100 轮 web search，分三个阶段：

- **品牌研究**（30轮）：品牌背景、创始故事、产品线、定价、社交媒体、专利、营收数据
- **竞品研究**（40轮）：每个竞品 4 轮深度搜索，覆盖产品、定价、定位、消费者口碑
- **消费者研究**（30轮）：购买行为、痛点、品牌忠诚度、人群画像、生活方式信号

如果搜索结果不够完整（质量分低于 8/10），系统会自动针对缺失的字段发起补充搜索，比如缺创始故事就专门搜创始故事，缺产品数据就专门搜产品。

> 60-100 rounds of autonomous web search across 3 sessions (brand, competitors, consumers). If quality score < 8/10, the system auto-triggers targeted gap-fill searches for specific missing fields.

### 3. 专业级消费者问卷

系统会根据品牌和品类自动生成一份 30+ 题的消费者调研问卷，方法论对标 Kantar、Ipsos、Nielsen 等头部调研公司：

- **问卷结构**：筛选题 → 行为题 → 驱动因素 → 品牌评估 → 生活方式 → 开放题 → 人口统计（放最后，减少弃答）
- **品牌漏斗**：无提示知名度（开放题）→ 提示知名度 → 考虑 → 试用 → 常用 → 最爱 → NPS（0-10标准量表）
- **质量控制**：注意力检测题、选项随机化、跳转逻辑、防引导性提问检查
- **可直接导出 Qualtrics**：生成的问卷支持一键导出为 Qualtrics QSF 格式，导入后可直接发放

问卷生成后会经过两轮质量验证：结构性检查（自动修复缺失的品牌漏斗、注意力题等）+ AI 专家审查（检查引导性问题、歧义选项等，发现问题自动修正）。

> Auto-generates a 30+ question survey following Kantar/Ipsos methodology: proper brand funnel (unaided → aided → consideration → trial → NPS), attention checks, randomization, skip logic. Exportable to Qualtrics QSF format. Two-pass quality validation with auto-fix.

### 4. 全流程质量门控

整个 pipeline 现在有 3 道 AI 质量检查：

| 位置 | 检查内容 | 处理方式 |
|------|---------|---------|
| 分析完成后 | 策略一致性 — capabilities/competition/consumer 之间是否自相矛盾 | 标注矛盾点，分析师可据此调整 |
| 问卷生成后 | 方法论合规 — 品牌漏斗完整性、NPS 格式、随机化覆盖、引导性问题 | 自动修复 |
| PPT 生成后 | 渲染质量 — 文字溢出、空内容区域、图片缺失、slide 数量 | 输出 0-100 质量分 |

> Three AI quality gates: post-analysis strategy coherence check, post-survey methodology validation with auto-fix, post-PPT rendering QA with 0-100 quality score.

### 5. 反幻觉机制

品牌分析中所有结论都标注数据来源层级：

- **OBSERVED**（观测到的）：来自网页、评论、电商数据 — 最强
- **INFERRED**（推断的）：从观测信号逻辑推导 — 中等
- **INDUSTRY KNOWLEDGE**（行业常识）：通用行业模式 — 最弱

数据不足时，系统会先自动补搜。补搜后仍然不足的，宁可写得短但准确，不会编造数据来填充页面。

> All findings labeled by evidence tier: OBSERVED > INFERRED > INDUSTRY KNOWLEDGE. When data is thin, the system searches more first; if still insufficient, it writes shorter but stays honest rather than fabricating.

---

## 二、接下来需要品牌团队提供的

为了让系统真正达到可交付的质量标准，我们需要品牌团队的以下支持：

### 1. 测试品牌名单（3-5个）

请提供 3-5 个真实的品牌名字，最好覆盖不同品类。比如：
- 一个美妆/护肤品牌
- 一个食品/饮料品牌
- 一个科技/电子品牌
- 一个家居/生活方式品牌

我们会用这些品牌跑完整的端到端测试，验证系统在不同品类上的表现。

> Please provide 3-5 real brand names across different categories for end-to-end testing.

### 2. 交付标杆 Deck

请提供一份过去真正交付给客户的品牌发现 deck，作为我们的质量标杆。我们需要知道：
- 什么样的 insight 深度是"交付级"的
- 每一页的信息密度和措辞风格
- 哪些 slide 是必须有的，哪些是可选的

> Please share one real past delivery deck as our quality benchmark — insight depth, information density, required vs optional slides.

### 3. 问卷用途确认

目前系统生成的问卷有两种用法：
- **模拟模式**：系统自动用 AI 生成模拟的消费者回答数据（当前默认）
- **真实模式**：导出到 Qualtrics 发给真实消费者 panel，收回真实数据后上传

请确认你们的使用场景是哪种，或者两种都需要。这会影响我们对问卷精度和导出格式的投入方向。

> Confirm survey use case: AI-simulated responses (current default), real consumer panel via Qualtrics, or both? This determines our optimization priority.

### 4. 品牌策略师逐页 Review

这是对我们帮助最大的一件事。等我们用测试品牌跑完一份完整输出后，请一位品牌策略师：
- 逐页看一遍 PPT
- 标注每一页：**到位** / **太浅（需要更深的什么）** / **有误（哪里不对）**
- 特别关注：insight 是否有洞察力，数据是否可信，策略建议是否可执行

一轮这样的反馈，比我们自己调十轮都有用。

> After we run a test brand, please have a brand strategist review the full output page by page, marking each slide as: solid / too shallow (what's missing) / incorrect (what's wrong). One round of this feedback is worth ten rounds of our own tuning.

### 5. 竞品名单偏好

目前竞品发现是全自动的（系统通过 web search 找到 6-10 个竞品）。请确认：
- 自动发现的竞品名单是否足够好？
- 是否需要手动指定/覆盖竞品的能力？
- 是否有些客户会自带竞品名单？

> Competitor discovery is fully automated. Do you need manual override capability? Do some clients come with their own competitor lists?

---

## 三、后续开发路线（参考）

| 优先级 | 事项 | 依赖 |
|--------|------|------|
| P0 | 用 3-5 个测试品牌跑端到端测试 | 需要品牌名单 |
| P0 | 根据策略师 review 调优 insight 深度 | 需要逐页反馈 |
| P1 | 真实问卷发放流程（如需要） | 需要确认问卷用途 |
| P1 | 报告中英双语支持优化 | — |
| P2 | 客户自助上传品牌素材的能力 | — |
| P2 | 多轮迭代（策略师在线修改→重新生成） | — |

---

**总结：系统的"骨架"已经搭好，能跑通任何品牌。接下来最重要的是拿真实品牌测试 + 品牌专家逐页反馈，把"能用"变成"好用"。**

> Summary: The pipeline skeleton is complete and works for any brand. The critical next step is real brand testing + page-by-page expert feedback to go from "functional" to "delivery-ready."
