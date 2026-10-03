#!/bin/bash
# 在 kivy/buildozer 容器内运行，用于诊断 license 处理
echo "===== A. buildozer 位置 ====="
which buildozer
echo "===== B. buildozer 版本 ====="
buildozer --version 2>&1 | head -3
echo
echo "===== C. buildozer 包位置 ====="
python3 -c "import buildozer, os; print(os.path.dirname(buildozer.__file__))"
echo
echo "===== D. 源码中 accept_sdk_license 的出现位置 ====="
BZDIR=$(python3 -c "import buildozer, os; print(os.path.dirname(buildozer.__file__))")
grep -rn "accept_sdk_license" "$BZDIR" || echo "  (源码中未找到 accept_sdk_license)"
echo
echo "===== E. python 解析 buildozer.spec 得到的值 ====="
cd /home/user/hostcwd
python3 <<'PYEOF'
import configparser, os
print("cwd:", os.getcwd())
print("buildozer.spec 存在:", os.path.exists("buildozer.spec"))
c = configparser.ConfigParser()
c.read("buildozer.spec")
print("sections:", c.sections())
for sec in c.sections():
    for k, v in c.items(sec):
        if "license" in k.lower() or "root" in k.lower():
            print("   [%s] %s = %r" % (sec, k, v))
try:
    print("getboolean(app, android.accept_sdk_license, fallback=False) =",
          c.getboolean("app", "android.accept_sdk_license", fallback=False))
except Exception as e:
    print("getboolean 异常:", e)
PYEOF
echo
echo "===== F. spec 第 40-50 行（cat -A 显示行尾） ====="
sed -n '40,50p' buildozer.spec | cat -A
echo
echo "===== G. 镜像里是否已带 licenses 目录 ====="
ls -la /home/user/.buildozer/android/platform/android-sdk/licenses/ 2>&1 | head
echo "--- /home/user/android-sdk? ---"
ls -d /home/user/android-sdk 2>&1
echo
echo "===== H. 镜像里 sdkmanager 的位置 ====="
find /home/user -name "sdkmanager" -type f 2>/dev/null | head
echo
echo "===== I. 尝试用镜像里的 sdkmanager 接受 license ====="
SDKM=$(find /home/user -name "sdkmanager" -type f 2>/dev/null | head -1)
if [ -n "$SDKM" ]; then
  echo "找到 sdkmanager: $SDKM"
  mkdir -p /home/user/.buildozer/android/platform/android-sdk/licenses
  yes | "$SDKM" --sdk_root=/home/user/.buildozer/android/platform/android-sdk --licenses 2>&1 | tail -15
  echo "--- 接受后 licenses 目录 ---"
  ls -la /home/user/.buildozer/android/platform/android-sdk/licenses/ 2>&1
else
  echo "镜像里没有 sdkmanager（需 buildozer 先下载 SDK）"
fi
