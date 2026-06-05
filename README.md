# AI 编导脚本生成工具 Demo

这是基于 `docs/prd/AI编导脚本生成工具_PRD.md` 做的可运行 MVP demo，用于验证 PRD 中的核心链路：

```text
任务创建 -> 产品信息录入 -> AI 卖点拆解 -> AI 选题生成 -> AI 脚本生成 -> 风险词初筛 -> 人工编辑审核 -> 脚本版本保存 -> CSV/Excel 导出
```

## 启动方式

首次启用 Supabase 存储前需要安装数据库连接依赖：

```bash
python -m pip install -r requirements.txt
```

```bash
python server.py
```

默认访问：

```text
http://127.0.0.1:8000
```

如果 8000 被占用，可以指定端口：

```bash
$env:PORT="8001"
python server.py
```

## AI 配置

未配置 `DEEPSEEK_API_KEY` 时，系统会使用本地演示模式，保证 demo 核心链路可跑通。

配置真实 DeepSeek 调用，建议复制 `.env.example` 为项目根目录的 `.env.local`，再填写真实密钥：

```text
DEEPSEEK_API_KEY=你的 API Key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
PORT=8000
```

然后启动：

```bash
python server.py
```

配置加载顺序为：系统环境变量优先，其次 `.env.local`，最后 `.env`。`.env.local` 已加入 `.gitignore`，适合保存本机真实 API Key 和数据库密码。

## Supabase 存储配置

默认情况下，系统继续把运行数据保存在 `data/runtime/*.jsonl`。如果要切换到 Supabase Postgres，把 `.env.example` 复制为 `.env.local` 后，至少填写下面几项：

```text
STORAGE_BACKEND=supabase
SUPABASE_DB_HOST=aws-0-REGION.pooler.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.PROJECT_REF
SUPABASE_DB_PASSWORD=你的数据库密码
SUPABASE_DB_SSLMODE=require
SUPABASE_DB_SCHEMA=app_private
SUPABASE_TABLE_PREFIX=ai_script
```

也可以不拆分字段，直接填写 Supabase Dashboard `Connect` 里复制出来的完整连接串：

```text
STORAGE_BACKEND=supabase
SUPABASE_DB_URL=postgresql://postgres.PROJECT_REF:你的数据库密码@aws-0-REGION.pooler.supabase.com:5432/postgres?sslmode=require
```

启动后访问下面接口可以确认当前存储后端：

```text
http://127.0.0.1:8000/api/health
```

应用会在首次读写 Supabase 时自动创建 `app_private` schema，并按 PRD 拆分保存任务、产品、卖点拆解、选题、脚本、脚本版本和投放复盘。参考结构见 `docs/supabase/storage_schema.sql`。为了避免前端暴露数据库能力，当前实现只在 Python 后端使用 Postgres 连接，不把 Supabase service role 或数据库密码传给浏览器。

如果使用 `postgresql://postgres:...@db.PROJECT_REF.supabase.co:5432/postgres` 直连串时遇到 DNS 或 IPv6 连接不稳定，建议改用 Supabase Dashboard `Connect` 里的 Session Pooler 连接串，并放到 `SUPABASE_DB_URL`。当前代码会对连接建立做短重试，重试次数可通过 `SUPABASE_CONNECT_RETRIES` 调整。

## 页面能力

- 产品信息表单：录入产品名称、核心卖点、目标用户、使用场景、平台、业务目标、内容形式、价格权益、证明材料和合规要求。
- 任务创建：点击“创建任务”后调用 `/api/tasks`。
- AI 卖点拆解：点击“AI 卖点拆解”后调用 `/api/decompose`，同时沉淀产品和卖点拆解记录。
- AI 选题生成：点击“生成选题池”后调用 `/api/topics`，同时沉淀结构化选题记录。
- AI 脚本生成：选择一个选题后调用 `/api/script`，生成待审核脚本并保存 AI 初稿版本。
- 风险词初筛：点击“风险词初筛”后调用 `/api/risk-scan`，命中结果会回写当前脚本。
- 结果展示：展示标题、Hook、口播脚本、分镜建议、字幕重点、素材建议、转化口播、合规提醒、待确认信息和风险词初筛。
- 人工编辑审核：可在页面修改口播脚本，点击“保存审核版本”后调用 `/api/review`，写入脚本库和版本记录。
- 表格自动化：脚本库表格自动刷新，支持 `/api/export.csv` 导出 CSV，支持 `/api/export.xls` 导出 Excel 可读文件，导出时回写脚本导出状态和导出时间。

## 代码结构

```text
server.py
  项目启动入口，调用 src/http_server.py。

src/http_server.py
  本地 HTTP 服务，负责静态页面、任务、拆解、选题、脚本、风险、审核版本、查询和导出接口。

src/demo_core.py
  核心业务逻辑，包括产品信息校验、本地卖点拆解、本地选题生成、本地脚本生成、风险词扫描、CSV 和 Excel 导出。

src/ai_client.py
  AI 客户端逻辑，包括 Prompt 构造、DeepSeek Chat Completions API 调用、返回文本提取和 JSON 解析。

src/storage.py
  任务、产品、卖点拆解、选题、脚本、版本和投放数据的存储层，支持本地 JSONL 和 Supabase Postgres 双后端。

src/config.py
  加载 .env 和 .env.local 配置文件，系统环境变量优先级最高。

web/index.html
  Demo 主页面。

web/styles.css
  页面样式。

web/app.js
  前端交互逻辑，负责表单提交、结果渲染、保存和表格刷新。

tests/
  单元测试，覆盖核心业务、AI 返回解析和本地存储。

data/runtime/
  JSONL 模式下运行后生成的本地任务、产品、拆解、选题、脚本和版本记录。

docs/supabase/
  Supabase 存储表结构参考。

docs/prd/
  PRD Markdown 和 Word 文档。

docs/assets/
  页面截图等说明材料。

tools/
  文档生成等辅助脚本。
```

## 验证命令

```bash
python -m unittest discover -s tests -v
python -m py_compile server.py src\http_server.py src\demo_core.py src\ai_client.py src\storage.py src\config.py
```
