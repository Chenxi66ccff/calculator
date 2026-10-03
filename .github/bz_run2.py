"""在 buildozer 内部运行：替换 p4a 的 run_pymodules_install。

背景
----
p4a 的 process_python_modules() 会先用一次
    pip install <modules> --dry-run --report ... --platform=android_24_arm64_v8a --python-version=3.14
去"预解析"纯 Python 依赖。pip 在被告知目标平台是 android_xxx 之后，会为某些包
（本项目是 charset-normalizer 3.5.2）编造出一个并不存在的 wheel 文件名：
    charset_normalizer-3.5.2-cp314-cp314-android_24_arm64_v8a.whl
p4a 再把这个假 URL 写进 requirements.txt 并用 pip -r 安装，于是必然失败：
    ERROR: ... is not a supported wheel on this platform.

修法
----
直接跳过这次"带平台标记的预解析"：把 run_pymodules_install 换成我们自己的版本，
它只做两件真正必要的事——
  1. 用 pip 把这些模块装进目标 site-packages（不带 --platform，pip 自行解析；
     charset-normalizer 会正常取到 py3-none-any 通用 wheel）；
  2. 若项目自带 setup.py，则照旧安装。

p4a 在 build_recipes() 里以 `run_pymodules_install(...)` 的形式调用它，因此只要在
buildozer 真正执行前把这个模块属性替换掉即可生效。
"""
import sys
from os import environ
from os.path import abspath, exists, join

import pythonforandroid.build as B
from pythonforandroid.logger import info, info_main, warning, shprint
import sh

_REAL = B.run_pymodules_install


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
        info('[PATCHED] installing python modules (no --platform pre-resolution): {}'.format(
            ', '.join(map(str, modules))))
        shprint(
            pip, 'install', *modules,
            '--target', target,
            '--upgrade', '--ignore-installed', '--no-deps',
            '--disable-pip-version-check', '--only-binary=:all:',
            _env=env,
        )

    # 项目自身的 setup.py（本项目 --ignore-setup-py，通常不会走到这里）
    if not ignore_setup_py and project_dir and exists(join(abspath(project_dir), "setup.py")):
        info('[PATCHED] installing project via setup.py')
        with B.current_directory(project_dir):
            shprint(
                pip, 'install', '.', '--no-deps', '--only-binary=:all:',
                '--target', target, '--disable-pip-version-check', '--upgrade',
                _env=env,
            )

    # 去掉 .so 里的调试符号（p4a 原本也做）
    try:
        arch_env = arch.get_env()
        if not ctx.with_debug_symbols and arch_env.get("STRIP"):
            shprint(sh.find, target, '-iname', '*.so', '-exec',
                    arch_env['STRIP'].split(' ')[0], '--strip-unneeded', '{}', ';',
                    _env=arch_env)
    except Exception:
        pass


B.run_pymodules_install = run_pymodules_install
print("[PATCHED] run_pymodules_install replaced (no --platform pre-resolution)", flush=True)

from buildozer.scripts.client import main as _bz_main

_bz_main()
