"""在 buildozer 内部运行：拦截 p4a 写 requirements.txt 时的伪造 wheel URL。

原理：p4a 用 pip --dry-run --report 解析依赖时会把 Android 平台标记传给 pip，
pip 据此为某些包编造出不存在的 wheel 文件名（charset_normalizer-3.5.2-
cp314-cp314-android_24_arm64_v8a.whl）。p4a 再把该 URL 写进 requirements.txt
并用 pip -r 安装，必然失败。这里在写文件前把它换成普通包名+版本，交给 pip 解析。
"""
import builtins
import sys

_REAL_OPEN = builtins.open


class _ReqWriter:
    def __init__(self, f):
        self._f = f

    def write(self, s):
        try:
            if isinstance(s, str) and "charset_normalizer" in s and "pythonhosted" in s:
                new = "charset-normalizer==3.4.4"
                print("PATCH-URL: %s -> %s" % (s.strip()[:110], new), flush=True)
                s = new + "\n"
        except Exception as e:
            print("PATCH-ERR:", e, flush=True)
        return self._f.write(s)

    def __getattr__(self, item):
        return getattr(self._f, item)


def _patched_open(file, mode="r", *a, **k):
    f = _REAL_OPEN(file, mode, *a, **k)
    try:
        name = str(file)
    except Exception:
        return f
    if name.endswith("requirements.txt") and "w" in str(mode):
        return _ReqWriter(f)
    return f


builtins.open = _patched_open
print("URL 修复钩子已安装，开始调用 buildozer ...", flush=True)

from buildozer.scripts.client import main as _bz_main

_bz_main()
