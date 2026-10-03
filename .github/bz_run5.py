"""运行 buildozer，并在每次启动 p4a 之前即时给 p4a 源码打补丁。

为什么要在"调用前一刻"打补丁
--------------------------
buildozer 会自己克隆 python-for-android，并且随后执行 git fetch / checkout 到
develop 分支——这会**覆盖掉任何提前打好的补丁**（实测：12:42:00 补丁成功，
12:42:01 buildozer 切分支，工作区被重置）。

因此这里改为拦截 buildozer 启动 p4a 的那一次 subprocess 调用，
在真正调用之前把补丁写进 p4a 源码，保证补丁是最后一步、一定生效。

补丁内容
--------
p4a 用 pip --dry-run --report 解析依赖时，pip 会依据平台标签为某些包编造出
并不存在的 wheel URL（本项目为 charset-normalizer 3.5.2 →
charset_normalizer-3.5.2-cp314-cp314-android_24_arm64_v8a.whl）。p4a 随后拿这个
假 URL 安装，必然失败。改为使用包名+版本号，让 pip 自行解析：
    processed_modules.append(f"{mname}=={mver}")
"""
import os
import shlex
import subprocess
import sys

WORK = os.environ.get("WORK_DIR") or "/home/user/hostcwd"
P4A = os.path.join(WORK, ".buildozer/android/platform/python-for-android")
BUILD_PY = os.path.join(P4A, "pythonforandroid", "build.py")

OLD = 'processed_modules.append(module["download_info"]["url"])'
MARK = '"{}=={}".format(mname, mver)'
NEW = ('processed_modules.append(\n'
       '                    "{}=={}".format(mname, mver)\n'
       '                )')

_state = {"patched": 0, "failed": 0}


def apply_patch():
    """给 p4a 的 build.py 打补丁；返回 True 表示补丁处于生效状态。"""
    if not os.path.isfile(BUILD_PY):
        print("[PATCH] build.py 尚不存在，跳过", flush=True)
        return False
    try:
        src = open(BUILD_PY, encoding="utf-8", errors="replace").read()
    except Exception as e:
        print("[PATCH] 读取失败: %s" % e, flush=True)
        return False

    if MARK in src and OLD not in src:
        print("[PATCH] 已处于补丁状态", flush=True)
        return True

    if OLD not in src:
        print("[PATCH-FAIL] 未找到目标行", flush=True)
        i = src.find("download_info")
        print(repr(src[max(0, i - 250):i + 250]), flush=True)
        _state["failed"] += 1
        return False

    src = src.replace(OLD, NEW, 1)
    try:
        open(BUILD_PY, "w", encoding="utf-8").write(src)
    except Exception as e:
        print("[PATCH] 写入失败: %s" % e, flush=True)
        return False

    chk = open(BUILD_PY, encoding="utf-8", errors="replace").read()
    ok = MARK in chk and OLD not in chk
    print("[PATCH-%s] 补丁%s (第 %d 次)" % ("OK" if ok else "FAIL",
                                          "已生效" if ok else "未生效",
                                          _state["patched"] + 1), flush=True)
    if ok:
        _state["patched"] += 1
    else:
        _state["failed"] += 1
    return ok


_real_call = subprocess.call
_real_check_call = subprocess.check_call
_real_Popen = subprocess.Popen


def _is_p4a(args):
    try:
        s = " ".join(args) if isinstance(args, (list, tuple)) else str(args)
    except Exception:
        return False
    return "pythonforandroid.toolchain" in s


def _pre(args):
    if _is_p4a(args):
        print("[HOOK] 检测到即将调用 p4a，先打补丁", flush=True)
        apply_patch()


def call(*a, **k):
    _pre(a[0] if a else k.get("args"))
    return _real_call(*a, **k)


def check_call(*a, **k):
    _pre(a[0] if a else k.get("args"))
    return _real_check_call(*a, **k)


def Popen(*a, **k):
    _pre(a[0] if a else k.get("args"))
    return _real_Popen(*a, **k)


subprocess.call = call
subprocess.check_call = check_call
subprocess.Popen = Popen

# 先打一次（覆盖 buildozer 已经准备好 p4a 的情况）
apply_patch()

print("[HOOK] 开始运行 buildozer（p4a 调用前会自动补丁）...", flush=True)
from buildozer.scripts.client import main as _bz_main

_bz_main()

print("[HOOK] buildozer 结束。补丁成功次数=%d 失败次数=%d" % (
    _state["patched"], _state["failed"]), flush=True)
