# Module B 完整原子化 Roadmap

> Google Drive 权限已获取。按合同 4 个 Phase 逐步拆解到可直接执行的粒度。
> 每个任务标注：⏱预估工时 | 👤负责人建议 | 📦交付物 | ✅验收标准

---

## 合同付款里程碑对照

```
$2,000 (20%) ← 签约已付
$2,000 (20%) ← Phase 1 交付：审计报告 + Taxonomy + DB 架构设计
$4,000 (40%) ← Phase 2+3 交付：结构化数据 + Web 平台 + Discovery DB
$2,000 (20%) ← Phase 4 交付：集成 + 培训 + UAT
```

---

# Phase 1：Case Audit + Taxonomy + DB Architecture（Week 1-3）

合同交付物：**Case Audit Report + Taxonomy Documentation + Customer Discovery Database Architecture Specification (PDF)**

---

## 1.1 Google Drive 探查 ⏱2h

### 1.1.1 你现在立刻要做的

打开 Dynabridge 分享的 Google Drive，手动浏览一遍，记录：

```
观察清单：
□ 共享了几个顶层文件夹？
□ 每个文件夹对应一个客户案例吗？
□ 文件夹命名规律是什么？（客户名/日期/项目类型）
□ 每个案例里有哪些文件？（PPT/PDF/Excel/Word/图片）
□ 有没有 Cozyfit 案例？（合同说这是参考标准）
□ 问卷原始数据是什么格式？（Excel? CSV? PDF?）
□ 最终交付 PPT 长什么样？（几页？什么语言？）
□ 有没有文件放错位置或命名混乱的？
□ 预估总文件数和总大小
```

**为什么要先手动看**：你需要在写任何代码之前理解数据的真实面貌。合同假设是"3-4 个完整案例"，但现实可能是 50 个零散文件、命名不规范、有重复。

📦 输出：一段文字记录，发给 Aojie 对齐认知。

### 1.1.2 用代码拉取完整文件树 ⏱3h

```python
# module_b/scripts/explore_drive.py
# 第一个要写的脚本：打印 Google Drive 文件树

from module_b.auth import get_drive_credentials
from module_b.gdrive import GDriveClient

def main():
    creds = get_drive_credentials()
    gdrive = GDriveClient(creds)
    
    # 替换为 Dynabridge 分享的文件夹 ID
    FOLDER_ID = "替换为实际的 Google Drive 文件夹 ID"
    
    files = gdrive.list_folder(FOLDER_ID, recursive=True)
    
    # 打印文件树
    print(f"总文件数: {len(files)}")
    print(f"总大小: {sum(f['size'] for f in files) / 1024 / 1024:.1f} MB")
    print()
    
    # 按文件夹分组
    folders = {}
    for f in files:
        top_folder = f['path'].split('/')[0]
        if top_folder not in folders:
            folders[top_folder] = []
        folders[top_folder].append(f)
    
    for folder_name, folder_files in sorted(folders.items()):
        print(f"📁 {folder_name} ({len(folder_files)} files)")
        for ff in sorted(folder_files, key=lambda x: x['path']):
            size_kb = ff['size'] / 1024
            print(f"   {'📄' if ff['extension'] != 'unknown' else '❓'} "
                  f"{ff['path']} [{ff['extension']}] {size_kb:.0f}KB")
        print()
    
    # 统计
    from collections import Counter
    ext_counts = Counter(f['extension'] for f in files)
    print("文件类型分布:")
    for ext, count in ext_counts.most_common():
        print(f"  .{ext}: {count}")
    
    # 保存完整列表供后续使用
    import json
    with open("/tmp/drive_file_list.json", "w") as f:
        json.dump(files, f, ensure_ascii=False, indent=2)
    print(f"\n完整列表已保存到 /tmp/drive_file_list.json")

if __name__ == "__main__":
    main()
```

✅ 验收：脚本运行成功，输出完整文件树，保存 JSON。

---

## 1.2 批量下载 ⏱2h

### 1.2.1 下载所有案例文件到本地

```python
# module_b/scripts/download_all.py

import json
from module_b.auth import get_drive_credentials
from module_b.gdrive import GDriveClient

FOLDER_ID = "替换"
LOCAL_DIR = "/data/module_b/cases"  # Docker 容器中的持久化路径

def main():
    creds = get_drive_credentials()
    gdrive = GDriveClient(creds)
    
    downloaded = gdrive.download_case_folder(FOLDER_ID, LOCAL_DIR)
    
    # 记录下载结果
    success = [f for f in downloaded if f.get('local_path')]
    failed = [f for f in downloaded if not f.get('local_path')]
    
    print(f"\n✅ 成功: {len(success)}")
    print(f"❌ 失败: {len(failed)}")
    
    if failed:
        print("\n失败文件:")
        for f in failed:
            print(f"  {f['name']}: {f.get('error', 'unknown')}")
    
    # 保存下载清单
    with open(f"{LOCAL_DIR}/download_manifest.json", "w") as f:
        json.dump(downloaded, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
```

**⚠️ Google 原生格式处理**：
- 如果 Dynabridge 用的是 Google Slides（不是上传的 .pptx），`gdrive.py` 会自动导出为 .pptx
- 如果是 Google Sheets，自动导出为 .xlsx
- 这个逻辑已经在之前的 `GDriveClient.download_file()` 中实现

✅ 验收：所有文件下载到 `/data/module_b/cases/`，`download_manifest.json` 记录每个文件的本地路径。

---

## 1.3 Case Audit Report ⏱4h

### 1.3.1 自动审计脚本

```python
# module_b/scripts/generate_audit.py

from module_b.audit import generate_audit_report
import json

def main():
    with open("/data/module_b/cases/download_manifest.json") as f:
        files = json.load(f)
    
    audit = generate_audit_report(files)
    
    # 保存 JSON
    with open("/data/module_b/audit_report.json", "w") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    s = audit['summary']
    print(f"案例总数: {s['case_count']}")
    print(f"文件总数: {s['total_files']}")
    print(f"总大小: {s['total_size_mb']} MB")
    print(f"文件类型: {s['file_types']}")
    
    print("\n各案例完整度:")
    for case, comp in audit['case_completeness'].items():
        status = "✅" if comp['complete'] else "⚠️"
        print(f"  {status} {case}: {comp['file_count']} files, "
              f"PPT={'✓' if comp['has_presentation'] else '✗'}, "
              f"问卷={'✓' if comp['has_questionnaire_data'] else '✗'}")
    
    if audit['issues']:
        print(f"\n发现 {len(audit['issues'])} 个问题:")
        for issue in audit['issues']:
            print(f"  {issue}")

if __name__ == "__main__":
    main()
```

### 1.3.2 人工审计补充 ⏱2h

自动脚本只能做结构化审计。你还需要**手动打开几个关键文件**看内容：

```
人工审计清单：
□ 打开每个案例的最终交付 PPT，记录：
  - 页数
  - 语言（中文/英文/双语）
  - 包含哪些章节（discovery/naming/strategy？）
  - 图表类型（柱状图/饼图/表格/矩阵）
  - 是否有消费者分群（几个群体？）
  - 是否有竞品分析（几个竞品？）
  
□ 打开问卷数据文件，记录：
  - 格式（Excel 表头是什么？几个 sheet？）
  - 样本量
  - 问题数量
  - 是否有交叉分析结果
  
□ 记录每个案例的行业/品牌名/项目类型
  （这些信息有些在文件名中，有些需要打开文件才能看到）
```

📦 输出：`audit_report.json`（自动）+ 人工审计笔记（手写/文档）

### 1.3.3 审计报告 PDF 生成 ⏱3h

合同交付物要求 PDF 格式。把审计结果整合成一个正式文档：

```python
# module_b/scripts/build_audit_pdf.py

"""
用 python-pptx 生成审计报告 PPT → LibreOffice 转 PDF
（因为 Dynabridge 习惯 PPT 格式的报告）

或者用 markdown → pandoc → PDF（更简单）
"""

def generate_audit_pdf(audit_data: dict, output_path: str):
    """
    方案 A：Markdown → PDF（推荐，更快）
    """
    md_content = f"""# Dynabridge Module B — Case Audit Report

**Generated:** {audit_data['generated_at']}

## Summary

| Metric | Value |
|--------|-------|
| Total Cases | {audit_data['summary']['case_count']} |
| Total Files | {audit_data['summary']['total_files']} |
| Total Size | {audit_data['summary']['total_size_mb']} MB |

## File Type Distribution

| Extension | Count |
|-----------|-------|
"""
    for ext, count in sorted(audit_data['summary']['file_types'].items()):
        md_content += f"| .{ext} | {count} |\n"
    
    md_content += "\n## Case Completeness\n\n"
    for case, comp in audit_data['case_completeness'].items():
        status = "✅ Complete" if comp['complete'] else "⚠️ Incomplete"
        md_content += f"### {case} — {status}\n\n"
        md_content += f"- Files: {comp['file_count']}\n"
        md_content += f"- Has Presentation: {'Yes' if comp['has_presentation'] else 'No'}\n"
        md_content += f"- Has Questionnaire Data: {'Yes' if comp['has_questionnaire_data'] else 'No'}\n"
        md_content += f"- File Types: {comp['types']}\n\n"
    
    if audit_data['issues']:
        md_content += "## Issues\n\n"
        for issue in audit_data['issues']:
            md_content += f"- {issue}\n"
    
    # 保存 markdown
    md_path = output_path.replace('.pdf', '.md')
    with open(md_path, 'w') as f:
        f.write(md_content)
    
    # 转 PDF
    import subprocess
    subprocess.run([
        "pandoc", md_path, "-o", output_path,
        "--pdf-engine=xelatex",  # 支持中文
        "-V", "geometry:margin=1in",
        "-V", "mainfont:Noto Sans CJK SC",  # 中文字体
    ], check=True)
    
    return output_path
```

✅ 验收：生成 `Case_Audit_Report.pdf`，包含文件统计、类型分布、完整度评估、问题清单。

---

## 1.4 Taxonomy Design ⏱6h

### 1.4.1 初稿：基于审计结果设计分类体系

**这一步需要和 Dynabridge 的品牌专家协作**（合同要求："Collaborate with Client's brand expert"）。

```python
# module_b/taxonomy.py

"""
Taxonomy = 案例知识库的分类和标签体系。
决定了用户能按什么维度搜索和发现案例。

分类维度来自三个来源：
1. 合同要求的查询维度："industry, challenge type, segment profile, growth metric"
2. AEKE 报告中观察到的实际案例结构
3. Dynabridge 品牌专家的领域知识
"""

TAXONOMY_SCHEMA = {
    "version": "1.0",
    
    # ===== 维度 1: 行业 =====
    "industry": {
        "description": "客户品牌所属行业",
        "type": "single_select",
        "values": [
            "home_fitness",       # 家庭健身（如 AEKE）
            "beauty_skincare",    # 美妆护肤
            "food_beverage",      # 食品饮料
            "consumer_electronics", # 消费电子
            "fashion_apparel",    # 时尚服饰
            "home_appliances",    # 家电
            "automotive",         # 汽车
            "healthcare",         # 健康医疗
            "baby_maternity",     # 母婴
            "pet_care",           # 宠物
            "outdoor_sports",     # 户外运动
            "home_furnishing",    # 家居
            "other",
        ],
        "note": "如果 Dynabridge 品牌专家提出新行业，直接加入列表"
    },
    
    # ===== 维度 2: 项目类型 =====
    "project_type": {
        "description": "Dynabridge 为客户做的项目类型",
        "type": "multi_select",
        "values": [
            "brand_discovery",    # 品牌探索（本合同 Module A 做的就是这个）
            "brand_naming",       # 品牌命名
            "brand_strategy",     # 品牌战略
            "brand_design",       # 品牌设计（VI/logo）
            "market_entry",       # 市场进入策略
            "full_rebrand",       # 全面品牌重塑
        ],
    },
    
    # ===== 维度 3: 核心挑战 =====
    "challenge_type": {
        "description": "客户面临的核心品牌挑战",
        "type": "multi_select",
        "values": [
            "low_brand_awareness",    # 品牌认知度低
            "generic_positioning",    # 定位模糊/通用
            "china_brand_perception", # 中国品牌出海刻板印象
            "price_war_escape",       # 脱离价格战
            "naming_conflict",        # 命名冲突/商标问题
            "target_unclear",         # 目标受众不清晰
            "competitive_pressure",   # 竞争压力大
            "category_creation",      # 开创新品类
            "premium_upgrade",        # 从平价升级高端
        ],
    },
    
    # ===== 维度 4: 研究方法 =====
    "research_methods": {
        "description": "项目中使用的研究方法",
        "type": "multi_select",
        "values": [
            "quantitative_survey",   # 定量问卷（如 AEKE 的 603 人调查）
            "competitive_analysis",  # 竞品分析
            "review_mining",         # 评论挖掘
            "social_listening",      # 社交媒体分析
            "consumer_interviews",   # 消费者访谈
            "focus_group",           # 焦点小组
            "google_trends",         # 搜索趋势分析
            "secondary_research",    # 二手研究/行业报告
        ],
    },
    
    # ===== 维度 5: 目标市场 =====
    "target_market": {
        "description": "品牌的目标市场",
        "type": "multi_select",
        "values": ["us", "europe", "japan", "southeast_asia", "global", "china_domestic"],
    },
    
    # ===== 维度 6: 品牌来源 =====
    "brand_origin": {
        "description": "品牌的来源国",
        "type": "single_select",
        "values": ["china", "us", "europe", "japan", "korea", "other"],
        "note": "Dynabridge 的客户主要是中国企业出海，大部分会是 china"
    },
    
    # ===== 维度 7: 关键产出类型 =====
    "output_types": {
        "description": "项目产出了哪些类型的交付物",
        "type": "multi_select",
        "values": [
            "consumer_segments",     # 消费者分群
            "brand_positioning",     # 品牌定位建议
            "naming_candidates",     # 命名候选
            "competitive_map",       # 竞争地图
            "evidence_plan",         # 证据收集计划
            "target_recommendation", # 目标受众推荐
        ],
    },
    
    # ===== 维度 8: 自由标签 =====
    "free_tags": {
        "description": "AI 自动生成的自由标签，用于语义搜索",
        "type": "free_text_list",
        "examples": ["DTC", "smart-home", "premium-pricing", "gen-z-target",
                     "subscription-model", "B2C", "cross-border-ecommerce"],
    },
}
```

### 1.4.2 与 Dynabridge 品牌专家评审 ⏱2h（会议）

准备一页纸的 Taxonomy 概览，和 Dynabridge 的品牌专家开一次 30-60 分钟的线上会议：

```markdown
## 会议议程

1. 展示 8 个分类维度 (5 min)
2. 逐一确认维度和可选值是否覆盖 Dynabridge 的实际需要 (15 min)
   - 有没有缺少的维度？
   - 有没有值需要增加/删除/合并？
3. 讨论案例优先级 (5 min)
   - 哪个案例最完整、质量最高？（作为我们的参考标准）
   - 有没有不完整的案例需要补充材料？
4. 确认搜索场景 (5 min)
   - Dynabridge 团队平时怎么"复用"历史案例？
   - 最常见的搜索需求是什么？（"找一个健身行业的分群案例"？）
```

📦 输出：确认后的 `taxonomy_v1.json` + 会议纪要

### 1.4.3 Taxonomy 文档 PDF ⏱2h

```python
# module_b/scripts/build_taxonomy_pdf.py

def generate_taxonomy_doc(taxonomy: dict, output_path: str):
    """
    生成 Taxonomy Documentation PDF。
    
    内容：
    1. 分类体系概述
    2. 每个维度的定义、可选值、使用说明
    3. 标签使用示例（以 AEKE/Cozyfit 为例）
    4. 新案例入库的标签流程
    """
    md = """# Dynabridge Knowledge Base — Taxonomy Documentation

## Overview

This document defines the classification system for Dynabridge's case knowledge base.
All historical and future brand discovery cases will be tagged using these dimensions.

## Taxonomy Dimensions

"""
    for dim_name, dim_def in taxonomy.items():
        if dim_name == "version":
            continue
        md += f"### {dim_name.replace('_', ' ').title()}\n\n"
        md += f"**Description:** {dim_def['description']}\n\n"
        md += f"**Selection type:** {dim_def['type']}\n\n"
        if 'values' in dim_def:
            md += "**Allowed values:**\n\n"
            for v in dim_def['values']:
                md += f"- `{v}`\n"
        if 'note' in dim_def:
            md += f"\n*Note: {dim_def['note']}*\n"
        md += "\n---\n\n"
    
    # 写 markdown → 转 PDF
    md_path = output_path.replace('.pdf', '.md')
    with open(md_path, 'w') as f:
        f.write(md)
    
    import subprocess
    subprocess.run(["pandoc", md_path, "-o", output_path,
                    "--pdf-engine=xelatex", "-V", "geometry:margin=1in"], check=True)
```

---

## 1.5 Customer Discovery Database Architecture ⏱8h

### 1.5.1 数据模型设计

合同要求设计三个数据模型。逐个实现：

```python
# module_b/models.py

"""
Customer Discovery Database 数据模型。
共享 Module A 的 SQLAlchemy Base 和 engine。
"""

from sqlalchemy import (Column, String, Integer, Float, DateTime, 
                        JSON, ForeignKey, Text, Boolean)
from sqlalchemy.orm import relationship
from models import Base  # 共享 Module A 的 Base
import uuid
from datetime import datetime

def gen_id(): 
    return str(uuid.uuid4())[:8]

# ============================================================
# 1. INPUT DATA MODEL（合同要求）
# "client briefs, raw data sources, questionnaire designs, competitor lists"
# ============================================================

class CaseRecord(Base):
    """案例知识库主记录 — 每个历史案例一条"""
    __tablename__ = "case_records"
    
    id = Column(String, primary_key=True, default=gen_id)
    case_name = Column(String, nullable=False)
    brand_name = Column(String)
    brand_name_cn = Column(String)
    
    # Taxonomy 标签（与 taxonomy.py 对应）
    industry = Column(String)
    project_type = Column(String)          # JSON array
    challenge_type = Column(String)         # JSON array
    target_market = Column(String)          # JSON array
    brand_origin = Column(String)
    research_methods = Column(String)       # JSON array
    free_tags = Column(String)              # JSON array
    
    # 内容摘要
    key_insights = Column(JSON)             # AI 提取的关键洞察
    segments_summary = Column(JSON)         # 消费者分群摘要
    positioning_summary = Column(Text)      # 品牌定位摘要
    
    # 来源
    gdrive_folder_id = Column(String)       # Google Drive 文件夹 ID
    gdrive_folder_url = Column(String)      # 可点击的 Drive 链接
    
    # 元数据
    engagement_date = Column(String)        # "2025-06"
    created_at = Column(DateTime, default=datetime.utcnow)
    taxonomy_json = Column(JSON)            # 完整 taxonomy（Agent 产出）
    
    # 关联
    files = relationship("CaseFile", back_populates="case")
    tags = relationship("CaseTag", back_populates="case")


class CaseFile(Base):
    """案例文件记录 — 每个文件一条"""
    __tablename__ = "case_files"
    
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("case_records.id"))
    
    # 文件信息
    filename = Column(String)
    file_type = Column(String)              # pptx / pdf / docx / xlsx / image
    file_size = Column(Integer)
    gdrive_file_id = Column(String)         # 原始 Google Drive 文件 ID
    local_path = Column(String)             # 下载后的本地路径
    
    # AI 提取的内容
    extracted_content = Column(JSON)        # Managed Agent 提取的结构化 JSON
    processing_method = Column(String)      # Agent 用了什么方法
    language = Column(String)               # en / cn / en+cn
    importance = Column(String)             # high / medium / low
    
    # 元数据
    slide_count = Column(Integer)           # PPT 专用
    page_count = Column(Integer)            # PDF 专用
    row_count = Column(Integer)             # Excel 专用
    
    case = relationship("CaseRecord", back_populates="files")


class CaseTag(Base):
    """案例标签索引（用于快速筛选）"""
    __tablename__ = "case_tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, ForeignKey("case_records.id"))
    dimension = Column(String)              # "industry" / "challenge_type" / "free_tag"
    value = Column(String)
    
    case = relationship("CaseRecord", back_populates="tags")


# ============================================================
# 2. OUTPUT DATA MODEL（合同要求）
# "generated reports, analysis artifacts, segmentation results, evidence matrices"
# ============================================================

class DiscoveryEngagement(Base):
    """
    Customer Discovery Database 主记录。
    每次 Module A 的品牌发现项目完成后，自动创建一条。
    """
    __tablename__ = "discovery_engagements"
    
    id = Column(String, primary_key=True, default=gen_id)
    
    # 关联 Module A 的 project
    module_a_project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    
    # 基本信息
    brand_name = Column(String)
    industry = Column(String)
    challenge_type = Column(String)
    target_market = Column(String)
    engagement_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")  # active / completed
    
    # 产出
    reports = relationship("DiscoveryReport", back_populates="engagement")
    segments = relationship("DiscoverySegment", back_populates="engagement")
    questionnaires = relationship("DiscoveryQuestionnaire", back_populates="engagement")


class DiscoveryReport(Base):
    """Module A 生成的报告记录"""
    __tablename__ = "discovery_reports"
    
    id = Column(String, primary_key=True, default=gen_id)
    engagement_id = Column(String, ForeignKey("discovery_engagements.id"))
    
    report_type = Column(String)            # brand_reality / market_structure / evidence / synthesis
    phase = Column(String)                  # phase1 / phase2 / phase3 / phase4
    pptx_path = Column(String)
    pdf_path = Column(String)
    analysis_json = Column(JSON)            # 完整分析 JSON（可搜索）
    generated_at = Column(DateTime)
    accepted_at = Column(DateTime, nullable=True)
    
    engagement = relationship("DiscoveryEngagement", back_populates="reports")


class DiscoverySegment(Base):
    """消费者分群结果"""
    __tablename__ = "discovery_segments"
    
    id = Column(String, primary_key=True, default=gen_id)
    engagement_id = Column(String, ForeignKey("discovery_engagements.id"))
    
    segment_name_en = Column(String)
    segment_name_cn = Column(String)
    size_percentage = Column(Float)
    profile_json = Column(JSON)             # 完整画像
    is_primary_target = Column(Boolean, default=False)
    
    engagement = relationship("DiscoveryEngagement", back_populates="segments")


# ============================================================
# 3. QUESTIONNAIRE DATA MODEL（合同要求）
# "question definitions, response sets, cross-tabulation structures, statistical summaries"
# ============================================================

class DiscoveryQuestionnaire(Base):
    """问卷定义"""
    __tablename__ = "discovery_questionnaires"
    
    id = Column(String, primary_key=True, default=gen_id)
    engagement_id = Column(String, ForeignKey("discovery_engagements.id"))
    
    title_en = Column(String)
    title_cn = Column(String)
    variant = Column(String)                # "A" or "B"
    question_count = Column(Integer)
    questions_json = Column(JSON)           # 完整题目结构
    
    # 问卷平台
    platform = Column(String)              # surveymonkey / typeform
    platform_survey_id = Column(String)
    collect_url = Column(String)
    
    # 统计
    response_count = Column(Integer, default=0)
    avg_completion_seconds = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    engagement = relationship("DiscoveryEngagement", back_populates="questionnaires")
    responses = relationship("QuestionnaireResponse", back_populates="questionnaire")


class QuestionnaireResponse(Base):
    """问卷回答"""
    __tablename__ = "questionnaire_responses"
    
    id = Column(String, primary_key=True, default=gen_id)
    questionnaire_id = Column(String, ForeignKey("discovery_questionnaires.id"))
    
    respondent_id = Column(String)          # 匿名化
    answers_json = Column(JSON)
    demographics_json = Column(JSON)
    submitted_at = Column(DateTime)
    completion_seconds = Column(Integer)
    
    questionnaire = relationship("DiscoveryQuestionnaire", back_populates="responses")


class CrossTabulation(Base):
    """交叉分析结果"""
    __tablename__ = "cross_tabulations"
    
    id = Column(String, primary_key=True, default=gen_id)
    questionnaire_id = Column(String, ForeignKey("discovery_questionnaires.id"))
    
    dimension_a = Column(String)
    dimension_b = Column(String)
    result_json = Column(JSON)
    statistical_significance = Column(Float)  # p-value
```

### 1.5.2 Architecture Specification PDF ⏱3h

合同要求的交付物。内容应包含：

```markdown
# Customer Discovery Database — Architecture Specification

## 1. System Overview
- 目的和范围
- 与 Module A 的关系
- 数据流图

## 2. Data Models
- 2.1 Input Data Model（ER 图 + 字段说明）
- 2.2 Output Data Model（ER 图 + 字段说明）
- 2.3 Questionnaire Data Model（ER 图 + 字段说明）

## 3. Metadata & Indexing Schema
- Taxonomy 维度映射
- 全文搜索索引设计
- 向量嵌入方案

## 4. Ingestion Pipeline Architecture
- Module A → Module B 自动入库流程
- Google Drive 新文件检测流程
- 数据清洗和验证规则

## 5. Query API Design
- 结构化筛选 API
- 语义搜索 API
- 跨案例分析 API

## 6. Technology Stack
- SQLAlchemy + SQLite（MVP）→ PostgreSQL（生产）
- sentence-transformers (all-MiniLM-L6-v2)
- Claude Managed Agents（文件处理）
```

生成方式：手写 Markdown → pandoc → PDF。或者用 Mermaid 画 ER 图嵌入。

### 1.5.3 创建数据库表 ⏱1h

```python
# module_b/scripts/init_db.py

from models import engine, Base
# 导入所有 Module B 模型，确保它们被注册到 Base
from module_b.models import (CaseRecord, CaseFile, CaseTag,
                             DiscoveryEngagement, DiscoveryReport,
                             DiscoverySegment, DiscoveryQuestionnaire,
                             QuestionnaireResponse, CrossTabulation)

def main():
    """创建所有 Module B 表（不影响 Module A 的现有表）"""
    Base.metadata.create_all(engine)
    print("✅ Module B 数据库表创建完成")
    
    # 验证
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    module_b_tables = [t for t in tables if t in [
        'case_records', 'case_files', 'case_tags',
        'discovery_engagements', 'discovery_reports', 'discovery_segments',
        'discovery_questionnaires', 'questionnaire_responses', 'cross_tabulations'
    ]]
    print(f"Module B 表: {module_b_tables}")
    
    # Module A 的表应该还在
    module_a_tables = [t for t in tables if t in ['projects', 'slides', 'comments', 'uploaded_files']]
    print(f"Module A 表 (不受影响): {module_a_tables}")

if __name__ == "__main__":
    main()
```

✅ Phase 1 验收：三个 PDF 交付物准备好 → 提交给 Dynabridge → 进入 14 天评审。

---

# Phase 2：Data Extraction + DB Core Build（Week 3-6）

---

## 2.1 案例文件智能提取（Managed Agent）⏱8h

**详细实现已在 Module_B_Case_Processing_Roadmap.md 的 Step 3 中给出。**

这里列出执行顺序：

```
任务 2.1.1: 创建 Case Processor Agent                      ⏱1h
  → 运行 create_case_processor_agent()
  → 记录 agent_id 和 env_id 到 .env

任务 2.1.2: 用第一个案例测试                                ⏱3h
  → 选最小/最简单的案例
  → 运行 process_case_files()
  → 检查输出的 JSON 质量
  → 根据结果调整 System Prompt

任务 2.1.3: 处理剩余案例                                   ⏱3h
  → 逐个案例运行（不要并行，观察每个的问题）
  → 记录每个案例的处理时间和 token 消耗

任务 2.1.4: 人工质检                                       ⏱1h
  → 随机抽 5 个文件的输出 JSON，对照原文件验证
  → 检查：PPT 幻灯片数量对吗？表格数据完整吗？中文正确吗？
```

## 2.2 Taxonomy 自动标签（Managed Agent）⏱4h

```
任务 2.2.1: 运行 Taxonomy Agent                            ⏱2h
  → 对每个案例的 summary.json 运行 tag_case_with_taxonomy()
  → 检查标签是否使用规范值

任务 2.2.2: 人工校正                                       ⏱2h
  → 对照实际案例内容，修正 AI 标签的错误
  → 特别检查：行业分类、消费者分群名称、关键洞察
  → 这一步非常重要——错误的标签会导致搜索结果不准确
```

## 2.3 全文搜索索引 + 向量嵌入 ⏱4h

```python
# module_b/search_index.py

"""
两种搜索能力：
1. 全文搜索（关键词精确匹配）→ SQLite FTS5
2. 语义搜索（理解搜索意图）→ sentence-transformers
"""

import sqlite3

class FullTextIndex:
    """
    SQLite FTS5 全文搜索。
    比自己实现倒排索引简单 100 倍，性能足够。
    """
    
    def __init__(self, db_path: str = "module_b.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_fts_table()
    
    def _create_fts_table(self):
        """创建 FTS5 虚拟表"""
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS case_fts USING fts5(
                case_id,
                brand_name,
                industry,
                key_insights,
                segments,
                full_text,
                tokenize='unicode61'
            )
        """)
        self.conn.commit()
    
    def index_case(self, case_id: str, brand_name: str, industry: str,
                   key_insights: str, segments: str, full_text: str):
        """添加一个案例到全文索引"""
        self.conn.execute(
            "INSERT INTO case_fts VALUES (?, ?, ?, ?, ?, ?)",
            (case_id, brand_name, industry, key_insights, segments, full_text)
        )
        self.conn.commit()
    
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """全文搜索"""
        cursor = self.conn.execute(
            "SELECT case_id, brand_name, snippet(case_fts, 5, '<b>', '</b>', '...', 20) "
            "FROM case_fts WHERE case_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit)
        )
        return [
            {"case_id": row[0], "brand_name": row[1], "snippet": row[2]}
            for row in cursor.fetchall()
        ]
```

## 2.4 入库 + 种子数据 ⏱4h

```
任务 2.4.1: 将所有案例数据写入数据库                        ⏱2h
  → 运行 ingest_case() for each case
  → 验证：SELECT COUNT(*) FROM case_records → 应该等于案例数

任务 2.4.2: 建立搜索索引                                   ⏱1h
  → 全文索引：index_case() for each case
  → 向量索引：vector_index.add_case() for each case

任务 2.4.3: 从历史案例中提取 Discovery 数据                  ⏱1h
  → 如果历史案例中有问卷数据 → 解析入 questionnaires 表
  → 如果有消费者分群 → 解析入 segments 表
  → 这就是合同说的 "Seed the database with discovery data"
```

## 2.5 跨案例查询 API ⏱6h

```python
# module_b/api.py — 加入 FastAPI main.py

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/knowledge", tags=["Module B"])

@router.get("/cases")
def list_cases(
    industry: Optional[str] = None,
    challenge_type: Optional[str] = None,
    project_type: Optional[str] = None,
    target_market: Optional[str] = None,
    limit: int = 20,
):
    """合同要求：Multi-criteria filtered search"""
    query = db.query(CaseRecord)
    if industry:
        query = query.filter(CaseRecord.industry == industry)
    if challenge_type:
        query = query.join(CaseTag).filter(
            CaseTag.dimension == "challenge_type",
            CaseTag.value == challenge_type
        )
    # ... 其他筛选
    return query.limit(limit).all()

@router.get("/cases/{case_id}")
def get_case(case_id: str):
    """案例详情页，含所有文件和标签"""
    case = db.query(CaseRecord).get(case_id)
    files = db.query(CaseFile).filter(CaseFile.case_id == case_id).all()
    return {"case": case, "files": files}

@router.get("/search")
def semantic_search(q: str = Query(..., description="搜索关键词或自然语言问题")):
    """合同要求：AI semantic search"""
    # 先试全文搜索
    fts_results = full_text_index.search(q, limit=5)
    # 再试语义搜索
    vector_results = vector_index.search(q, top_k=5)
    # 合并去重
    return merge_results(fts_results, vector_results)

@router.get("/discovery/search")
def discovery_search(
    industry: Optional[str] = None,
    segment_keyword: Optional[str] = None,
    challenge: Optional[str] = None,
):
    """合同要求：cross-case query API (filter by industry, segment, challenge type, growth metric)"""
    pass

# 在 main.py 中注册
# app.include_router(router)
```

✅ Phase 2 验收：
- 所有案例文件被解析为结构化 JSON
- 数据库中有案例记录 + 文件记录 + 标签
- 全文搜索和语义搜索都能返回相关结果
- API 文档自动生成（FastAPI /docs）

---

# Phase 3：Knowledge Platform + Discovery Dashboard（Week 5-9）

---

## 3.1 知识平台 Web 界面 ⏱15h

### 前端路由规划

```
/knowledge                    → 案例列表页（搜索 + 筛选）
/knowledge/case/{id}          → 案例详情页
/knowledge/search?q=xxx       → 搜索结果页
/discovery-dashboard          → Discovery Dashboard
/discovery-dashboard/patterns → 跨案例模式
/discovery-dashboard/surveys  → 问卷分析
```

### 3.1.1 案例列表页 ⏱5h

```tsx
// frontend/src/app/knowledge/page.tsx

"use client";
import { useState, useEffect } from "react";

export default function KnowledgePage() {
    const [cases, setCases] = useState([]);
    const [filters, setFilters] = useState({
        industry: "", challenge_type: "", search: ""
    });

    useEffect(() => {
        const params = new URLSearchParams();
        if (filters.industry) params.set("industry", filters.industry);
        if (filters.challenge_type) params.set("challenge_type", filters.challenge_type);
        
        fetch(`/api/knowledge/cases?${params}`)
            .then(r => r.json())
            .then(setCases);
    }, [filters]);

    return (
        <div className="flex gap-6 p-6">
            {/* 左侧筛选面板 */}
            <div className="w-64 shrink-0">
                <h3 className="font-bold mb-4">Filters</h3>
                
                <div className="mb-4">
                    <label className="text-sm text-gray-500">Industry</label>
                    <select
                        className="w-full mt-1 border rounded p-2"
                        value={filters.industry}
                        onChange={e => setFilters({...filters, industry: e.target.value})}
                    >
                        <option value="">All Industries</option>
                        <option value="home_fitness">Home Fitness</option>
                        <option value="beauty_skincare">Beauty & Skincare</option>
                        {/* ... 从 taxonomy 动态生成 */}
                    </select>
                </div>
                
                {/* 类似的筛选器：challenge_type, target_market, research_methods */}
            </div>

            {/* 右侧案例列表 */}
            <div className="flex-1">
                {/* 搜索框 */}
                <input
                    className="w-full border rounded-lg p-3 mb-6"
                    placeholder="搜索案例... (支持中英文语义搜索)"
                    value={filters.search}
                    onChange={e => setFilters({...filters, search: e.target.value})}
                />

                {/* 案例卡片列表 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {cases.map(c => (
                        <CaseCard key={c.id} case_={c} />
                    ))}
                </div>
            </div>
        </div>
    );
}

function CaseCard({ case_ }) {
    return (
        <a href={`/knowledge/case/${case_.id}`}
           className="block border rounded-lg p-4 hover:shadow-lg transition">
            <div className="flex justify-between items-start">
                <h3 className="font-bold text-lg">{case_.brand_name}</h3>
                <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                    {case_.industry}
                </span>
            </div>
            <p className="text-sm text-gray-500 mt-1">{case_.brand_name_cn}</p>
            <div className="flex gap-2 mt-3 flex-wrap">
                {JSON.parse(case_.free_tags || '[]').slice(0, 4).map(tag => (
                    <span key={tag} className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                        {tag}
                    </span>
                ))}
            </div>
            <div className="text-xs text-gray-400 mt-3">
                {case_.engagement_date} · {case_.files?.length || 0} files
            </div>
        </a>
    );
}
```

### 3.1.2 案例详情页 ⏱5h

```tsx
// frontend/src/app/knowledge/case/[id]/page.tsx

// 包含：
// - 案例基本信息 + taxonomy 标签
// - 文件列表（可点击 → 打开 Google Drive 原文件）
// - AI 提取的关键洞察
// - 消费者分群卡片
// - "Similar Cases" 推荐（合同要求）
```

### 3.1.3 Similar Cases 推荐引擎 ⏱3h

```python
@router.get("/cases/{case_id}/similar")
def get_similar_cases(case_id: str, limit: int = 3):
    """
    合同要求：AI-powered "Similar Cases" recommendation engine
    
    算法：用当前案例的 taxonomy 标签 + 关键洞察文本，
    在向量索引中搜索最相似的其他案例。
    """
    case = db.query(CaseRecord).get(case_id)
    
    # 用案例的关键信息组成查询
    query_text = f"{case.brand_name} {case.industry} {' '.join(json.loads(case.free_tags or '[]'))}"
    
    results = vector_index.search(query_text, top_k=limit + 1)
    
    # 排除自己
    return [r for r in results if r["case_id"] != case_id][:limit]
```

### 3.1.4 AI 语义搜索 UI ⏱2h

搜索框支持自然语言：
- "找一个健身行业的消费者分群案例" → 返回 AEKE
- "price war" → 返回标签含 price_war_escape 的案例
- "品牌认知度低怎么办" → 语义匹配相关案例

---

## 3.2 Discovery Dashboard ⏱12h

合同要求四个子功能：

### 3.2.1 跨案例模式可视化 ⏱4h

```python
@router.get("/discovery/patterns")
def cross_case_patterns():
    """
    recurring consumer segments, common need-states, frequently validated hypotheses
    """
    # 提取所有案例的消费者分群
    all_segments = db.query(DiscoverySegment).all()
    
    # 用 Claude 识别跨案例模式
    segment_data = [{"name": s.segment_name_en, "traits": s.profile_json} for s in all_segments]
    
    patterns = claude_analyze(
        prompt="分析以下来自不同品牌项目的消费者分群，识别反复出现的分群模式...",
        data=segment_data
    )
    
    return patterns
```

前端用 Recharts 画：
- 各行业中反复出现的消费者类型（气泡图）
- 最常见的挑战类型分布（饼图）
- 跨案例的共性洞察（词云或列表）

### 3.2.2 问卷分析仪表板 ⏱3h

```python
@router.get("/discovery/survey-analytics")
def survey_analytics():
    """
    response rate trends, cross-case question effectiveness, benchmarkable metrics
    """
    questionnaires = db.query(DiscoveryQuestionnaire).all()
    
    return {
        "total_surveys": len(questionnaires),
        "total_responses": sum(q.response_count for q in questionnaires),
        "avg_completion_minutes": round(
            sum(q.avg_completion_seconds or 0 for q in questionnaires) 
            / max(len(questionnaires), 1) / 60, 1
        ),
        "by_platform": Counter(q.platform for q in questionnaires),
        "response_trend": [
            {"date": q.created_at.strftime("%Y-%m"), "responses": q.response_count}
            for q in sorted(questionnaires, key=lambda x: x.created_at)
        ],
    }
```

### 3.2.3 策略洞察探索器 ⏱3h

一个搜索界面，允许 Dynabridge 团队输入问题（如"健身行业的消费者最看重什么？"），系统从所有历史数据中检索答案。

### 3.2.4 增长分析数据导出 ⏱2h

```python
@router.get("/discovery/export")
def export_data(
    format: str = "csv",  # csv / json / xlsx
    engagement_ids: list[str] = Query(default=[]),
):
    """
    合同要求：exportable data views designed for downstream 
    performance marketing and paid-growth workflows
    """
    # 导出选定案例的：分群数据、问卷响应、关键指标
    pass
```

---

# Phase 4：Integration + UAT + Training（Week 10-12）

---

## 4.1 Google Drive 自动检测新文件 ⏱4h

```
任务 4.1.1: 实现 GDriveWatcher                              ⏱2h
  → 每 5 分钟轮询 Google Drive Changes API
  → 检测到新文件 → 触发下载 + Agent 处理 + 入库

任务 4.1.2: 注册为后台任务                                   ⏱2h
  → 用 Python 的 APScheduler 或 Celery Beat
  → 在 Docker 容器启动时自动运行
  → 日志记录每次检测结果
```

## 4.2 Module A → B 自动入库 ⏱4h

```
任务 4.2.1: 实现 ingest_from_module_a()                     ⏱2h
  → 当 Module A 的 project.status 变为 approved 时触发
  → 从 project.analysis_json 提取所有数据
  → 写入 DiscoveryEngagement + Reports + Segments

任务 4.2.2: 在 main.py 中注册触发器                         ⏱1h
  → PATCH /api/projects/{id}/approve 成功后调用

任务 4.2.3: 端到端测试                                      ⏱1h
  → 用 Module A 跑一个完整项目
  → 确认 approved 后数据出现在 Discovery Dashboard
```

## 4.3 UAT ⏱6h

```
UAT 测试用例：

知识平台：
  [ ] 打开案例列表 → 所有案例显示正确
  [ ] 按行业筛选 → 结果正确
  [ ] 搜索 "品牌认知" → 返回相关案例
  [ ] 搜索 "consumer segmentation" → 返回相关案例
  [ ] 打开案例详情 → 文件列表完整
  [ ] 点击文件 → 能打开 Google Drive 原文件
  [ ] Similar Cases → 推荐结果合理
  
Discovery Dashboard：
  [ ] 跨案例模式 → 图表显示正确
  [ ] 问卷分析 → 统计数据正确
  [ ] 策略探索器 → 搜索返回有用结果
  [ ] 数据导出 → CSV/JSON 下载正确
  
集成：
  [ ] Module A 项目 approve 后 → Discovery DB 有数据
  [ ] Google Drive 新增文件 → 自动检测 + 入库
  
性能：
  [ ] 搜索响应 < 2 秒
  [ ] 案例详情页加载 < 1 秒
  [ ] Dashboard 图表渲染 < 3 秒
```

## 4.4 培训材料 ⏱6h

```
任务 4.4.1: 用户手册                                        ⏱3h
  → Markdown 编写，pandoc 导出 PDF
  → 中英双语
  → 内容：登录、搜索、浏览案例、Dashboard 使用

任务 4.4.2: 培训视频录制                                    ⏱2h
  → 工具：OBS Studio（免费）或 Loom
  → 时长：60-90 分钟
  → 大纲：
    0:00 系统概览
    0:10 案例知识库演示
    0:25 语义搜索演示
    0:35 Discovery Dashboard 演示
    0:50 Module A → B 集成演示
    1:00 常见操作 Q&A

任务 4.4.3: 集成文档                                        ⏱1h
  → API 文档：FastAPI 自动生成 /docs
  → 系统架构图：Mermaid 绘制
  → 数据库 ER 图：从 SQLAlchemy models 自动生成
```

---

# 总计工时估算

| Phase | 任务 | 工时 |
|-------|------|------|
| Phase 1 | Drive 探查 + 下载 | 7h |
| Phase 1 | 审计报告 | 9h |
| Phase 1 | Taxonomy 设计 + 评审 | 8h |
| Phase 1 | DB Architecture + 建表 | 12h |
| **Phase 1 小计** | | **36h (~1 周)** |
| Phase 2 | 文件智能提取 (Agent) | 8h |
| Phase 2 | Taxonomy 标签 (Agent) | 4h |
| Phase 2 | 搜索索引 | 4h |
| Phase 2 | 入库 + 种子数据 | 4h |
| Phase 2 | 查询 API | 6h |
| **Phase 2 小计** | | **26h (~1 周)** |
| Phase 3 | 知识平台 UI | 15h |
| Phase 3 | Discovery Dashboard | 12h |
| **Phase 3 小计** | | **27h (~1 周)** |
| Phase 4 | Drive 自动检测 | 4h |
| Phase 4 | Module A → B 集成 | 4h |
| Phase 4 | UAT | 6h |
| Phase 4 | 培训材料 | 6h |
| **Phase 4 小计** | | **20h (~0.5 周)** |
| **总计** | | **~109h (~3.5 周)** |
