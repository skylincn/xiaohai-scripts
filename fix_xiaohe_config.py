#!/usr/bin/env python3
"""
修复小河虾(NAS)的 OpenClaw 模型配置
- 统一使用 openai-completions API 格式
- 使用已验证有效的 API key
- 同步小海虾的模型结构
"""
import json
import shutil
from datetime import datetime

CONFIG_PATH = "/volume2/homes/skyyz/.openclaw/openclaw.json"

# 读取现有配置
with open(CONFIG_PATH, "r") as f:
    data = json.load(f)

# 备份
backup_path = f"{CONFIG_PATH}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy2(CONFIG_PATH, backup_path)
print(f"已备份到: {backup_path}")

# 新的模型配置（统一 openai-completions 格式，使用有效 key）
new_models = {
    "mode": "merge",
    "providers": {
        "kimi": {
            "baseUrl": "https://df.dawnloadai.com:8443/v1",
            "apiKey": "sk-086b7eb6c6e9d10444bc5e64dfd080fc384b7bec97b7b4718f636b292986a8c8",
            "api": "openai-completions",
            "models": [
                {
                    "id": "kimi-k2.6",
                    "name": "Kimi-K2.6（月卡）",
                    "input": ["text", "image"]
                }
            ]
        },
        "minimax": {
            "baseUrl": "https://df.dawnloadai.com:8443/v1",
            "apiKey": "sk-95ea96ea54cfe74387dab8577860573b5b9e1b05e2630b69dafd3ec7ddfa46fc",
            "api": "openai-completions",
            "models": [
                {
                    "id": "MiniMax-M2.7-highspeed",
                    "name": "MiniMax M2.7 Speed"
                }
            ]
        },
        "zhipu": {
            "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
            "apiKey": "8e7b292043eb499a9dfd2e26db50f7aa.UO1pbaNRNjXN9voD",
            "api": "openai-completions",
            "models": [
                {
                    "id": "glm-4v-flash",
                    "name": "GLM-4V-Flash",
                    "api": "openai-completions",
                    "reasoning": False,
                    "input": ["text", "image"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    "contextWindow": 200000,
                    "maxTokens": 8192
                },
                {
                    "id": "glm-4.6v-flash",
                    "name": "GLM-4.6V-Flash",
                    "input": ["text", "image"],
                    "reasoning": False,
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    "contextWindow": 200000,
                    "maxTokens": 8192,
                    "api": "openai-completions"
                }
            ]
        },
        "deepseek": {
            "baseUrl": "https://api.deepseek.com/v1",
            "apiKey": "sk-03400e5b80d14498b62deb7c38d46fe0",
            "api": "openai-completions",
            "models": [
                {
                    "id": "deepseek-chat",
                    "name": "DeepSeek Chat"
                }
            ]
        },
        "apiyi": {
            "baseUrl": "https://imagen.apiyi.com/v1",
            "apiKey": "sk-h3LbjhNvSgv46uFm2d36B651439642E5Bb4bFcC2237aAa02",
            "api": "openai-completions",
            "models": [
                {
                    "id": "gpt-4o-image",
                    "name": "GPT-4o Image (apiyi)"
                },
                {
                    "id": "nano-banana",
                    "name": "Nano Banana (apiyi)"
                },
                {
                    "id": "sora-2-character",
                    "name": "Sora-2-Character (apiyi)"
                }
            ]
        }
    }
}

# 更新配置
data["models"] = new_models

# 保存
with open(CONFIG_PATH, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ 配置已更新")
print("\n变更摘要:")
print("- minimax: anthropic-messages → openai-completions, key 更新为 df/minimax")
print("- deepseek: anthropic-messages → openai-completions")
print("- apiyi: anthropic-messages → openai-completions")
print("- 新增: kimi (df/kimi key, openai-completions)")
print("- 新增: zhipu/GLM (glm-4v-flash, glm-4.6v-flash)")
