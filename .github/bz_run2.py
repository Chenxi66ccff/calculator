"""在 buildozer 内部运行：替换 p4a 的 run_pymodules_install（跳过带 --platform 的预解析）。

背景
----
p4a 的 process_python_modules() 会先做一次带 Android 平台标记的 pip 预解析：
    pip install <modules> --dry-run --report ... --platform=android_24_arm64_v8a --python-version=3.14
pip 被告知目标是 android_xxx 平台后，会为某些包（本项目是 charset-normalizer 3.5.2）
编造一个 PyPI 上并不存在的 wheel 文件名：
    charset_normalizer-3.5.2-cp314-cp314-android_24_arm64_v8a.whl
p4a 再把这个假 URL 写进 requirements.txt 并用 pip -r 安装，于是失败：
    ERROR: ... is not a supported wheel on this platform.

修法
----
跳过这次"带平台标记的预解析"：把 run_pymodules_install 换成我们自己的版本，
它只做真正必要的事——用 pip（不带 --platform）把模块装进目标 site-packages，
pip 会正常解析并取到 charset-normalizer 的 py3-none-any 通用 wheel。

注意：p4a 是 buildozer 运行过程中才克隆的，所以这里需要先把它取下来再导入。
"""
import os
import subprocess
import sys

# 镜像里的依赖（sh、pexpect 等）装在 /home/user/.venv，
# 而 --entrypoint python3 用的是系统 Python。若不在 venv 里，就自我重启到 venv。
_VENV_PY = "/home/user/.venv/bin/python3"
if os.path.isfile(_VENV_PY) and os.path.realpath(sys.executable) != os.path.realpath(_VENV_PY):
    print("[PATCH] re-exec into venv: %s" % _VENV_PY, flush=True)
    os.execv(_VENV_PY, [_VENV_PY, os.path.abspath(__file__)] + sys.argv[1:])

P4A_DIR = "/home/user/hostcwd/.buildozer/android/platform/python-for-android"
P4A_URL = "https://github.com/kivy/python-for-android.git"


def ensure_p4a():
    if os.path.isdir(os.path.join(P4A_DIR, "pythonforandroid")):
        return True
    os.makedirs(os.path.dirname(P4A_DIR), exist_ok=True)
    print("[PATCH] pre-cloning python-for-android ...", flush=True)
    try:
        subprocess.check_call(
            ["git", "clone", "--single-branch", "--depth", "1", P4A_URL, P4A_DIR]
        )
    except Exception as e:
        print("[PATCH] git clone failed: %s" % e, flush=True)
    return os.path.isdir(os.path.join(P4A_DIR, "pythonforandroid"))


ok = ensure_p4a()
print("[PATCH] p4a present:", ok, flush=True)
if P4A_DIR not in sys.path:
    sys.path.insert(0, P4A_DIR)

from os import environ
from os.path import abspath, exists, join

import sh
import pythonforandroid.build as B
from pythonforandroid.logger import info, shprint


def run_pymodules_install(ctx, arch, modules, project_dir=None, ignore_setup_py=False):
    info('*** [PATCHED] PYTHON PACKAGE / PROJECT INSTALL STAGE FOR ARCH: {} ***'.format(arch))

    modules = [m for m in (modules or [])]

    try:
        host_recipe = B.Recipe.get_recipe("hostpython3", ctx)
        pip = host_recipe.pip
    except Exception:
        pip = sh.Command("pip")

    env = environ.copy()
    target = ctx.get_site_packages_dir(arch)

    if not modules:
        info('[PATCHED] no python modules to install')
    else:
        info('[PATCHED] installing (no --platform pre-resolution): {}'.format(
            ', '.join(map(str, modules))))
        shprint(
            pip, 'install', *modules,
            '--target', target,
            '--upgrade', '--ignore-installed', '--no-deps',
            '--disable-pip-version-check', '--only-binary=:all:',
            _env=env,
        )

    if not ignore_setup_py and project_dir and exists(join(abspath(project_dir), "setup.py")):
        info('[PATCHED] installing project via setup.py')
        with B.current_directory(project_dir):
            shprint(
                pip, 'install', '.', '--no-deps', '--only-binary=:all:',
                '--target', target, '--disable-pip-version-check', '--upgrade',
                _env=env,
            )

    try:
        arch_env = arch.get_env()
        if not ctx.with_debug_symbols and arch_env.get("STRIP"):
            shprint(sh.find, target, '-iname', '*.so', '-exec',
                    arch_env['STRIP'].split(' ')[0], '--strip-unneeded', '{}', ';',
                    _env=arch_env)
    except Exception:
        pass


B.run_pymodules_install = run_pymodules_install
print("[PATCHED] run_pymodules_install replaced", flush=True)

from buildozer.scripts.client import main as _bz_main

_bz_main()
