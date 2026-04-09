# ============================================================
# 配置文件 — 请勿将此文件提交到 Git 仓库（加入 .gitignore）
# ============================================================

# DeepSeek API Key（填入后启用 AI 动态追问和智能评分）
# 获取地址：https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY = "sk-************************"

# 服务配置
HOST  = "0.0.0.0"
PORT  = 5000
DEBUG = True

# CORS 允许的前端地址（生产环境改为具体域名）
CORS_ORIGINS = ["http://localhost:5000", "http://127.0.0.1:5000", "null", "*"]
