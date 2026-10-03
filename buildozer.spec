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

# 依赖：本项目是纯离线计算器，不需要任何网络功能。
# Kivy 自身会把 requests（以及 charset-normalizer 等）作为依赖带进来，
# p4a 会在安装阶段处理它们。相关细节见 .github/bz_run2.py 的说明。
requirements = python3,kivy

# 自动接受 Android SDK license（必须写在 [app] 段）
android.accept_sdk_license = True

# 图标
icon.filename = %(source.dir)s/icon.png

# 竖屏
orientation = portrait
fullscreen = 0

# 目标架构
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
