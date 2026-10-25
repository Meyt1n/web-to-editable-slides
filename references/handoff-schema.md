# 交接表

`scripts/make_handoff.py` 接受UTF-8 JSON。它校验最小结构与重复页码，输出Markdown供模型继续制作；不会登录网页版、上传文件、调用图像API或自动生成幻灯片。

```json
{
  "project": "示例项目",
  "purpose": "产品介绍",
  "style": {
    "ratio": "16:9",
    "colors": ["#164B3B", "#FF816B"],
    "description": "清新绿色、暖白背景、圆角卡片"
  },
  "imagegen_allowed": true,
  "asset_priority": ["真实照片", "真实界面", "基于实物优化", "概念配图"],
  "conversations": [
    {"role": "大纲", "location": "本地导出的文字或宿主可访问的关联对话", "visibility": "private"}
  ],
  "slides": [
    {
      "id": 1,
      "title": "作品概述",
      "reference": "reference/01_cover.png",
      "key_points": ["实际功能", "使用场景"],
      "assets": ["media/prototype.jpg"],
      "status": "verified",
      "notes": "保留实物外形"
    }
  ]
}
```

必填：非空`project`、非空`slides`，每页有唯一正整数`id`和非空`title`。页码按数值排序；可不连续。`status`可选：

| 值 | 含义 |
|---|---|
| `verified` | 有实际材料支持，仍需核对对应证据 |
| `demo` | 功能或数据演示，不作为效果试验证据 |
| `concept` | 概念说明或生成配图 |
| `planned` | 尚未完成的后续设想 |
| `unspecified` | 信息不足，不能自行改为“已完成” |

`reference`和`assets`是交接记录中的位置，不在生成交接表时复制或验证文件，也不默认授予访问权限。实际制作时逐一解析到用户授权的目录；缺图先用已有资料推进，不虚构替代实物。

`conversations[].visibility`仅记录可见范围，不能控制实际文件权限。私有对话的定位信息只保存在私有工作区；公开示例应使用合成内容，不能只删掉`private`标记后发布。
