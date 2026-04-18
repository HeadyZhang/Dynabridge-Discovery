# Claude Code 自主搭建 Module B — 完整配置指南

> 目标：让 Claude Code 按照 Roadmap 自主搭建，自检，自验收，自修复。
> 你只需要在关键节点审查，而不是逐行指导。

---

## 核心方法论：Ralph Loop

Ralph Loop 的核心思想很简单：给 Claude Code 一个明确的任务 + 明确的"完成"标准，让它循环工作直到所有标准通过。

关键要素：
1. **原子任务**：每个任务足够小，有明确的 pass/fail
2. **自验证**：每完成一步，跑测试/检查来证明它真的完成了
3. **学习循环**：犯的错记到 LEARNINGS.md，下一轮不再犯
4. **完成信号**：只有所有检查都通过，才能输出 "RALPH_COMPLETE"

---

## 第一步：项目结构准备

在你的 `Dynabridge-Discovery/` 项目根目录下执行：

```bash
# 1. 创建 Module B 目录结构
mkdir -p backend/module_b
mkdir -p backend/module_b/scripts
mkdir -p .claude/commands
mkdir -p tasks

# 2. 把 roadmap 文件放进项目
cp Module_B_Full_Atomic_Roadmap.md tasks/ROADMAP.md

# 3. 初始化任务追踪文件
touch tasks/todo.md
touch tasks/LEARNINGS.md
touch tasks/progress.txt
```

---

## 第二步：CLAUDE.md 配置

```bash
cat > CLAUDE.md << 'CLAUDEMD'
# Dynabridge Brand Discovery — Module B

## 项目概述
这是 Dynabridge 品牌咨询公司的 AI 自动化系统。
Module B = 历史案例知识库 + Customer Discovery Database。
代码在 backend/module_b/ 下。

## 技术栈
- 后端: FastAPI (Python 3.11+) + SQLAlchemy + SQLite
- AI: Anthropic Claude API (claude-sonnet-4-20250514)
- 爬虫: Playwright
- 向量搜索: sentence-transformers (all-MiniLM-L6-v2)
- 前端: Next.js 16 + React 19 + TypeScript + Tailwind CSS 4
- 部署: Docker Compose
- Google Drive: google-api-python-client + google-auth-oauthlib

## 代码规范
- Python: 类型注解必须完整，用 dataclass 或 Pydantic
- 异步: 所有 IO 操作用 async/await
- 错误处理: 所有外部调用 (Google API, Claude API) 必须 try/except，失败时记录日志并返回 None，不抛异常
- 导入: 相对导入用于 module_b 内部，绝对导入用于 backend/ 共享模块
- 测试: 每个模块写 pytest 测试，放在 backend/tests/module_b/
- 日志: 用 Python logging，不用 print（除了 scripts/ 下的脚本）

## 目录结构
```
backend/
├── main.py              # FastAPI 入口（Module A + B 共享）
├── models.py            # SQLAlchemy 模型（Module A 已有表，Module B 追加表）
├── config.py            # 路径/密钥配置
├── pipeline/            # Module A（不要修改）
├── module_b/            # Module B（你的工作区）
│   ├── __init__.py
│   ├── auth.py          # Google Drive OAuth
│   ├── gdrive.py        # Google Drive 文件操作
│   ├── audit.py         # 文件审计
│   ├── models.py        # Module B 数据模型
│   ├── taxonomy.py      # Taxonomy 定义
│   ├── search_index.py  # 全文 + 向量搜索
│   ├── api.py           # FastAPI router
│   ├── integration.py   # Module A → B 集成
│   └── scripts/         # 独立运行脚本
└── tests/module_b/      # 测试
```

## 关键约束
- 不要修改 backend/pipeline/ 下的任何文件（Module A 代码）
- 不要修改 backend/models.py 中已有的 Module A 表（projects, slides, comments, uploaded_files）
- Module B 的表追加在 backend/models.py 末尾，或放在 backend/module_b/models.py 中
- Google Drive credentials.json 和 token.json 不要提交到 git
- 所有 API 密钥通过环境变量读取，不硬编码

## 任务管理
- 主 roadmap: tasks/ROADMAP.md
- 当前任务: tasks/todo.md
- 经验教训: tasks/LEARNINGS.md
- 进度记录: tasks/progress.txt
- 每完成一个任务，在 tasks/todo.md 中标记 [x]
- 每遇到一个问题并解决，记到 tasks/LEARNINGS.md
- 每个里程碑完成后，更新 tasks/progress.txt

## 自检清单（每次 commit 前必做）
1. `cd backend && python -m pytest tests/module_b/ -v` — 所有测试通过
2. `python -m py_compile module_b/auth.py` — 无语法错误（对每个改动文件）
3. `grep -r "print(" module_b/*.py` — 主代码不用 print（scripts/ 除外）
4. `grep -r "api_key\|secret\|password" module_b/` — 无硬编码密钥
CLAUDEMD
```

---

## 第三步：Slash Commands

### /project:plan — 从 Roadmap 生成当前阶段任务

```bash
cat > .claude/commands/plan.md << 'CMD'
根据 tasks/ROADMAP.md 中的当前阶段，生成下一批要做的原子任务。

步骤：
1. 读取 tasks/ROADMAP.md
2. 读取 tasks/progress.txt 了解已完成的任务
3. 找到下一个未完成的 Phase/Section
4. 将该 Section 的任务拆解为可直接执行的原子任务
5. 写入 tasks/todo.md，格式：

```markdown
# 当前阶段: Phase X — Section Y.Z

## 任务列表
- [ ] 任务1: 具体描述
  - 文件: backend/module_b/xxx.py
  - 验收: 运行 `python -m pytest tests/module_b/test_xxx.py` 通过
- [ ] 任务2: ...
```

6. 告诉我你规划了什么，等我确认后再开始执行
CMD
```

### /project:build — 执行当前任务列表

```bash
cat > .claude/commands/build.md << 'CMD'
执行 tasks/todo.md 中所有未完成的任务。

对每个任务：
1. 读取任务描述和验收标准
2. 先读 tasks/LEARNINGS.md 查看相关经验
3. 实现代码
4. 写测试
5. 运行测试验证
6. 如果测试失败 → 修复 → 重新测试 → 直到通过
7. 标记任务为 [x]
8. 更新 tasks/progress.txt
9. git add + commit（代码和 progress 一起提交）

关键规则：
- 永远不要标记一个任务 [x] 而不先运行验证命令
- 如果连续 3 次修复同一个错误失败，停下来记到 LEARNINGS.md 并问我
- 每个文件改动后先跑 py_compile 确认无语法错误
- commit message 格式: "module_b: [phase X.Y] 描述"
CMD
```

### /project:verify — 验收当前阶段

```bash
cat > .claude/commands/verify.md << 'CMD'
对当前阶段的所有产出执行全面验收检查。

步骤：
1. 读取 tasks/todo.md 确认所有任务都标记为 [x]
2. 运行完整测试套件：
   ```bash
   cd backend && python -m pytest tests/module_b/ -v --tb=short
   ```
3. 检查代码质量：
   ```bash
   # 类型检查
   cd backend && python -m mypy module_b/ --ignore-missing-imports || true
   # 无硬编码密钥
   grep -rn "api_key\|secret\|password\|token" module_b/*.py | grep -v "os.getenv\|os.environ\|environ.get\|config\." || echo "OK: no hardcoded secrets"
   ```
4. 检查 ROADMAP 中该阶段的所有交付物是否存在
5. 输出验收报告：

```markdown
## 验收报告: Phase X

### 通过 ✅
- [x] 所有测试通过 (N/N)
- [x] 无硬编码密钥
- [x] 交付物 A 存在
- [x] 交付物 B 存在

### 失败 ❌
- [ ] 问题描述 → 修复方案

### 结论: PASS / FAIL
```

6. 如果 FAIL → 自动修复失败项 → 重新验收
7. 如果 PASS → 更新 tasks/progress.txt，提示我可以进入下一阶段
CMD
```

### /project:fix — 自动修复失败的测试

```bash
cat > .claude/commands/fix.md << 'CMD'
读取最近的测试失败输出，自动诊断并修复。

步骤：
1. 运行 `cd backend && python -m pytest tests/module_b/ -v --tb=long 2>&1 | tail -100`
2. 分析失败原因
3. 修复代码
4. 重新运行测试
5. 如果通过 → 记录修复方法到 LEARNINGS.md
6. 如果仍失败 → 再试一次（最多 3 次）
7. 3 次仍失败 → 记录问题到 LEARNINGS.md，询问我
CMD
```

---

## 第四步：Hooks 配置

```bash
cat > .claude/settings.json << 'HOOKS'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "file=\"$CLAUDE_TOOL_INPUT_FILE\"; if [[ \"$file\" == *.py ]] && [[ \"$file\" == *module_b* ]]; then python -m py_compile \"$file\" 2>&1 || echo 'SYNTAX ERROR in $file'; fi",
        "description": "每次写入 module_b 的 Python 文件后自动检查语法"
      },
      {
        "matcher": "Write|Edit",
        "command": "file=\"$CLAUDE_TOOL_INPUT_FILE\"; if [[ \"$file\" == *.py ]] && [[ \"$file\" == *module_b* ]]; then grep -n 'api_key\\|secret\\|password' \"$file\" | grep -v 'os.getenv\\|environ\\|config\\.' | head -5 && echo 'WARNING: possible hardcoded secret' || true; fi",
        "description": "检测硬编码密钥"
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "echo \"$CLAUDE_TOOL_INPUT\" | grep -qE 'rm -rf /|drop table|DROP TABLE' && echo 'BLOCKED: dangerous command' && exit 1 || exit 0",
        "description": "阻止危险命令"
      },
      {
        "matcher": "Write|Edit",
        "command": "file=\"$CLAUDE_TOOL_INPUT_FILE\"; if [[ \"$file\" == backend/pipeline/* ]] || [[ \"$file\" == frontend/* && \"$file\" != frontend/src/app/knowledge/* ]]; then echo 'BLOCKED: do not modify Module A files'; exit 1; fi; exit 0",
        "description": "保护 Module A 文件不被修改"
      }
    ],
    "Stop": [
      {
        "type": "prompt",
        "prompt": "检查 tasks/todo.md 中是否还有未完成的 [ ] 任务。如果有，继续工作。如果没有，确认所有测试通过后才能停止。",
        "description": "防止 Claude 提前停止"
      }
    ]
  }
}
HOOKS
```

**Hook 解释**：

| Hook | 类型 | 作用 |
|------|------|------|
| PostToolUse: py_compile | 命令 | 每次写 .py 文件后自动语法检查 |
| PostToolUse: secret check | 命令 | 每次写文件后检查硬编码密钥 |
| PreToolUse: dangerous cmd | 命令 | 阻止 `rm -rf /` 等危险命令 |
| PreToolUse: protect Module A | 命令 | 阻止修改 pipeline/ 下的 Module A 代码 |
| Stop: check tasks | Prompt | Claude 试图停止时，检查任务是否全部完成 |

---

## 第五步：Master Prompt 模板

这是你给 Claude Code 的**第一条指令**。每个 Phase 用一个 Master Prompt 启动一个新 session。

### Phase 1 Master Prompt

```markdown
你的任务是实现 Dynabridge Module B Phase 1 的全部内容。

## 开始前必读
1. 先读 tasks/LEARNINGS.md（如果存在）
2. 再读 tasks/ROADMAP.md 的 Phase 1 部分
3. 再读 tasks/progress.txt 了解已完成的工作

## Phase 1 任务清单

### 1.1 Google Drive 连接
创建 backend/module_b/auth.py:
- get_drive_credentials() 函数
- SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
- 支持 token.json 缓存和自动刷新
- credentials.json 路径从 config.py 读取

验收: 
```bash
cd backend && python -c "from module_b.auth import get_drive_credentials; creds = get_drive_credentials(); print('OK' if creds else 'FAIL')"
```

### 1.2 Google Drive 文件操作
创建 backend/module_b/gdrive.py:
- GDriveClient 类
- list_folder(folder_id, recursive=True) → list[dict]
- download_file(file_id, save_path) — 含 Google Slides→PPTX 自动导出
- download_case_folder(folder_id, local_dir) → list[dict]

验收:
```bash
cd backend && python -c "
from module_b.auth import get_drive_credentials
from module_b.gdrive import GDriveClient
creds = get_drive_credentials()
client = GDriveClient(creds)
files = client.list_folder('FOLDER_ID_HERE')
print(f'Found {len(files)} files')
assert len(files) > 0, 'No files found'
print('OK')
"
```

### 1.3 审计报告
创建 backend/module_b/audit.py:
- generate_audit_report(files: list[dict]) → dict
- 输出: total_files, file_types, case_completeness, issues

验收:
```bash
cd backend && python -m pytest tests/module_b/test_audit.py -v
```

### 1.4 Taxonomy
创建 backend/module_b/taxonomy.py:
- TAXONOMY_SCHEMA 字典（8 个维度，每个有 values 列表）
- validate_taxonomy(tags: dict) → list[str] 返回验证错误

验收:
```bash
cd backend && python -m pytest tests/module_b/test_taxonomy.py -v
```

### 1.5 数据模型
在 backend/module_b/models.py 中创建所有 Module B 的 SQLAlchemy 模型:
- CaseRecord, CaseFile, CaseTag
- DiscoveryEngagement, DiscoveryReport, DiscoverySegment
- DiscoveryQuestionnaire, QuestionnaireResponse, CrossTabulation
- 必须能和 Module A 的 models.py 共存（共享 Base）

验收:
```bash
cd backend && python -c "
from module_b.models import *
from models import engine, Base
Base.metadata.create_all(engine)
from sqlalchemy import inspect
tables = inspect(engine).get_table_names()
required = ['case_records', 'case_files', 'case_tags', 'discovery_engagements']
missing = [t for t in required if t not in tables]
assert not missing, f'Missing tables: {missing}'
print(f'OK: {len(tables)} tables total')
"
```

### 1.6 测试
为每个模块写测试:
- tests/module_b/test_audit.py
- tests/module_b/test_taxonomy.py
- tests/module_b/test_models.py

## 工作流程
1. 先创建 tasks/todo.md 列出所有任务
2. 逐个实现 + 测试
3. 每完成一个标记 [x] + git commit
4. 全部完成后运行 /project:verify

## 完成信号
只有当以下条件全部满足时，输出 "PHASE_1_COMPLETE":
- tasks/todo.md 中所有任务标记 [x]
- `python -m pytest tests/module_b/ -v` 全部通过
- 所有 .py 文件通过 py_compile
- 无硬编码密钥
```

### Phase 2 Master Prompt

```markdown
你的任务是实现 Dynabridge Module B Phase 2 的全部内容。

## 开始前必读
1. tasks/LEARNINGS.md
2. tasks/ROADMAP.md Phase 2 部分
3. tasks/progress.txt

## Phase 2 任务清单

### 2.1 全文搜索索引
创建 backend/module_b/search_index.py:
- FullTextIndex 类（SQLite FTS5）
- index_case(case_id, brand_name, industry, key_insights, full_text)
- search(query, limit=10) → list[dict]

验收:
```bash
cd backend && python -m pytest tests/module_b/test_search.py -v
```

### 2.2 向量搜索索引
在 backend/module_b/search_index.py 中追加:
- VectorIndex 类（sentence-transformers + numpy）
- add_case(case_id, text, metadata)
- search(query, top_k=5) → list[dict]

验收:
```bash
cd backend && python -c "
from module_b.search_index import VectorIndex
vi = VectorIndex()
vi.add_case('test1', '健身品牌出海美国市场', {'industry': 'fitness'})
vi.add_case('test2', '美妆护肤品欧洲定价策略', {'industry': 'beauty'})
results = vi.search('fitness brand going global')
assert results[0]['case_id'] == 'test1'
print('OK')
"
```

### 2.3 数据入库
创建 backend/module_b/ingest.py:
- ingest_case(case_name, taxonomy, file_extractions) → str (case_id)
- 写入 CaseRecord + CaseFile + CaseTag

验收:
```bash
cd backend && python -m pytest tests/module_b/test_ingest.py -v
```

### 2.4 跨案例查询 API
创建 backend/module_b/api.py:
- FastAPI Router，prefix="/api/knowledge"
- GET /cases — 列表 + 筛选
- GET /cases/{id} — 详情
- GET /search?q= — 全文 + 语义搜索
- GET /discovery/search — 跨案例查询

验收:
```bash
cd backend && python -m pytest tests/module_b/test_api.py -v
```

### 2.5 注册 API 路由
在 backend/main.py 中:
- import module_b.api
- app.include_router(module_b.api.router)
- 不修改任何 Module A 的端点

验收:
```bash
cd backend && python -c "
from main import app
routes = [r.path for r in app.routes]
assert '/api/knowledge/cases' in routes
assert '/api/projects' in routes  # Module A 端点仍在
print('OK')
"
```

## 完成信号
PHASE_2_COMPLETE
```

---

## 第六步：实际执行流程

### 启动

```bash
# 1. 进入项目目录
cd Dynabridge-Discovery

# 2. 安装 Ralph Loop（如果要用自动循环）
claude plugins install ralph-loop

# 3. 启动 Claude Code
claude

# 4. 第一条命令：初始化
> 读取 tasks/ROADMAP.md，然后执行 Phase 1 Master Prompt 中的所有任务。
> 开始前先创建 tasks/todo.md 列出所有任务。
> 每完成一个任务，运行验收命令确认通过后再标记 [x]。
> 如果测试失败，修复后重试，最多 3 次。3 次仍失败就停下来问我。
```

### 或用 Ralph Loop 自动执行

```bash
# 把 Master Prompt 保存为文件
cat > tasks/phase1_prompt.md << 'EOF'
[粘贴上面的 Phase 1 Master Prompt]
EOF

# 启动 Ralph Loop
claude /ralph-loop tasks/phase1_prompt.md

# Claude Code 会：
# 1. 读取 prompt
# 2. 执行任务
# 3. 如果 session 结束但未输出 PHASE_1_COMPLETE → 自动重启新 session 继续
# 4. 直到所有任务完成
```

### 你需要做的

| 时机 | 你的动作 |
|------|---------|
| Claude Code 开始前 | 确认 Google Drive FOLDER_ID 填对了 |
| Claude Code 遇到 3 次失败 | 看 LEARNINGS.md，决定是 prompt 问题还是真的 bug |
| Phase 1 COMPLETE | 审查代码，运行 /project:verify，确认交付物 |
| 进入 Phase 2 | 启动新 session，输入 Phase 2 Master Prompt |
| Phase 2 需要 Managed Agent | 这部分 Claude Code 无法自动做——你需要手动配置 Agent |

---

## 第七步：哪些任务适合自动，哪些需要人工

```
✅ 完全自动化（Claude Code 独立完成）
├── auth.py — OAuth 凭证管理
├── gdrive.py — 文件列表 + 下载
├── audit.py — 审计报告生成
├── taxonomy.py — Taxonomy schema 定义
├── models.py — SQLAlchemy 数据模型
├── search_index.py — 全文 + 向量搜索
├── ingest.py — 数据入库
├── api.py — FastAPI 路由
├── integration.py — Module A → B 集成
└── 所有测试文件

⚠️ 半自动（Claude Code 写代码，你验证结果）
├── 探查 Google Drive 实际文件结构 → 你看结果确认
├── 下载文件 → 你确认文件完整
├── 前端知识平台页面 → 你看 UI 效果
└── Dashboard 图表 → 你看可视化效果

❌ 需要人工（Claude Code 做不了）
├── Google OAuth 首次授权（需要浏览器弹窗 + 人登录）
├── Managed Agent 创建和配置（需要 Anthropic API 操作）
├── 与 Dynabridge 品牌专家的 Taxonomy 评审会议
├── 培训视频录制
└── 最终 IP 交付和签字确认
```

---

## 关键经验（来自社区最佳实践）

1. **一次只给一个 Phase 的任务**。不要把整个 Roadmap 扔给 Claude Code——它的 context window 会被淹没。每个 Phase 启动一个新 session。

2. **验收命令必须是可执行的 bash**。"检查代码质量"不是验收标准，`python -m pytest tests/ -v` 才是。Claude Code 可以自己运行 bash 来验证。

3. **LEARNINGS.md 是复利**。Phase 1 踩的坑写进 LEARNINGS.md，Phase 2 的 Claude Code 会先读它。到 Phase 4，Claude Code 已经是你项目的专家了。

4. **Stop hook 是关键防线**。没有 Stop hook，Claude Code 会在完成一半时说"我已经实现了基础框架，你可以在此基础上扩展"然后停止。Stop hook 强制它检查 todo.md 是否全部 [x]。

5. **Protect Module A hook 必须有**。Claude Code 看到 Module A 代码时可能会"顺便优化一下"，这会破坏已有功能。PreToolUse hook 硬性阻止它修改 pipeline/ 目录。

6. **Git commit 是检查点**。每个任务完成后 commit，如果后续任务把代码搞崩了，可以 `git revert` 回到上一个好的状态。
