# -*- coding: utf-8 -*-
"""AI 接口密钥配置模板。

使用方法：把本文件复制为同目录下的 config_local.py，填入自己的密钥即可。
  copy config_local.example.py config_local.py      （Windows）
  cp   config_local.example.py config_local.py      （macOS / Linux）

不配置也能运行：作品会完整浏览，仅纹样生成与 AI 换装降级为本地演示模式。

也可以用环境变量代替本文件：
  Windows      set SILICONFLOW_API_KEY=sk-xxxx
  macOS/Linux  export SILICONFLOW_API_KEY=sk-xxxx
"""

# 硅基流动（图像编辑：纹样补全、AI 换装）
# 获取地址：https://cloud.siliconflow.cn/
SILICONFLOW_API_KEY = ""

# DeepSeek（文本生成：纹样工艺解读）
# 获取地址：https://platform.deepseek.com/
DEEPSEEK_API_KEY = ""