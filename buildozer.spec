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
requirements = python3,kivy

# 图标
icon.filename = %(source.dir)s/icon.png

# 竖屏
orientation = portrait
fullscreen = 0

# 目标架构（arm64-v8a 覆盖现代手机，含 Android 16 设备）
android.archs = arm64-v8a, armeabi-v7a

# SDK / NDK
android.api = 35
android.minapi = 24
android.ndk = 25b

# 不需要任何敏感权限
android.permissions =

[buildozer]

log_level = 2
warn_on_root = 1
