# -*- coding: utf-8 -*-
"""计算器计算引擎：安全的数学表达式解析与求值（递归下降语法分析）。

支持的语法：
    数字、+ - × ÷ ^、括号、隐式乘法（如 2π、3(4)）
    函数：sin cos tan asin acos atan lg ln √
    常量：π e
    后缀：!（阶乘）、%（百分数）
"""
import math


class CalcError(Exception):
    """表达式错误，message 可直接展示给用户。"""


_FUNCS = ("asin", "acos", "atan", "sin", "cos", "tan", "lg", "ln", "sqrt")


class _Parser:
    def __init__(self, text, deg=True):
        self.tokens = self._tokenize(text)
        self.pos = 0
        self.deg = deg

    # ---------- 词法分析 ----------
    @staticmethod
    def _tokenize(s):
        tokens = []
        i = 0
        while i < len(s):
            ch = s[i]
            if ch.isspace():
                i += 1
            elif ch.isdigit() or ch == ".":
                j = i
                while j < len(s) and (s[j].isdigit() or s[j] == "."):
                    j += 1
                num = s[i:j]
                if num == "." or num.count(".") > 1:
                    raise CalcError("格式错误")
                tokens.append(("NUM", float(num)))
                i = j
            elif ch == "π":
                tokens.append(("CONST", math.pi))
                i += 1
            elif ch.isalpha():
                j = i
                while j < len(s) and s[j].isalpha() and s[j] != "π":
                    j += 1
                word = s[i:j]
                if word == "e":
                    tokens.append(("CONST", math.e))
                elif word in _FUNCS:
                    tokens.append(("FUNC", word))
                else:
                    raise CalcError("格式错误")
                i = j
            elif ch == "√":
                tokens.append(("FUNC", "sqrt"))
                i += 1
            elif ch in "+-−":
                tokens.append(("OP", "-" if ch in "-−" else "+"))
                i += 1
            elif ch in "×*":
                tokens.append(("OP", "×"))
                i += 1
            elif ch in "÷/":
                tokens.append(("OP", "÷"))
                i += 1
            elif ch == "^":
                tokens.append(("OP", "^"))
                i += 1
            elif ch == "(":
                tokens.append(("LP", ch))
                i += 1
            elif ch == ")":
                tokens.append(("RP", ch))
                i += 1
            elif ch == "!":
                tokens.append(("FACT", ch))
                i += 1
            elif ch == "%":
                tokens.append(("PCT", ch))
                i += 1
            else:
                raise CalcError("格式错误")
        if not tokens:
            raise CalcError("格式错误")
        return tokens

    # ---------- 工具 ----------
    def _peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return (None, None)

    def _next(self):
        tok = self._peek()
        self.pos += 1
        return tok

    # ---------- 语法分析（边解析边求值） ----------
    def parse(self):
        val = self._expr()
        if self.pos != len(self.tokens):
            raise CalcError("格式错误")
        if isinstance(val, complex) or math.isnan(val) or math.isinf(val):
            raise CalcError("数学错误")
        return val

    def _expr(self):  # expr := term (('+'|'-') term)*
        val = self._term()
        while True:
            t, v = self._peek()
            if t == "OP" and v in "+-":
                self._next()
                rhs = self._term()
                val = val + rhs if v == "+" else val - rhs
            else:
                return val

    def _term(self):  # term := factor (('×'|'÷'|隐式×) factor)*
        val = self._factor()
        while True:
            t, v = self._peek()
            if t == "OP" and v in "×÷":
                self._next()
                rhs = self._factor()
                if v == "×":
                    val = val * rhs
                else:
                    if rhs == 0:
                        raise CalcError("除数不能为0")
                    val = val / rhs
            elif t in ("NUM", "CONST", "FUNC", "LP"):  # 隐式乘法
                val = val * self._factor()
            else:
                return val

    def _factor(self):  # factor := unary ('^' factor)?  右结合
        base = self._unary()
        t, v = self._peek()
        if t == "OP" and v == "^":
            self._next()
            exp = self._factor()
            try:
                val = base ** exp
            except (OverflowError, ZeroDivisionError):
                raise CalcError("数学错误")
            if isinstance(val, complex):
                raise CalcError("数学错误")
            return val
        return base

    def _unary(self):  # unary := ('-'|'+') unary | postfix
        t, v = self._peek()
        if t == "OP" and v == "-":
            self._next()
            return -self._unary()
        if t == "OP" and v == "+":
            self._next()
            return self._unary()
        return self._postfix()

    def _postfix(self):  # postfix := primary ('!'|'%')*
        val = self._primary()
        while True:
            t, _ = self._peek()
            if t == "FACT":
                self._next()
                if val < 0 or val != int(val):
                    raise CalcError("数学错误")
                n = int(val)
                if n > 170:
                    raise CalcError("超出范围")
                val = float(math.factorial(n))
            elif t == "PCT":
                self._next()
                val = val / 100.0
            else:
                return val

    def _primary(self):
        t, v = self._next()
        if t in ("NUM", "CONST"):
            return v
        if t == "LP":
            val = self._expr()
            if self._next()[0] != "RP":
                raise CalcError("括号不匹配")
            return val
        if t == "FUNC":
            if self._next()[0] != "LP":
                raise CalcError("格式错误")
            arg = self._expr()
            if self._next()[0] != "RP":
                raise CalcError("括号不匹配")
            return self._apply_func(v, arg)
        raise CalcError("格式错误")

    def _apply_func(self, name, arg):
        try:
            if name == "sin":
                return math.sin(math.radians(arg) if self.deg else arg)
            if name == "cos":
                return math.cos(math.radians(arg) if self.deg else arg)
            if name == "tan":
                if self.deg:
                    if abs(arg % 180) == 90:
                        raise CalcError("数学错误")
                    return math.tan(math.radians(arg))
                return math.tan(arg)
            if name == "asin":
                r = math.asin(arg)
                return math.degrees(r) if self.deg else r
            if name == "acos":
                r = math.acos(arg)
                return math.degrees(r) if self.deg else r
            if name == "atan":
                r = math.atan(arg)
                return math.degrees(r) if self.deg else r
            if name == "lg":
                if arg <= 0:
                    raise CalcError("数学错误")
                return math.log10(arg)
            if name == "ln":
                if arg <= 0:
                    raise CalcError("数学错误")
                return math.log(arg)
            if name == "sqrt":
                if arg < 0:
                    raise CalcError("数学错误")
                return math.sqrt(arg)
        except ValueError:
            raise CalcError("数学错误")
        raise CalcError("格式错误")


def evaluate(text, deg=True):
    """求值表达式字符串，返回 float；出错抛出 CalcError。"""
    return _Parser(text, deg).parse()


def format_number(x):
    """把计算结果格式化成适合显示的字符串。"""
    if math.isnan(x) or math.isinf(x):
        raise CalcError("数学错误")
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    if x != 0 and (abs(x) >= 1e15 or abs(x) < 1e-9):
        mant, exp = f"{x:.8e}".split("e")
        mant = mant.rstrip("0").rstrip(".")
        return f"{mant}e{int(exp)}"
    return f"{x:.10f}".rstrip("0").rstrip(".")
