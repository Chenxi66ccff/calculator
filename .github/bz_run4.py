"""补丁 p4a 源码 + 运行 buildozer（单阶段、自校验）。

问题
----
p4a 用 pip --dry-run --report 解析纯 Python 依赖时，pip 会把主机/目标平台标签
塞进文件名，为某些包编造出一个 PyPI 上并不存在的 wheel URL。例如：
    charset_normalizer-3.5.2-cp314-cp314-android_24_arm64_v8a.whl
p4a 随后（build.py 的 run_pymodules_install）把这个假 URL 交给 pip 安装，于是：
    ERROR: ... is not a supported wheel on this platform

本机实测：加不加 --platform 都会伪造（只是平台标签不同），所以"去掉 --platform"无效。

做法
----
把 p4a 源码里构造安装列表的那一行
    processed_modules.append(module["download_info"]["url"])
换成使用包名+版本号（p4a 本来就已解析出 mname / mver）：
    processed_modules.append(f"{mname}=={mver}")
这样 pip 会自行解析，charset-normalizer 正常取到 py3-none-any 通用 wheel。

补丁在导入 p4a 之前写到源文件上，因此 p4a 读到的就是修改后的代码（不涉及 .pyc 缓存）。
替换后会立即回读文件校验，打印 PATCH-OK / PATCH-FAIL。
"""
import os
import subprocess
import sys

WORK = os.environ.get("WORK_DIR") or "/home/user/hostcwd"
P4A = os.path.join(WORK, ".buildozer/android/platform/python-for-android")
P4A_URL = "https://github.com/kivy/python-for-android.git"
BUILD_PY = os.path.join(P4A, "pythonforandroid", "build.py")

OLD = 'processed_modules.append(module["download_info"]["url"])'
NEW = ('processed_modules.append(\n'
       '                    "{}=={}".format(mname, mver)\n'
       '                )')


def ensure_p4a():
    if os.path.isfile(BUILD_PY):
        print("[PATCH] p4a 已存在", flush=True)
        return True
    os.makedirs(os.path.dirname(P4A), exist_ok=True)
    print("[PATCH] 克隆 p4a ...", flush=True)
    try:
        subprocess.check_call(["git", "clone", "--single-branch", P4A_URL, P4A])
    except Exception as e:
        print("[PATCH] 克隆失败: %s" % e, flush=True)
    return os.path.isfile(BUILD_PY)


def patch_build_py():
    if not os.path.isfile(BUILD_PY):
        print("[PATCH-FAIL] 找不到 %s" % BUILD_PY, flush=True)
        return False

    src = open(BUILD_PY, encoding="utf-8", errors="replace").read()

    if '"{}=={}".format(mname, mver)' in src:
        print("[PATCH-SKIP] 已打过补丁", flush=True)
        return True

    if OLD not in src:
        print("[PATCH-FAIL] 未找到目标行。附近内容：", flush=True)
        i = src.find("download_info")
        print(repr(src[max(0, i - 300):i + 300]), flush=True)
        return False

    src = src.replace(OLD, NEW, 1)

    # 去掉已验证失败的旧补丁残留（若之前写过）
    src = src.replace('_url = module["download_info"]["url"]\n', '')
    src = src.replace('_dep = transform_dep_for_pip(dependency)\n', '')

    open(BUILD_PY, "w", encoding="utf-8").write(src)

    # 立即回读校验
    chk = open(BUILD_PY, encoding="utf-8", errors="replace").read()
    ok = '"{}=={}".format(mname, mver)' in chk and OLD not in chk
    print("[PATCH-%s] build.py 补丁%s" % ("OK" if ok else "FAIL", "" if ok else "未生效"), flush=True)
    return ok


ensure_p4a()
ok = patch_build_py()
print("[PATCH] 补丁结果 = %s" % ok, flush=True)

print("[PATCH] 开始运行 buildozer ...", flush=True)
from buildozer.scripts.client import main as _bz_main

_bz_main()
