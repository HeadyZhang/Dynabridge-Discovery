# Module B — 原子化架构拆解

## 总览

Module B 由 3 个独立子系统组成，挂载在同一个 FastAPI 应用上：

```
Module B
├── Knowledge Base (案例知识库)      ← 真实数据，48个品牌案例
├── Datacube (营销决策引擎)          ← 样本数据，16个demo campaigns
└── Consumer Discovery (消费者研究)   ← 空表，只有schema
```

---

## 一、文件清单 (17 个 Python 文件)

### 1.1 基础设施层 (5 个)

| 文件 | 功能 | 数据性质 | 状态 |
|------|------|----------|------|
| `auth.py` | Google Service Account 认证 → 返回 Drive API 客户端 | 真实凭证 | ✅ 生产可用 |
| `gdrive.py` | Google Drive 文件操作: 列目录、下载、格式转换 | 真实 Drive | ✅ 生产可用 |
| `gdrive_watcher.py` | Drive 变更轮询: 检测新增/修改/删除文件 | 真实 Drive | ✅ 生产可用 |
| `extractor.py` | 文件内容提取: PPTX/PDF/DOCX/XLSX → 纯文本 + 元数据 | 真实文件 | ✅ 生产可用 |
| `taxonomy.py` | 文件分类器: 14 种文档类型 × 6 个阶段, 基于文件名模式匹配 | 分类规则 | ✅ 生产可用 |

### 1.2 知识库层 (5 个)

| 文件 | 功能 | 数据性质 | 状态 |
|------|------|----------|------|
| `models.py` | ORM 模型: CaseProject, CaseFile, ConsumerInsight 等 9 个表 | Schema | ✅ 生产可用 |
| `api.py` | REST API: /search, /cases, /insights, /market-intelligence 等 | 真实数据 | ✅ 生产可用 |
| `search_index.py` | 双引擎搜索: FTS5 关键词 + sentence-transformer 语义 | 真实索引 | ✅ 生产可用 |
| `ingest.py` | 入库流水线: 分类→提取→AI标签→索引→审计→存储 | 真实流程 | ✅ 生产可用 |
| `ai_tagger.py` | Claude AI 结构化标签提取 (品牌/行业/挑战/洞察) | 真实AI | ✅ 需要 API key |

### 1.3 Datacube 层 (5 个)

| 文件 | 功能 | 数据性质 | 状态 |
|------|------|----------|------|
| `datacube_models.py` | ORM: Campaign, Tags(3类), Performance, Insight, Learning | Schema | ✅ 生产可用 |
| `datacube_api.py` | REST API: CRUD, import, attribution, planning, debrief | 样本数据 | ✅ 代码完整 |
| `datacube_insight_engine.py` | 6 个 pattern detector + Claude AI 增强 | 样本数据 | ✅ 代码完整 |
| `datacube_tags.py` | 标签体系定义: WHO(30值) × WHAT(38值) × WHERE(29值) | 配置 | ✅ 生产可用 |
| `google_trends.py` | Google Trends: 搜索热度 + 相关查询 + 地域分布 (24h缓存) | 真实API | ✅ 生产可用 |

### 1.4 辅助层 (2 个)

| 文件 | 功能 | 数据性质 | 状态 |
|------|------|----------|------|
| `audit.py` | 案例完整度审计: 检查文件覆盖 → 评分 0~1.0 | 真实评估 | ✅ 生产可用 |
| `integration.py` | Module A → Module B 桥接: 项目审批后自动入库 | 真实桥接 | ✅ 生产可用 |

---

## 二、数据库表清单

### 2.1 真实数据表 (有内容)

| 表名 | 行数 | 功能 | 数据来源 |
|------|------|------|----------|
| `case_projects` | 48 | 品牌案例元数据 | Google Drive 同步 |
| `case_files` | 2,009 | 案例文件清单 (路径/类型/阶段/质量) | Drive 文件分类 |
| `consumer_insights` | 147 | 结构化消费者洞察 (中英双语) | AI 提取 + 翻译 |

**case_projects 行业分布:**
- electronics: 13, other: 10, fitness: 6, outdoor: 5, home: 4
- fashion: 3, toys: 2, baby_maternity: 2, jewelry: 1, food_beverage: 1, cleaning: 1

**case_files 阶段分布:**
- assets: 1,575 (78%), strategy: 183, planning: 100, discovery: 91, design: 54, marketing: 6

**consumer_insights 类型分布:**
- need_state: 45, purchase_driver: 33, behavior: 24, perception: 18
- barrier: 13, channel: 7, attitude: 5, target_segment: 1, pricing: 1

### 2.2 样本数据表 (Demo)

| 表名 | 行数 | 功能 | 数据来源 |
|------|------|------|----------|
| `dc_campaigns` | 16 | 营销活动 | sample_campaigns.csv + fatigue_sample.csv |
| `dc_audience_tags` | 16 | 受众标签 (WHO) | 同上 |
| `dc_content_tags` | 16 | 内容标签 (WHAT) | 同上 |
| `dc_context_tags` | 16 | 渠道标签 (WHERE) | 同上 |
| `dc_performance` | 21 | 效果指标 (时序) | 同上 |
| `dc_insights` | 22 | AI 发现的 pattern | insight_engine 生成 |
| `dc_learnings` | 6 | 累积知识 | consolidate 生成 |

**Campaigns 品牌分布:** AEKE: 11, CozyFit: 2, NEENCA: 2, CASEKOO: 1
**数据标记:** 15 条标记为 SAMPLE, 1 条为 fatigue 测试数据

### 2.3 空表 (Schema Only)

| 表名 | 行数 | 功能 | 激活条件 |
|------|------|------|----------|
| `discovery_engagements` | 0 | 品牌探索记录 | Module A 项目 approve 时触发 |
| `discovery_segments` | 0 | 消费者人群分群 | 同上 |
| `discovery_questionnaires` | 0 | 问卷设计 | 手动创建 |
| `questionnaire_responses` | 0 | 问卷回收 | 问卷部署后 |
| `cross_tabulations` | 0 | 交叉分析 | 数据分析后 |
| `market_geo_data` | 0 | 地域市场数据 | 手动录入 |
| `projects` | 0 | Module A 项目 | Module A 使用 |
| `slides` | 0 | PPT 页面 | Module A 生成 |
| `uploaded_files` | 0 | Module A 上传文件 | Module A 使用 |
| `comments` | 0 | PPT 评审意见 | Module A 使用 |

### 2.4 搜索索引 (独立文件)

| 文件 | 大小 | 内容 | 状态 |
|------|------|------|------|
| `case_search.db` | 9.9 MB | FTS5 全文索引, 357 条文档 | 真实 |
| `case_vectors.npz` | 64 KB | 语义向量, 46×384 维 | 真实 |
| `case_vectors_meta.json` | ~4 KB | 向量元数据 (doc_id, brand) | 真实 |

---

## 三、API 端点清单

### 3.1 Knowledge Base API (`/api/knowledge/`)

| 端点 | 方法 | 功能 | 数据性质 |
|------|------|------|----------|
| `/cases` | GET | 案例列表 + 行业/阶段筛选 | 真实 |
| `/cases/{id}` | GET | 案例详情 + 文件列表 | 真实 |
| `/cases/{id}/similar` | GET | 相似案例推荐 (向量相似度) | 真实 |
| `/search` | GET | 三模式搜索: fts / vector / hybrid | 真实 |
| `/stats` | GET | 总览统计 (案例数/文件数/完整度) | 真实 |
| `/dashboard` | GET | 仪表盘聚合数据 | 真实 |
| `/export` | GET | CSV/JSON 导出 | 真实 |
| `/insights` | GET | 消费者洞察列表 + 筛选 | 真实 |
| `/insights/synthesis` | GET | Claude AI 跨案例综合分析 | 真实 AI |
| `/industries` | GET | 行业概览 | 真实 |
| `/industries/{name}` | GET | 行业详情 | 真实 |
| `/industries/{name}/report` | GET | AI 行业报告 | 真实 AI |
| `/industries/compare` | GET | 多行业对比 | 真实 |
| `/market-intelligence` | GET | Google Trends + AI 营销策略 | 真实 API |
| `/market-intelligence/export` | GET | 营销报告导出 | 真实 |
| `/survey-analytics` | GET | 问卷统计概览 | 真实 (目前0条) |
| `/engagements` | GET | 探索记录列表 | 真实 (目前0条) |

### 3.2 Datacube API (`/api/datacube/`)

| 端点 | 方法 | 功能 | 数据性质 |
|------|------|------|----------|
| `/tags/options` | GET | 标签选项 (下拉框用) | 配置 |
| `/stats` | GET | 总览: campaigns/revenue/ROAS/top channels | 样本 |
| `/campaigns` | GET | 活动列表 + 筛选 | 样本 |
| `/campaigns` | POST | 创建活动 | — |
| `/campaigns/{id}` | GET | 活动详情 + tags + performance | 样本 |
| `/campaigns/{id}` | PUT | 更新活动 | — |
| `/campaigns/{id}/performance` | POST | 添加效果数据 (批量) | — |
| `/campaigns/{id}/debrief` | POST | AI 自动复盘 | 样本 + AI |
| `/import/csv` | POST | 通用 CSV 导入 (同名分组) | — |
| `/import/{platform}` | POST | 平台 CSV 导入 (Google/Meta/Amazon) | — |
| `/attribution` | GET | 归因分析: 按 audience/content/channel 聚合 | 样本 |
| `/insights/generate` | POST | 运行 6 个 pattern detector + AI | 样本 |
| `/insights` | GET | 洞察列表 | 样本 |
| `/recommendations` | GET | Scale / Stop / Test 建议 | 样本 |
| `/learnings` | GET | 累积知识列表 | 样本 |
| `/learnings/consolidate` | POST | 洞察 → 知识沉淀 | 样本 |
| `/plan` | POST | AI Campaign 规划 (基于 learnings) | 样本 + AI |
| `/unified-analysis` | GET | 研究+效果统一视图 | 真实+样本 |

---

## 四、Datacube Insight Engine 细节

### 4.1 六个 Pattern Detector

| # | 函数名 | 检测逻辑 | 当前触发 |
|---|--------|----------|----------|
| 1 | `_pattern_content_by_segment` | 每个受众最佳内容类型 (按ROAS排序) | ✅ 5条 |
| 2 | `_pattern_channel_efficiency` | 渠道效率 vs 平均值 (>20%差异) | ✅ 3条 |
| 3 | `_pattern_untested_combinations` | WHO×WHAT×WHERE 矩阵空白 | ✅ 5条 |
| 4 | `_pattern_creative_fatigue` | 同campaign engagement连续下降>15% | ✅ 1条 |
| 5 | `_pattern_geo_variance` | 同内容不同地域ROAS差异>1.5x | ✅ 1条 |
| 6 | `_pattern_temporal_trends` | 渠道ROAS月度趋势变化>20% | ✅ 2条 |

**额外:** Claude AI 增强分析 (3-5 条 `opportunity` 类型)

### 4.2 标签体系

**WHO (Audience, 30 值):**
- segment: 8 种 (self_disciplined_achiever, trend_seeker, budget_conscious, premium_buyer, loyal_customer, tech_driven_upgrader, first_time_buyer, health_focused)
- motivation: 8 种
- need_state: 4 种
- geo_market: 10 种

**WHAT (Content, 38 值):**
- theme: 12 种 (professional_review, lifestyle, tutorial_howto, user_generated, comparison, testimonial, entertainment, educational, brand_story, promotion_deal, behind_scenes, seasonal)
- format: 10 种
- message_type: 7 种
- creative_approach: 9 种

**WHERE (Context, 29 值):**
- channel: 14 种 (youtube, instagram, tiktok, facebook, google_ads, amazon_ads, reddit, twitter, pinterest, linkedin, email, blog, podcast, influencer)
- placement: 10 种
- funnel_stage: 5 种 (awareness, consideration, conversion, retention, advocacy)

---

## 五、脚本清单

| 文件 | 功能 | 运行方式 |
|------|------|----------|
| `scripts/batch_ingest_all.py` | 批量入库所有 Drive 案例 | `python -m module_b.scripts.batch_ingest_all` |
| `scripts/classify_industries.py` | AI 批量分类行业 | `python -m module_b.scripts.classify_industries` |
| `scripts/extract_insights.py` | AI 批量提取消费者洞察 | `python -m module_b.scripts.extract_insights` |
| `scripts/translate_insights.py` | Claude 批量翻译洞察为英文 | `python -m module_b.scripts.translate_insights` |

---

## 六、Connectors (广告平台导入)

| 文件 | 平台 | 解析列 | 输出 |
|------|------|--------|------|
| `connectors/google_ads.py` | Google Ads | Campaign, Impressions, Clicks, Conversions, Cost, Conv. value | Campaign + Performance |
| `connectors/meta_ads.py` | Meta (FB/IG) | Campaign name, Impressions, Link clicks, Results, Amount spent, ROAS | Campaign + Performance |
| `connectors/amazon_ads.py` | Amazon Ads | Campaign Name, Impressions, Clicks, Spend, Sales, Orders | Campaign + Performance |

---

## 七、真实 vs 演示 判定总结

### 真实数据 (生产级)

| 组件 | 证据 |
|------|------|
| 48 个品牌案例 | 从 Google Drive 同步, 含完整文件结构 |
| 2,009 个文件分类 | 每个文件有 doc_type/phase/confidence |
| 357 条全文索引 | 可搜索的文档内容 |
| 46 条语义向量 | sentence-transformer 编码 |
| 147 条消费者洞察 | AI 提取 + 中英双语 |
| Google Trends 数据 | 实时 API + 24h 缓存 |
| AI 综合分析 | Claude API 实时生成 |

### 演示数据 (需替换为真实)

| 组件 | 证据 | 替换方式 |
|------|------|----------|
| 16 个 campaign | sample_campaigns.csv 导入, 标记为 SAMPLE | 客户上传真实广告平台数据 |
| 21 条 performance | 虚构的 ROAS/Revenue 数字 | 从 Google Ads/Meta 导入 |
| 22 条 insight | 基于样本数据生成 | 真实数据后重新 generate |
| 6 条 learning | 基于样本 insight 沉淀 | 真实 insight 后重新 consolidate |

### 空壳 (Schema Ready, 无数据)

| 组件 | 激活方式 |
|------|----------|
| 品牌探索记录 | Module A 项目进入 approved 状态 |
| 消费者分群 | 同上 (从 analysis_json 提取) |
| 问卷系统 | 手动创建问卷 + 部署收集 |
| 交叉分析 | 问卷回收后运行统计 |
| 地域市场数据 | 手动录入或 API 对接 |

---

## 八、数据流水线

```
Google Drive
    │
    ▼
gdrive_watcher.py ──检测变更──▶ ingest.py
    │                              │
    │                    ┌─────────┼─────────┐
    │                    ▼         ▼         ▼
    │            taxonomy.py  extractor.py  ai_tagger.py
    │            (分类文件)   (提取文本)    (AI标签)
    │                    │         │         │
    │                    ▼         ▼         ▼
    │               case_files  case_fts   case_projects
    │               (DB表)      (FTS索引)   (DB表+评分)
    │                                │
    │                                ▼
    │                        search_index.py
    │                        (FTS5 + Vector)
    │
    ▼
api.py ──────────────────────────▶ Frontend /knowledge
                                    /insights
                                    /marketing
                                    /industries

---

CSV / Platform Export
    │
    ▼
datacube_api.py ──/import──▶ dc_campaigns + Tags + Performance
    │
    ▼
datacube_insight_engine.py ──generate──▶ dc_insights
    │
    ▼
datacube_api.py ──/consolidate──▶ dc_learnings
    │
    ▼
datacube_api.py ──/plan──▶ AI Campaign Plan (uses learnings)
    │
    ▼
Frontend /datacube/*
```

---

## 九、依赖关系

| 依赖 | 用途 | 必须? |
|------|------|-------|
| `anthropic` | Claude AI (标签/洞察/策略/规划) | 高度依赖, 无key时有fallback |
| `sentence-transformers` | 语义搜索向量编码 | 可选 (FTS仍可用) |
| `pytrends` | Google Trends 数据 | 可选 (有缓存+降级) |
| `python-pptx` | PPTX 文件解析 | 提取文件内容用 |
| `pdfplumber` | PDF 文件解析 | 提取文件内容用 |
| `python-docx` | DOCX 文件解析 | 提取文件内容用 |
| `openpyxl` | XLSX 文件解析 | 提取文件内容用 |
| `google-api-python-client` | Google Drive API | Drive 同步用 |
| `numpy` | 向量计算 (余弦相似度) | 语义搜索用 |
