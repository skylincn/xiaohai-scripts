#!/usr/bin/env python3
"""
MSC 幻天屿图片分析脚本 v2.2
- 模型: glm-4.6v-flash (识图优先)
- 输出: 7维度描述 + B1-B8手办细节 + 中英双语提示词 + GPT Image 2格式
"""

import sys
import json
import base64
import urllib.request
import urllib.error

# ========== 配置 ==========
API_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
API_KEY = "8e7b292043eb499a9dfd2e26db50f7aa.UO1pbaNRNjXN9voD"  # 请替换为有效的API Key
MODEL = "glm-4.6v-flash"
TIMEOUT = 120

ANALYSIS_PROMPT = '''你是一个专业的图片分析模型。请对上传的图片进行**极其详细**的画面描述，并生成可用于文生图的提示词。

## 第一部分：详细画面描述（中文）

请从以下维度进行客观、细致的描述：

1. **主体内容**：画面核心主体是什么？人物/物品/建筑/风景？具体特征（服装、姿态、表情、材质、颜色）
2. **环境背景**：室内还是室外？具体场景（商场/街道/自然/家居）？背景元素（店铺、标识、家具、植被、天空）？
3. **色彩分析**：整体色调（暖色/冷色/中性）？主色调和点缀色？色彩对比关系？
4. **光影效果**：光源方向（顺光/逆光/侧光）？光线强度（强烈/柔和/昏暗）？阴影分布？
5. **构图特点**：拍摄角度（平视/俯视/仰视）？景深（浅景深/全景深）？主体位置（三分法/居中）？
6. **质感与细节**：表面材质（金属/布料/玻璃/石材）？纹理特征？清晰度/锐度？
7. **氛围情绪**：画面传递的情感（活力/宁静/紧张/温馨）？整体风格（写实/梦幻/复古/科幻）？

**进阶细节（检测到手办/人偶/人物时必写）：**
- B1 整体姿态：朝向、站姿/坐姿、肢体动作、双腿姿势
- B2 头部与面部：脸型→发型→眉毛→眼睛→鼻子→嘴巴→耳朵→表情
- B3 上半身服装：款式→颜色→材质→细节（拉链/纽扣/口袋/徽章/领口/袖子）→配饰
- B4 手部细节：手型→手掌姿势→手指状态
- B5 下半身服装：款式→颜色→腰部→裤脚
- B6 鞋履：类型→颜色→鞋带→鞋底
- B7 身体比例：身高观感→体型→肩宽→腰臀比→四肢长度
- B8 材质工艺：PVC/ABS/树脂→光泽度→接缝线→涂装精度→关节→底座

## 第二部分：文生图提示词（中英双语）

### 中文提示词
用自然语言描述画面核心元素，包含：主体、环境，光线、色彩、风格、摄影参数。适合国内文生图平台（如通义万相、文心一格）。至少150字。

### 英文提示词（Stable Diffusion / Midjourney 格式）
使用英文逗号分隔的关键词列表，必须包含：
* Subject: 主体详细描述
* Environment: 场景环境
* Lighting: 光影效果
* Color: 色彩基调
* Camera: 摄影参数
* Style: 画风
* Quality: 画质增强词（highly detailed, 8k, masterpiece, best quality）

### GPT Image 2 格式（5段式）
```
Scene: [时间 + 地点 + 环境描述]
Subject: [主体 + 核心特征]
Important details: [材质 + 光影 + 镜头 + 构图 + 情绪氛围]
Use case: [用途描述]
Constraints: [限制描述]
```

请确保描述足够详细，提示词可以直接用于文生图生成。'''


def analyze_image(img_path: str) -> str:
    """分析图片并返回详细描述 + 文生图提示词"""
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": ANALYSIS_PROMPT}
            ]
        }]
    }

    req = urllib.request.Request(
        API_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        result = json.load(resp)
        return result["choices"][0]["message"]["content"]


def main():
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
    else:
        img_path = input("请输入图片路径: ").strip().strip('"').strip("'")

    if not img_path:
        print("错误：未提供图片路径")
        print("用法: python3 image_analyzer.py <图片路径>")
        sys.exit(1)

    print(f"正在分析图片: {img_path}")
    print("=" * 60)

    try:
        result = analyze_image(img_path)
        print(result)
    except FileNotFoundError:
        print(f"错误：找不到图片文件 '{img_path}'")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"API 请求失败: {e.code} {e.reason}")
        print(f"响应: {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"分析出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
