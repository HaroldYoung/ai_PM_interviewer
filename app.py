"""
PM Interview Protocol — Python 后端 v2.0
依赖: flask flask-cors openai
运行: python app.py
"""

import re
import json
import random
import string
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from config import DEEPSEEK_API_KEY, HOST, PORT, DEBUG, CORS_ORIGINS
except ImportError:
    DEEPSEEK_API_KEY = ""
    HOST = "0.0.0.0"
    PORT = 5000
    DEBUG = True
    CORS_ORIGINS = ["*"]

try:
    from openai import OpenAI
    _ai_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    ) if DEEPSEEK_API_KEY else None
except ImportError:
    _ai_client = None

app = Flask(__name__)
CORS(app, origins=CORS_ORIGINS)

# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def uniq(lst):
    seen = set()
    out = []
    for x in lst:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def session_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def call_claude(system_prompt, user_prompt, max_tokens=1200):
    """调用 DeepSeek API，无 API Key 时返回 None"""
    if not _ai_client:
        return None
    try:
        response = _ai_client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"DeepSeek API error: {e}")
        return None

# ─────────────────────────────────────────
# 简历解析
# ─────────────────────────────────────────

def guess_title(line, index):
    matches = re.findall(r'(会员增长|AI助手|增长|留存|推荐|活动|搜索|商业化|埋点|冷启动|风控|电商|社区|内容)', line)
    presets = ["会员增长项目", "AI助手项目", "用户增长项目", "核心产品项目"]
    return f"{matches[0]}项目" if matches else (presets[index] if index < len(presets) else f"项目{index+1}")

def build_focus(line, metrics, actions, methods):
    out = []
    if metrics:         out.append("指标真实性")
    if actions:         out.append("个人贡献边界")
    if methods:         out.append("方案设计方法")
    if re.search(r'复盘|问题|误触|失败|波动', line):  out.append("复盘深度")
    if re.search(r'协同|推动|联动', line):             out.append("跨团队推进")
    if not re.search(r'为什么|原因', line):            out.append("目标定义逻辑")
    return uniq(out)[:4]

def analyze_resume(text):
    keywords = uniq(
        re.findall(r'\d+(?:\.\d+)?%|\d+(?:\.\d+)?(?:万|千|亿|天|周|月|次)', text) +
        re.findall(r'留存|转化|GMV|DAU|MAU|CTR|LTV|NPS|ROI|使用率|召回|成本|满意度|增长|漏斗|实验', text) +
        re.findall(r'用户访谈|AB实验|A/B|PRD|埋点|灰度|策略|分层|画像|增长|留存|推荐|AI助手|冷启动|复盘|协同', text)
    )[:16]
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    raw_lines = lines if lines else [text]
    projects = []
    for index, line in enumerate(raw_lines[:4]):
        metrics = re.findall(r'\d+(?:\.\d+)?%|\d+(?:\.\d+)?(?:万|千|亿|天|周|月|次)', line)
        actions = re.findall(r'负责|推动|设计|主导|搭建|优化|梳理|上线|复盘|验证|协同|分析|拆解|定义', line)
        methods = re.findall(r'用户访谈|AB实验|A/B|PRD|埋点|灰度|策略|分层|漏斗|画像|实验|复盘', line)
        projects.append({
            "title": guess_title(line, index), "summary": line,
            "metrics": metrics, "actions": actions, "methods": methods,
            "focus": build_focus(line, metrics, actions, methods)
        })
    if not projects:
        projects = [{"title": "核心产品项目", "summary": "待补充项目经历",
                     "metrics": [], "actions": [], "methods": [], "focus": ["目标定义", "方案拆解", "结果归因"]}]
    return {"text": text, "keywords": keywords, "projects": projects,
            "focusPoints": uniq([f for p in projects for f in p["focus"]])[:8]}

# ─────────────────────────────────────────
# 动态题目生成
# ─────────────────────────────────────────

MODE_SYSTEM_PROMPTS = {
    "standard": """你是一位经验丰富的产品经理面试官，风格专业、有节奏感。
职责：生成一道针对候选人的面试追问。
要求：
- 基于候选人上一轮的具体回答找到弱点进行追问
- 结构清晰，考察背景→目标→动作→结果→复盘
- 语气专业但不刁难，给候选人展示自己的空间
- 问题聚焦在一个具体点上，不要一次问多个问题
- 用中文，问题长度控制在50-100字""",

    "pressure": """你是一位以"打穿候选人"著称的高压面试官，来自顶级互联网大厂。
职责：生成一道高强度压力追问。
要求：
- 直接指出候选人回答中最薄弱的地方，毫不客气
- 追问数据真实性：你说的"提升X%"，基线是什么？怎么归因？有对照组吗？
- 追问个人贡献：这是你做的还是团队的？你具体做了哪个决策？
- 追问方案取舍：为什么选这个方案？排除了哪些？依据是什么？
- 语气犀利，可以直接质疑候选人的表述
- 如果候选人回答模糊，用"你说的X，我没听明白，能具体说说吗？"方式追问
- 问题长度50-100字，有明显的压迫感""",

    "board": """你是公司业务总监，面试P8以上战略产品岗候选人。
职责：生成一道聚焦战略和宏观视野的面试题。
要求：
- 考察候选人对行业趋势、竞争格局的理解
- 追问资源优先级：一个季度只能押一个方向，押哪里？为什么？
- 考察组织协同：怎么拉动业务、技术、数据一起做这件事？
- 考察风险认知：这个方向最大的风险是什么？怎么对冲？
- 考察第二曲线：这个产品三年后的核心价值和现在有什么不同？
- 语气像有丰富阅历的前辈，问题宏观但落地
- 问题长度60-120字，体现战略思维深度"""
}

def build_followup_prompt(round_index, previous_qa, parsed, mode):
    projects = parsed.get("projects", [])
    p0 = projects[0] if projects else {"title": "核心项目", "metrics": [], "summary": ""}
    p1 = projects[1] if len(projects) > 1 else p0
    metrics = "、".join(p0.get("metrics", [])[:3]) or "（未提及具体指标）"

    round_labels = ["开场扫描", "项目深挖", "指标与方案", "推进与复盘", "终局追问"]
    round_hints  = [
        "让候选人90秒介绍最能代表自己的PM项目，考察结构表达和结果输出",
        "深挖问题定义和优先级判断，重点看候选人如何识别核心问题",
        "追问北极星指标、实验设计和方案取舍逻辑",
        "考察项目推进阻力处理、风险判断和复盘深度",
        "考察方法论抽象能力、自我认知和终局思维"
    ]

    history_text = ""
    if previous_qa:
        history_text = "\n\n【已有对话记录】\n"
        for i, qa in enumerate(previous_qa):
            history_text += f"\n第{i+1}轮问题：{qa.get('question','')}\n"
            history_text += f"候选人回答：{qa.get('answer','')[:300]}\n"
            weakest = qa.get('weakest_dim', '')
            score   = qa.get('score', 0)
            if weakest:
                history_text += f"（得分：{score}/10，最弱维度：{weakest}）\n"

    return f"""请为第{round_index+1}轮面试生成追问。

本轮定位：{round_labels[round_index]}
考察方向：{round_hints[round_index]}

候选人项目："{p0['title']}"
项目摘要：{p0['summary'][:200]}
关键指标：{metrics}
第二项目："{p1['title']}"
{history_text}

根据以上信息，生成一道针对性强的面试问题。
如有历史回答，必须基于候选人回答中的具体弱点或模糊点进行追问。
只输出问题本身，不要有任何前缀、解释或标签。"""

def make_questions_static(parsed, mode):
    projects = parsed.get("projects", [])
    main   = projects[0] if projects else {"title": "核心项目", "metrics": [], "focus": []}
    second = projects[1] if len(projects) > 1 else main
    metric0 = main["metrics"][0] if main.get("metrics") else "关键指标提升"
    suffix_map = {
        "pressure": "回答必须给出明确数据口径和归因逻辑，模糊表述将被追问。",
        "board":    "请从业务全局视角作答，突出资源取舍和战略判断。",
        "standard": "尽量结构化表达，按背景→目标→动作→结果组织回答。"
    }
    suffix = suffix_map.get(mode, suffix_map["standard"])
    return [
        {"type": "开场扫描", "scene": "Candidate Profile Check",
         "hint": "用 90 秒讲清你最能代表自己的 PM 项目。",
         "focus": ["结构表达", "个人贡献", "结果输出"], "dynamic": False,
         "text": f"如果只允许你用一个项目代表自己的产品经理能力，你会选哪个？请讲清楚背景、目标、你的角色和结果。{suffix}"},
        {"type": "项目深挖", "scene": "Problem Framing",
         "hint": "重点看你怎么定义问题。", "dynamic": True,
         "focus": ["问题定义", "用户洞察", "优先级判断"],
         "text": "围绕你刚才说的项目，为什么把核心目标定在这个问题上？有很多问题并存时，你是如何判断先打这个点的？"},
        {"type": "指标与方案", "scene": "Metrics & Strategy",
         "hint": "说明北极星指标、实验口径、方案取舍。", "dynamic": True,
         "focus": ["数据意识", "方案设计", "取舍逻辑"],
         "text": f"你提到 {metric0}。请展开说说：这个指标为什么成立、你设计了什么方案、为什么没选别的方案？"},
        {"type": "推进与复盘", "scene": "Execution & Risk",
         "hint": "不能只讲成功，还要讲过程中的风险和修正。", "dynamic": True,
         "focus": ["协同推进", "风险判断", "复盘深度"],
         "text": f"项目推进时最棘手的阻力是什么？以<{second['title']}>为例，说一个真实踩过的坑，以及你是怎么判断要不要调整方案的。"},
        {"type": "终局追问", "scene": "Director Challenge",
         "hint": "考察你的抽象能力和自我认知。", "dynamic": True,
         "focus": ["方法论抽象", "成长意识", "终局表达"],
         "text": "如果我把你拉去做一个全新的 PM 项目，你会复用哪三条原则？另外，说一个你目前还不够成熟的判断习惯。"}
    ]

# ─────────────────────────────────────────
# 语音分析
# ─────────────────────────────────────────

def analyze_speech_metrics(speech_data):
    if not speech_data:
        return None
    duration  = speech_data.get("duration_seconds", 0)
    char_count = speech_data.get("char_count", 0)
    pause_count = speech_data.get("pause_count", 0)
    if duration <= 0 or char_count <= 0:
        return None

    cpm = (char_count / duration) * 60
    if 200 <= cpm <= 280:    fluency = 9.0
    elif 160 <= cpm < 200 or 280 < cpm <= 340: fluency = 7.0
    elif 120 <= cpm < 160 or 340 < cpm <= 400: fluency = 5.0
    else:                    fluency = 3.0

    ppm = (pause_count / duration) * 60
    if ppm > 8:   fluency -= 2.0
    elif ppm > 5: fluency -= 1.0
    fluency = clamp(fluency, 0, 10)

    speed_label = (
        "语速偏慢（<160字/分钟），可能显得不够自信" if cpm < 160 else
        "语速适中（160-280字/分钟），表达流畅"     if cpm <= 280 else
        "语速偏快（>280字/分钟），注意给面试官反应时间"
    )
    return {
        "chars_per_minute": round(cpm, 1),
        "duration_seconds": duration,
        "pause_count": pause_count,
        "fluency_score": round(fluency, 1),
        "speed_label": speed_label,
        "pauses_per_minute": round(ppm, 1)
    }

# ─────────────────────────────────────────
# 评分
# ─────────────────────────────────────────

def build_eval_system_prompt(mode):
    base = "你是一位专业的产品经理面试评委，需要对候选人回答进行多维度评分。严格按 JSON 格式返回，不能有任何额外文字。"
    extras = {
        "standard": "\n评分重点：结构清晰度、数据意识、产品判断、复盘意识、语言是否简洁专业。",
        "pressure": "\n高压模式评分标准更严格：数据口径不清晰扣分；个人贡献不明确扣分；方案取舍逻辑缺失扣分；语言啰嗦或填充词多要体现在speech_quality中；总分标准整体比标准模式严0.5-1分。",
        "board":    "\n总监模式重点考察战略维度：全局视野、商业逻辑、行业趋势理解、管理者汇报风格。缺乏战略思维时judgment维度严格扣分。"
    }
    return base + extras.get(mode, extras["standard"])

def evaluate_with_ai(answer, question, parsed, mode, round_index, speech_data=None):
    system_prompt = build_eval_system_prompt(mode)
    speech_section = ""
    if speech_data:
        speech_section = f"""
【语音输入数据】
原始转写：{speech_data.get('raw_transcript', answer)[:500]}
语速：{speech_data.get('chars_per_minute','未知')} 字/分钟
时长：{speech_data.get('duration_seconds',0):.1f}秒
停顿次数：{speech_data.get('pause_count',0)}次"""

    user_prompt = f"""请对以下面试回答评分。

【题目】{question.get('text','')}
【考察重点】{', '.join(question.get('focus',[]))}
【面试模式】{mode}
【第几轮】第{round_index+1}轮

【候选人回答】
{answer}
{speech_section}
【简历关键词】{', '.join(parsed.get('keywords',[])[:10])}

严格按以下 JSON 格式输出，不含任何其他文字：
{{
  "dimensions": {{
    "structure": <0-10，结构表达>,
    "data": <0-10，数据意识>,
    "judgment": <0-10，产品判断>,
    "retro": <0-10，复盘深度>
  }},
  "speech_quality": {{
    "score": <0-10，综合语速流畅度、遣词造句、逻辑连贯>,
    "comment": "<30字内语言质量点评>"
  }},
  "total": <0-10，四维均值，保留1位小数>,
  "strengths": ["<优势1，15字内>", "<优势2，15字内>"],
  "risks": ["<风险1，20字内>", "<风险2，20字内>"],
  "next": "<本轮最需改进的一点，30字内>",
  "tags": ["<标签1>","<标签2>","<标签3>","<标签4>"],
  "delta": <压力值变化，整数，好回答负值-8到0，差回答正值0到15>,
  "weakest_dim": "<structure|data|judgment|retro>"
}}"""

    response = call_claude(system_prompt, user_prompt, max_tokens=800)
    if not response:
        return None
    try:
        clean = re.sub(r'```json|```', '', response).strip()
        data = json.loads(clean)
        if speech_data:
            sm = analyze_speech_metrics(speech_data)
            if sm:
                data["speech_metrics"] = sm
        return data
    except Exception as e:
        print(f"Parse error: {e}\n{response}")
        return None

def evaluate_rule_based(answer, question, parsed, mode, round_index, speech_data=None):
    chars       = len(re.sub(r'\s+', '', answer))
    has_metric  = bool(re.search(r'\d+(?:\.\d+)?%|\d+(?:\.\d+)?(?:万|千|亿|天|周|月|次)', answer))
    has_owner   = bool(re.search(r'我负责|我主导|我推动|我设计|我定义|我判断|我复盘|我协调|我拆解', answer))
    has_struct  = bool(re.search(r'背景|目标|首先|然后|最后|结果|复盘|当时|因此|所以', answer))
    has_judge   = bool(re.search(r'为什么|因为|权衡|取舍|优先|判断|选择|风险|假设|验证', answer))
    has_user    = bool(re.search(r'用户|客群|新客|老客|画像|访谈|需求|场景', answer))
    has_retro   = bool(re.search(r'复盘|问题|失败|坑|遗憾|下次|重新做|不足|副作用|调整', answer))
    hit         = sum(1 for kw in parsed.get("keywords",[]) if str(kw).lower() in answer.lower())

    structure = clamp(3.2+(2.2 if chars>=90 else 1.5 if chars>=55 else 0.6)+(1.8 if has_struct else 0)+(1.1 if has_owner else 0), 0, 10)
    data      = clamp(2.8+(3.2 if has_metric else 0)+(1.2 if hit>=2 else 0.6 if hit==1 else 0)+(1.8 if re.search(r'基线|口径|对比|提升|下降|增长|留存|转化',answer) else 0), 0, 10)
    judgment  = clamp(3.0+(2.6 if has_judge else 0)+(1.3 if has_user else 0)+(2.0 if re.search(r'方案|实验|分层|灰度|策略|优先级|资源',answer) else 0), 0, 10)
    retro     = clamp(2.2+(3.0 if has_retro else 0)+(2.2 if re.search(r'风险|调整|迭代|验证|副作用',answer) else 0)+(1.3 if round_index>=3 and chars>=80 else 0), 0, 10)
    if mode=="pressure": structure=clamp(structure-.3,0,10); data=clamp(data+.2,0,10)
    if mode=="board":    judgment=clamp(judgment+.5,0,10)
    total = round((structure+data+judgment+retro)/4, 1)

    strengths, risks = [], []
    if structure>=7.5: strengths.append("结构清楚，能让面试官快速抓到背景、动作和结果。")
    if data>=7.5:      strengths.append("数据意识较强，回答里有指标、口径或结果支撑。")
    if judgment>=7.5:  strengths.append("体现了方案选择和业务判断，不只是执行描述。")
    if retro>=7.5:     strengths.append("能说清风险、调整和复盘，像真正做过项目的人。")
    if structure<6.5:  risks.append("表达还偏散，建议下轮先说背景和目标，再讲动作和结果。")
    if data<6.5:       risks.append("缺少可验证的数据口径，容易被追问<这个结果怎么证明>。")
    if judgment<6.5:   risks.append("讲了做法但没讲为什么这么做，产品判断还不够突出。")
    if retro<6.5:      risks.append("复盘不够，建议补充踩坑、调整动作和下一次怎么做。")
    if not strengths: strengths=["信息量够，但还可以更锐利地突出你的个人决策。"]
    if not risks:     risks=["回答完成度不错，下一轮可以再压缩废话、把结论打得更狠。"]

    dim_dict = {"structure": structure, "data": data, "judgment": judgment, "retro": retro}
    weakest  = min(dim_dict, key=dim_dict.get)
    weakest_labels = {"structure":"结构表达","data":"数据意识","judgment":"产品判断","retro":"复盘深度"}

    result = {
        "dimensions": {k: round(v,1) for k,v in dim_dict.items()},
        "total": total,
        "strengths": strengths, "risks": risks,
        "next": f"下一轮重点补强：{weakest_labels[weakest]}",
        "tags": ["数据支撑" if has_metric else "缺指标口径",
                 "个人贡献明确" if has_owner else "职责边界待补",
                 "有判断" if has_judge else "判断偏弱",
                 "有复盘" if has_retro else "复盘偏少"],
        "delta": int(clamp(10-(total-5)*2, -8, 15)),
        "weakest_dim": weakest
    }

    sm = analyze_speech_metrics(speech_data)
    if sm:
        result["speech_metrics"] = sm
        result["speech_quality"] = {"score": sm["fluency_score"], "comment": sm["speed_label"]}
    return result

def evaluate(answer, question, parsed, mode, round_index, speech_data=None):
    if _ai_client:
        result = evaluate_with_ai(answer, question, parsed, mode, round_index, speech_data)
        if result:
            return result
    return evaluate_rule_based(answer, question, parsed, mode, round_index, speech_data)

# ─────────────────────────────────────────
# 报告
# ─────────────────────────────────────────

def verdict_info(avg):
    if avg>=8.3: return {"title":"可直接进入下一轮业务面","badge":"green","hire":"Strong Hire","summary":"你的回答有明显的产品经理质感，既能讲清项目，也能给出判断依据和结果证明。"}
    if avg>=6.6: return {"title":"具备潜力，但表达还可以更狠","badge":"amber","hire":"Need More Evidence","summary":"你有真实项目感，但在指标口径、方案取舍或复盘深度上还有提升空间。"}
    return {"title":"信息量不足，容易在真实面试中被打穿","badge":"red","hire":"Not Yet","summary":"当前回答更像经历描述，还没有完全转化成产品判断和可验证结果。"}

def avg_dimensions(feedbacks):
    if not feedbacks: return {"structure":0,"data":0,"judgment":0,"retro":0}
    keys = ["structure","data","judgment","retro"]
    totals = {k:0.0 for k in keys}
    for fb in feedbacks:
        for k in keys: totals[k] += fb.get("dimensions",{}).get(k,0)
    return {k: round(totals[k]/len(feedbacks),1) for k in keys}

def recommendation(dim, avg):
    weakest = min(dim, key=dim.get)
    tips = {
        "structure": "下一步最值得补的是结构表达。建议任何项目都按<背景-目标-动作-结果-复盘>先打草稿，再压缩成90秒版本。",
        "data": "下一步最值得补的是数据意识。把每个项目补成<基线-目标-动作-结果-归因>格式，会让你从<做过>变成<说得服>。",
        "judgment": "下一步最值得补的是产品判断。每个项目都准备一组<为什么选这个方案，不选另一个>的回答。",
        "retro": "下一步最值得补的是复盘深度。真实面试官很看重你怎么处理失败、风险和副作用。"
    }
    tip = tips.get(weakest, "")
    return (f"你已经具备不错的 PM 面试表达力。{tip} 继续补齐后，表达会更加成熟有力。" if avg>=8 else tip)

# ─────────────────────────────────────────
# API 路由
# ─────────────────────────────────────────

@app.route("/api/parse_resume", methods=["POST"])
def api_parse_resume():
    data = request.get_json(silent=True) or {}
    text = data.get("text","").strip()
    if not text: return jsonify({"error":"简历内容不能为空"}),400
    return jsonify(analyze_resume(text))


@app.route("/api/get_question", methods=["POST"])
def api_get_question():
    """动态生成单道面试题（含基于历史回答的追问）"""
    data        = request.get_json(silent=True) or {}
    parsed      = data.get("parsed", {})
    mode        = data.get("mode", "standard")
    round_index = int(data.get("round_index", 0))
    previous_qa = data.get("previous_qa", [])

    static_qs = make_questions_static(parsed, mode)
    base_q    = static_qs[round_index] if round_index < len(static_qs) else static_qs[-1]

    if round_index == 0 or not _ai_client:
        return jsonify(base_q)

    sys_p  = MODE_SYSTEM_PROMPTS.get(mode, MODE_SYSTEM_PROMPTS["standard"])
    user_p = build_followup_prompt(round_index, previous_qa, parsed, mode)
    ai_text = call_claude(sys_p, user_p, max_tokens=200)
    if ai_text:
        base_q["text"]    = ai_text.strip()
        base_q["dynamic"] = True
    return jsonify(base_q)


@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    data        = request.get_json(silent=True) or {}
    answer      = data.get("answer","").strip()
    question    = data.get("question",{})
    parsed      = data.get("parsed",{})
    mode        = data.get("mode","standard")
    round_index = int(data.get("round_index",0))
    speech_data = data.get("speech_data")
    if not answer or len(answer) < 15:
        return jsonify({"error":"回答太短了，至少讲清楚背景、动作和结果中的两项。"}), 400
    return jsonify(evaluate(answer, question, parsed, mode, round_index, speech_data))


@app.route("/api/report", methods=["POST"])
def api_report():
    data      = request.get_json(silent=True) or {}
    feedbacks = data.get("feedbacks", [])
    mode      = data.get("mode", "standard")
    sid       = data.get("session_id", session_id())
    if not feedbacks: return jsonify({"error":"没有反馈数据"}), 400

    avg      = round(sum(fb["total"] for fb in feedbacks)/len(feedbacks), 1)
    avg_dims = avg_dimensions(feedbacks)
    verdict  = verdict_info(avg)

    sq_scores = [fb["speech_quality"]["score"] for fb in feedbacks if fb.get("speech_quality")]
    speech_avg = round(sum(sq_scores)/len(sq_scores), 1) if sq_scores else None
    speech_summary = None
    if speech_avg is not None:
        if speech_avg>=8:   speech_summary=f"语言表达质量优秀（均分{speech_avg}/10），语速适中、逻辑连贯，面试官好感度高。"
        elif speech_avg>=6: speech_summary=f"语言表达中等（均分{speech_avg}/10），部分回答语速或停顿需优化，建议加强口头表达练习。"
        else:               speech_summary=f"语言表达有较大提升空间（均分{speech_avg}/10），语速不稳定或逻辑跳跃，容易影响面试官判断。"

    return jsonify({
        "session_id": sid, "mode": mode, "total_rounds": len(feedbacks),
        "avg_score": avg, "avg_dimensions": avg_dims, "verdict": verdict,
        "recommendation": recommendation(avg_dims, avg),
        "round_scores": [fb["total"] for fb in feedbacks],
        "speech_avg": speech_avg, "speech_summary": speech_summary
    })


@app.route("/api/session_id", methods=["GET"])
def api_session_id():
    return jsonify({"session_id": session_id()})


@app.route("/")
def index():
    return jsonify({
        "status": "PM Interview Protocol API v2.0",
        "ai_enabled": bool(_ai_client),
        "endpoints": ["POST /api/parse_resume","POST /api/get_question","POST /api/evaluate","POST /api/report","GET /api/session_id"]
    })


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
