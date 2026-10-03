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
# 说明：
#   kivy 会带出 requests 依赖链（requests -> charset-normalizer 等），
#   python-for-android 默认自动解析这些纯 Python 包，但它向 pip 传入了
#   Android 平台标记（--platform=android_24_arm64_v8a --python-version=3.14），
#   导致 pip 在 --report 里为 charset-normalizer 3.5.2 编造出一个并不存在的
#   文件名 charset_normalizer-3.5.2-cp314-cp314-android_24_arm64_v8a.whl，
#   p4a 再拿这个假 URL 去安装，必然失败。
#   实测：charset-normalizer 3.4.4 及更早版本会正常解析为 py3-none-any.whl。
#   故显式钉住整条依赖链，避免自动解析选到有问题的版本。
requirements = python3,kivy,charset-normalizer==3.4.4,requests,urllib3,idna,certifi

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
