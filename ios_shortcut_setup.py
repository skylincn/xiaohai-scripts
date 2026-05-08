#!/usr/bin/env python3
"""
iOS Shortcut Configuration for OpenClaw Image Upload

This script generates a Shortcut configuration that can be imported
or manually created in the iOS Shortcuts app.

Usage:
    python3 /root/.openclaw/workspace/scripts/ios_shortcut_setup.py
    
Then follow the printed instructions to set up the shortcut on iPhone.
"""

import json
import base64
import urllib.parse

SHORTCUT_NAME = "Upload to OpenClaw"
UPLOAD_URL = "https://claw.skylin.cn/image-upload/upload"

def generate_shortcut_json():
    """Generate iOS Shortcut JSON for import"""
    shortcut = {
        "WFWorkflowClientVersion": "1092.0.2",
        "WFWorkflowClientRelease": "4.0",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 4292093695,
            "WFWorkflowIconGlyphNumber": 61456
        },
        "WFWorkflowImportQuestions": [],
        "WFWorkflowTypes": ["NCWidget", "WatchKit"],
        "WFWorkflowInputContentItemClasses": [
            "WFImageContentItem",
            "WFMediaContentItem"
        ],
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.getmyworkflows",
                "WFWorkflowActionParameters": {
                    "WFShowWorkflow": False
                }
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.getvariable",
                "WFWorkflowActionParameters": {
                    "WFVariable": {
                        "Value": {
                            "Type": "ExtensionInput"
                        },
                        "WFSerializationType": "WFTextTokenAttachment"
                    }
                }
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.getimage",
                "WFWorkflowActionParameters": {
                    "WFImage": {
                        "Value": {
                            "attachmentsByRange": {
                                "{0, 1}": {
                                    "Type": "ExtensionInput"
                                }
                            },
                            "string": "￼"
                        },
                        "WFSerializationType": "WFTextTokenString"
                    }
                }
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.encodemedia",
                "WFWorkflowActionParameters": {
                    "WFEncodeMediaActionAudioOnly": False,
                    "WFEncodeMediaActionExportFormat": "JPEG",
                    "WFEncodeMediaActionQuality": 0.8,
                    "WFEncodeMediaActionWidth": 1200,
                    "WFEncodeMediaActionHeight": 1200
                }
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.getvariable",
                "WFWorkflowActionParameters": {
                    "WFVariable": {
                        "Value": {
                            "Type": "ActionOutput",
                            "OutputName": "Encoded Media",
                            "OutputUUID": "encoded-media-uuid"
                        },
                        "WFSerializationType": "WFTextTokenAttachment"
                    }
                }
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {
                    "WFTextActionText": {
                        "Value": {
                            "string": "￼",
                            "attachmentsByRange": {
                                "{0, 1}": {
                                    "Type": "ActionOutput",
                                    "OutputName": "Encoded Media",
                                    "OutputUUID": "encoded-media-uuid"
                                }
                            }
                        },
                        "WFSerializationType": "WFTextTokenString"
                    }
                }
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
                "WFWorkflowActionParameters": {
                    "WFURL": UPLOAD_URL,
                    "WFHTTPMethod": "POST",
                    "WFHTTPHeaders": {
                        "Value": {
                            "WFDictionaryFieldValueItems": []
                        },
                        "WFSerializationType": "WFDictionaryFieldValue"
                    },
                    "WFRequestVariableCreation": True,
                    "WFHTTPBodyType": "Multipart",
                    "WFHTTPBody": {
                        "Value": {
                            "attachmentsByRange": {
                                "{0, 1}": {
                                    "Type": "ActionOutput",
                                    "OutputName": "Encoded Media",
                                    "OutputUUID": "encoded-media-uuid"
                                }
                            },
                            "string": "￼"
                        },
                        "WFSerializationType": "WFTextTokenString"
                    }
                }
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.showresult",
                "WFWorkflowActionParameters": {
                    "Text": {
                        "Value": {
                            "string": "✅ 上传成功！\n请打开 Clawket 发送「分析图片」"
                        },
                        "WFSerializationType": "WFTextTokenString"
                    }
                }
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.openapp",
                "WFWorkflowActionParameters": {
                    "WFAppIdentifier": "com.openclaw.ios",
                    "WFShowOnAppLaunch": False
                }
            }
        ],
        "WFWorkflowName": SHORTCUT_NAME
    }
    return shortcut

def print_manual_setup():
    """Print manual setup instructions"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         iOS 快捷指令配置 - Upload to OpenClaw                    ║
╚══════════════════════════════════════════════════════════════════╝

【方法一：手动创建（推荐，3分钟完成）】

1. 打开 iPhone「快捷指令」App
2. 点击右上角「+」新建快捷指令
3. 点击顶部「...」→ 命名: "Upload to OpenClaw"
4. 点击「添加操作」，按顺序添加以下操作：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

操作 1: 接收图像输入
   → 搜索"接收"
   → 选择「接收来自其他 App 的输入」
   → 类型: 图像
   → 勾选「在共享表单中显示」

操作 2: 压缩图像
   → 搜索"调整"
   → 选择「调整图像大小」
   → 宽度: 1200 像素
   → 高度: 1200 像素（自动保持比例）

操作 3: 转换格式
   → 搜索"转换"
   → 选择「转换图像」
   → 格式: JPEG
   → 质量: 80%

操作 4: 上传到服务器
   → 搜索"获取"
   → 选择「获取 URL 的内容」
   → 方法: POST
   → URL: https://claw.skylin.cn/image-upload/upload
   → 请求体: 表单（Form）
   → 字段:
      • 名称: image
      • 类型: 文件
      • 值: 快捷输入（选择上一个步骤的"转换的图像"）

操作 5: 显示通知
   → 搜索"显示"
   → 选择「显示通知」
   → 标题: ✅ 上传成功
   → 内容: 请打开 Clawket 发送「分析图片」

操作 6: 打开 Clawket（可选）
   → 搜索"打开"
   → 选择「打开 App」
   → 选择 Clawket

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5. 点击「完成」保存

【使用方法】（以后每次只需2秒）

1. 打开「照片」App，选择要上传的图片
2. 点左下角「分享」按钮
3. 在分享菜单中找到并点击「Upload to OpenClaw」
4. 等待1秒，显示"上传成功"通知
5. 自动跳回 Clawket（如果配置了操作6）
6. 在 Clawket 发送: "分析图片"
7. 我自动读取并分析最新上传的图片

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【方法二：URL Scheme 快速跳转】

如果 Clawket 支持 URL Scheme，可以在快捷指令最后添加：

操作: 打开 URL
   → URL: openclaw-ios://chat
   
（需要确认 Clawket 的实际 URL Scheme 是什么）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【常见问题】

Q: 分享菜单里找不到快捷指令？
A: 首次使用需要在分享菜单底部点"编辑操作"→ 添加快捷指令

Q: 上传失败？
A: 检查网络连接，或图片是否过大（超过20MB）

Q: 如何同时上传多张图？
A: 快捷指令支持接收多张图像，会自动依次上传

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

def generate_shortcut_link():
    """Generate a shortcut link if possible"""
    shortcut_json = generate_shortcut_json()
    json_str = json.dumps(shortcut_json, ensure_ascii=False)
    
    # Try to create a data URL (limited support)
    encoded = base64.b64encode(json_str.encode()).decode()
    
    print(f"""
【快捷指令 JSON（供开发者使用）】

如果需要导入快捷指令，可以使用以下 JSON：

文件名: Upload to OpenClaw.shortcut

此 JSON 可以转换为 .shortcut 文件通过 iMazing 等工具导入。

或访问快捷指令社区网站创建分享链接。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

上传地址: {UPLOAD_URL}
压缩后保存: /root/.openclaw/media/compressed/
""")

if __name__ == '__main__':
    print_manual_setup()
    generate_shortcut_link()
    
    # Save shortcut JSON to file
    shortcut = generate_shortcut_json()
    output_path = "/root/.openclaw/workspace/Upload_to_OpenClaw.shortcut.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(shortcut, f, ensure_ascii=False, indent=2)
    print(f"\n快捷指令 JSON 已保存到: {output_path}")
    print("可以通过 iMazing 等工具导入到 iPhone")
