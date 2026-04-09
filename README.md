# PM Interview Protocol v2.0 — 系统文档

## 案例示范
以下是不同回答效果和评判结果，根据回答内容的结构表达、数据意识、产品判断、复盘深度、语言表达进行综合评分，如果有语音输入则将语音输入也纳入评分
<img width="2514" height="1203" alt="3e6676476b8a97c35feea8a242176d59" src="https://github.com/user-attachments/assets/0fc233ec-cb19-41e8-bb3b-b1ec1a2ccb2e" />
<img width="2559" height="1347" alt="509dd0fe630c60a0533b1d7b5500edef" src="https://github.com/user-attachments/assets/2176ce1c-a43a-47d7-a66b-e77124ca37a2" />
<img width="2559" height="1347" alt="bc790a6f877e1d7fd7691a48f0b7a131" src="https://github.com/user-attachments/assets/79415546-49c4-447c-bda1-d95e6c46a20f" />
<img width="2559" height="1347" alt="04afd13848c48cee02747b8ad0e9294b" src="https://github.com/user-attachments/assets/9e09359b-6a0a-416c-80f4-820fb8c06266" />

## 一、项目概述

PM Interview Protocol 是一个前后端分离的产品经理面试模拟系统，支持：
- 基于用户简历的 AI 动态追问（每轮追问都针对上一轮的具体弱点）
- 三种面试强度模式（标准 / 压力 / 总监），每种模式有独立的追问 Prompt
- 语音优先输入，实时统计语速并纳入评分
- 五维度评分（结构表达、数据意识、产品判断、复盘深度、语言表达）

---

## 二、文件结构

```
interview_project/
├── config.py        ← API Key 及服务配置（不要提交到 Git！）
├── app.py           ← Python Flask 后端（所有业务逻辑）
├── index.html       ← 前端页面（UI + 语音 + API 调用）
├── requirements.txt ← Python 依赖
└── README.md        ← 本文档
```

---

## 三、各模块功能说明

### 3.1 `config.py` — 配置管理

| 配置项 | 说明 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API Key，填入后启用 AI 动态追问和智能评分 |
| `HOST / PORT` | Flask 服务监听地址（默认 0.0.0.0:5000） |
| `DEBUG` | 开发模式开关 |
| `CORS_ORIGINS` | 允许跨域的前端地址列表 |

> **安全提示**：将 `config.py` 加入 `.gitignore`，不要提交到版本控制。

---

### 3.2 `app.py` — Python 后端

#### 核心功能模块

**① 简历解析（`analyze_resume`）**

接收用户粘贴的简历文本，通过正则表达式提取：
- 关键指标（百分比、万/亿/次等数字）
- 产品方法论关键词（ABTest、埋点、留存、漏斗等）
- 项目列表（自动猜测项目名、提取指标和动作词）
- 追问锚点（指标真实性、个人贡献边界等）

对应 API：`POST /api/parse_resume`

---

**② 动态题目生成（`api_get_question`）**

第 1 轮使用静态模板题；第 2-5 轮通过 Claude API 动态生成，追问逻辑：
- 将前几轮的问题、答案、得分、最弱维度传入 Claude
- Claude 根据候选人的具体弱点生成针对性追问
- 无 API Key 时自动降级为静态题目（规则模板）

对应 API：`POST /api/get_question`

---

**③ 三种面试模式的 Prompt**

| 模式 | Prompt 核心方向 |
|---|---|
| **标准模式** | 专业节奏，考察结构→目标→动作→结果→复盘，语气不刁难 |
| **压力模式** | 追问数据真实性（基线/归因/对照组）、个人贡献边界（我vs我们）、方案取舍依据，语气犀利 |
| **总监模式** | 考察全局视野、资源优先级判断、组织协同、风险对冲、第二曲线思维，像业务终面 |

---

**④ 语音分析（`analyze_speech_metrics`）**

前端传入：
- `duration_seconds`：录音时长（秒）
- `char_count`：识别字符数
- `pause_count`：停顿次数
- `raw_transcript`：原始转写文本

后端计算：
- **语速**（字/分钟）：正常范围 200-280 字/分钟
- **流畅度得分**（0-10）：基于语速和停顿频率
- **速度标签**：语速偏慢/适中/偏快

---

**⑤ 答案评分（`evaluate`）**

优先调用 Claude AI 评分（需要 API Key），降级到规则引擎：

**评分维度（各 0-10 分）：**
- **结构表达**：回答是否有背景→目标→动作→结果的框架，是否使用"我"而非"我们"
- **数据意识**：是否有可验证指标、基线、对比和归因逻辑
- **产品判断**：是否体现方案取舍、用户洞察、优先级判断
- **复盘深度**：是否提到失败、风险、副作用和调整动作
- **语言表达**：综合语速、停顿、遣词造句和逻辑连贯性（来自语音分析）

压力模式下评分标准整体偏严（-0.5 到 -1 分）；总监模式着重 judgment 维度。

对应 API：`POST /api/evaluate`

---

**⑥ 最终报告（`api_report`）**

汇总 5 轮数据，生成：
- 综合得分和晋级建议（Strong Hire / Need More Evidence / Not Yet）
- 最强/最弱维度分析
- 每轮分数曲线
- 语音表达综合评价
- 个性化提升建议

对应 API：`POST /api/report`

---

### 3.3 `index.html` — 前端页面

#### 页面流程

```
Boot（启动动画）→ Brief（简历输入 + 模式选择）→ Interview（5轮面试）→ Report（最终报告）
```

#### 简历输入逻辑

- 页面默认加载内置示例简历（字节跳动 + 小红书背景）并自动解析
- 用户在文本框内输入内容后，自动切换为自定义简历（防抖 700ms 再调用解析接口）
- 清空输入框后，自动回到示例简历

#### 语音输入逻辑（核心）

- 进入每轮面试题后，**自动启动麦克风**（无需手动点击）
- 实时显示语速（字/分钟）、录音时长、停顿次数
- 提交时将 `speech_data`（含原始转写文本）传给后端，纳入 AI 评分
- 支持手动点击麦克风停止/继续，也可直接键盘输入补充

#### 动态追问展示

- AI 生成的追问题目带有 `AI动态追问` 蓝色标签
- 每次提交后自动向后端请求下一题（携带完整对话历史）

---

## 四、快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `config.py`，填入 Anthropic API Key：
```python
ANTHROPIC_API_KEY = "sk-ant-你的key"
```

> 不填写 API Key 也可运行，将使用规则引擎评分 + 静态题目。

### 3. 启动后端

```bash
python app.py
```

后端运行在 `http://127.0.0.1:5000`

### 4. 打开前端

用 **Chrome 或 Edge** 浏览器直接打开 `index.html`。

> 语音功能需要 Chrome/Edge，Safari 不支持 Web Speech API。

---

## 五、API 接口速查

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/parse_resume` | 解析简历文本 |
| POST | `/api/get_question` | 动态生成面试题（含历史追问） |
| POST | `/api/evaluate` | 评分单条答案（含语音分析） |
| POST | `/api/report` | 生成最终报告 |
| GET  | `/api/session_id` | 获取随机 Session ID |

---

## 六、.gitignore 建议

```
config.py
__pycache__/
*.pyc
.env
```
