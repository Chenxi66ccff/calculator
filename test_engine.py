# -*- coding: utf-8 -*-
"""计算引擎单元测试：python test_engine.py"""
import math
import sys

from calculator_engine import evaluate, format_number, CalcError

PASSED = FAILED = 0


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1, abs(a), abs(b))


def check(expr, expected, deg=True):
    global PASSED, FAILED
    try:
        got = evaluate(expr, deg)
        ok = approx(got, expected)
    except CalcError as e:
        ok, got = False, f"CalcError: {e}"
    if ok:
        PASSED += 1
    else:
        FAILED += 1
        print(f"  FAIL  {expr!r} -> {got!r}，期望 {expected!r}")


def check_error(expr, deg=True):
    global PASSED, FAILED
    try:
        got = evaluate(expr, deg)
        FAILED += 1
        print(f"  FAIL  {expr!r} -> {got!r}，期望报错")
    except CalcError:
        PASSED += 1


def check_format(value, expected):
    global PASSED, FAILED
    got = format_number(value)
    if got == expected:
        PASSED += 1
    else:
        FAILED += 1
        print(f"  FAIL  format({value!r}) -> {got!r}，期望 {expected!r}")


# 四则运算与优先级
check("1+2", 3)
check("7-8", -1)
check("6×7", 42)
check("8÷2", 4)
check("2+3×4", 14)
check("(2+3)×4", 20)
check("10÷4", 2.5)
check("0.1+0.2", 0.3)
check("-5+3", -2)
check("2^10", 1024)
check("2^3^2", 512)          # 右结合
check("(2^3)^2", 64)
check("9^(1/2)", 3)          # / 与 ÷ 等价

# 隐式乘法
check("2π", 2 * math.pi)
check("3(4)", 12)
check("(2)(3)", 6)
check("2sin(30)", 1)

# 函数（角度制）
check("sin(30)", 0.5)
check("cos(60)", 0.5)
check("tan(45)", 1)
check("asin(0.5)", 30)
check("acos(0.5)", 60)
check("atan(1)", 45)
check("lg(1000)", 3)
check("ln(e)", 1)
check("√(16)", 4)
check("√(2)^2", 2)

# 函数（弧度制）
check("sin(π/2)", 1, deg=False)
check("cos(π)", -1, deg=False)
check("tan(π/4)", 1, deg=False)

# 常量
check("π", math.pi)
check("e", math.e)
check("e^2", math.e ** 2)

# 阶乘与百分数
check("5!", 120)
check("0!", 1)
check("3!!", 720)
check("50%", 0.5)
check("200×5%", 10)

# 错误处理
check_error("1÷0")
check_error("√(-1)")
check_error("lg(0)")
check_error("ln(-5)")
check_error("asin(2)")
check_error("tan(90)")
check_error("tan(270)")
check_error("2.5!")
check_error("(-1)!")
check_error("171!")
check_error("1+")
check_error("(1+2")
check_error("1..2")
check_error("abc")
check_error("")
check_error("()")

# 格式化
check_format(3.0, "3")
check_format(0.30000000000000004, "0.3")
check_format(1 / 3, "0.3333333333")
check_format(-2.5, "-2.5")
check_format(1e16, "1e16")
check_format(1.5e-10, "1.5e-10")
check_format(123456789012345.0, "123456789012345")

print(f"\n通过 {PASSED} 项，失败 {FAILED} 项")
sys.exit(1 if FAILED else 0)
