from dotenv import load_dotenv
import os

# 自动加载当前目录下的 .env 文件
load_dotenv()



# 环境变量（可在 .env 中配置）
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.siliconflow.cn/v1/chat/completions")
LLM_API_KEY = os.getenv("SILICONFLOW_API_TOKEN")
LLM_DEFAULT_MODEL = os.getenv("LLM_DEFAULT_MODEL", "deepseek-ai/DeepSeek-V3")

# 请求超时/重试
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_BACKOFF_BASE = float(os.getenv("LLM_BACKOFF_BASE", "0.6"))
