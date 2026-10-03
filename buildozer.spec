[app]

# 应用名称（显示在手机桌面上）
title = 计算器

# 包名
package.name = calculator
package.domain = org.kivy.calculator

# 源码
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,ttc,otf
source.exclude_dirs = .venv,bin,.buildozer,.github,.git,__pycache__

# 入口与版本
version = 1.0.0

# 依赖
# 说明：这里把 requests 依赖链的每个包都显式列出，使 p4a 的内部模块列表
# 与这些名字完全一致，便于用环境变量 VERSION_<模块名> 精确覆盖版本。
# 原因见 .github/workflows/build.yml 中的注释：
# p4a 自动解析纯 Python 依赖时会给 pip 传 Android 平台标记，
# 导致 pip 为 charset-normalizer 3.5.2 编造出不存在的 wheel 文件名。
requirements = python3,kivy,certifi,charset-normalizer,idna,requests,urllib3

# 自动接受 Android SDK license
# 注意：必须写在 [app] 段内！buildozer 读取的是 [app].android.accept_sdk_license，
# 写到 [buildozer] 段无效（configparser 不会把带点的键归并到 [app]）。
android.accept_sdk_license = True

# 图标
icon.filename = %(source.dir)s/icon.png

# 竖屏
orientation = portrait
fullscreen = 0

# 目标架构（arm64-v8a 覆盖现代手机，含 Android 16 设备）
android.archs = arm64-v8a

# SDK / NDK
android.api = 35
android.minapi = 24
android.ndk = 25b

# 不需要任何敏感权限
android.permissions =

[buildozer]

log_level = 2
warn_on_root = 0
