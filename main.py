# -*- coding: utf-8 -*-
"""计算器 —— 仿参考图风格的科学计算器（Kivy）。

运行：python main.py
打包：buildozer android debug（见 buildozer.spec）
"""
import os

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput

from calculator_engine import CalcError, evaluate, format_number

# ---------------------------------------------------------------- 基础配置

BG = (0.957, 0.957, 0.965, 1)        # 页面浅灰底
WHITE = (1, 1, 1, 1)                 # 按钮白底
DARK = (0.16, 0.16, 0.18, 1)         # 深色文字
GRAY = (0.60, 0.60, 0.65, 1)         # 次要文字
ORANGE = (0.98, 0.35, 0.05, 1)       # 主题橙


def _find_cjk_font():
    """在各平台寻找支持中文/数学符号的系统字体。"""
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",                       # Windows 微软雅黑
        "/system/fonts/NotoSansCJK-Regular.ttc",            # Android 原生
        "/system/fonts/NotoSansSC-Regular.otf",
        "/system/fonts/DroidSansFallbackFull.ttf",          # 旧 Android
        "/system/fonts/MiSans-Regular.ttf",                 # MIUI
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


FONT = _find_cjk_font()


def _font_kwargs(**extra):
    kw = {"font_name": FONT} if FONT else {}
    kw.update(extra)
    return kw


# ---------------------------------------------------------------- 通用控件

class RoundedButton(Button):
    """白色圆角按钮，文字颜色可配。"""

    bg = ListProperty(WHITE)
    radius = ListProperty([dp(16)])

    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = kw.get("color", DARK)
        with self.canvas.before:
            self._bg_color = Color(*self.bg)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size,
                                             radius=self.radius)
        self.bind(pos=self._sync, size=self._sync, bg=self._recolor)

    def _sync(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _recolor(self, *_):
        self._bg_color.rgba = self.bg


class IconButton(Button):
    """用 canvas 绘制的图标按钮：expand（双向箭头）/ back（退格）/ dots（菜单）。"""

    kind = StringProperty("expand")
    icon_color = ListProperty(ORANGE)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        c = self.canvas
        c.after.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        r, g, b, a = self.icon_color
        with c.after:
            Color(r, g, b, a)
            if self.kind == "expand":
                # 左上-右下 双向箭头（切换键盘）
                for dx, dy in ((1, 1), (-1, -1)):
                    tipx, tipy = x + w * (0.68 if dx > 0 else 0.32), \
                                 y + h * (0.68 if dy > 0 else 0.32)
                    Line(points=[x + w / 2, y + h / 2, tipx, tipy], width=dp(1.6))
                    Line(points=[tipx - dx * w * 0.13, tipy, tipx, tipy,
                                 tipx, tipy - dy * h * 0.13], width=dp(1.6),
                         cap="round", joint="round")
            elif self.kind == "back":
                bx, by = x + w * 0.18, y + h * 0.30
                bw, bh = w * 0.64, h * 0.40
                Line(rounded_rectangle=(bx, by, bw, bh, dp(5)), width=dp(1.5))
                cx, cy, s = bx + bw / 2, by + bh / 2, bw * 0.13
                Line(points=[cx - s, cy - s, cx + s, cy + s], width=dp(1.5))
                Line(points=[cx - s, cy + s, cx + s, cy - s], width=dp(1.5))
            elif self.kind == "dots":
                cx = x + w / 2
                for i in (-1, 0, 1):
                    Ellipse(pos=(cx - dp(2), y + h / 2 + i * h * 0.18 - dp(2)),
                            size=(dp(4), dp(4)))


# ---------------------------------------------------------------- 显示区

class Display(BoxLayout):
    """表达式 + 实时预览 + 橙色光标。"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=(dp(20), 0), **kw)
        self.preview = Label(text="", size_hint_y=0.35, halign="right",
                             valign="bottom", color=GRAY, font_size=sp(20),
                             **_font_kwargs())
        self.main = Label(text="0", size_hint_y=0.65, halign="right",
                          valign="center", color=DARK, font_size=sp(44),
                          **_font_kwargs())
        for lbl in (self.preview, self.main):
            lbl.bind(size=self._sync_text_size)
        self.add_widget(self.preview)
        self.add_widget(self.main)
        self.main.bind(text=self._restyle, size=self._restyle,
                       pos=self._restyle, texture_size=self._restyle)
        self._cursor_gap = dp(16)

    def _sync_text_size(self, lbl, *_):
        lbl.text_size = (lbl.width - self._cursor_gap, None)

    def _restyle(self, *_):
        # 字体随长度收缩
        n = len(self.main.text)
        self.main.font_size = sp(44) if n <= 9 else sp(max(22, 44 * 9.0 / n))
        # 光标：紧贴右对齐文本末尾
        c = self.main.canvas.after
        c.clear()
        with c:
            Color(*ORANGE)
            tw = min(self.main.texture_size[0],
                     self.main.width - self._cursor_gap)
            x = self.main.right - tw + dp(6) if tw < self.main.width - self._cursor_gap \
                else self.main.right - self._cursor_gap + dp(6)
            Rectangle(pos=(min(x, self.main.right - dp(4)),
                           self.main.y + self.main.height * 0.22),
                      size=(dp(2), self.main.height * 0.56))


# ---------------------------------------------------------------- 换算页

_UNIT_TABLES = {
    "长度": {"毫米": 0.001, "厘米": 0.01, "米": 1.0, "千米": 1000.0,
             "英寸": 0.0254, "英尺": 0.3048, "英里": 1609.344},
    "质量": {"克": 0.001, "千克": 1.0, "吨": 1000.0,
             "磅": 0.45359237, "盎司": 0.028349523125},
    "温度": {"摄氏度": None, "华氏度": None, "开尔文": None},
}


class _WhiteSpinnerOption(SpinnerOption):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_color = WHITE
        self.color = DARK
        if FONT:
            self.font_name = FONT


class ConverterPage(BoxLayout):
    """简单单位换算：长度 / 质量 / 温度。"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=dp(16), spacing=dp(14), **kw)
        self.category = "长度"

        # 分类切换
        cats = GridLayout(cols=3, spacing=dp(10), size_hint_y=None, height=dp(48))
        self._cat_btns = {}
        for name in _UNIT_TABLES:
            btn = RoundedButton(text=name, font_size=sp(16), **_font_kwargs())
            btn.bind(on_release=lambda _b, n=name: self._set_category(n))
            self._cat_btns[name] = btn
            cats.add_widget(btn)
        self.add_widget(cats)

        # 输入
        self.input = TextInput(text="1", multiline=False, halign="right",
                               font_size=sp(26), size_hint_y=None, height=dp(60),
                               padding=(dp(14), dp(14)), background_normal="",
                               background_active="", background_color=WHITE,
                               foreground_color=DARK, cursor_color=ORANGE,
                               input_filter=self._filter_number, **_font_kwargs())
        self.input.bind(text=lambda *_: self._update())
        self.add_widget(self.input)

        # 单位选择
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
        self.from_spin = Spinner(color=DARK, background_normal="",
                                 background_color=WHITE, option_cls=_WhiteSpinnerOption,
                                 **_font_kwargs())
        self.to_spin = Spinner(color=DARK, background_normal="",
                               background_color=WHITE, option_cls=_WhiteSpinnerOption,
                               **_font_kwargs())
        arrow = Label(text="→", size_hint_x=None, width=dp(36), color=GRAY,
                      font_size=sp(20), **_font_kwargs())
        self.from_spin.bind(text=lambda *_: self._update())
        self.to_spin.bind(text=lambda *_: self._update())
        row.add_widget(self.from_spin)
        row.add_widget(arrow)
        row.add_widget(self.to_spin)
        self.add_widget(row)

        # 结果
        self.result = Label(text="", halign="right", valign="top", color=DARK,
                            font_size=sp(32), **_font_kwargs())
        self.result.bind(size=lambda l, *_: setattr(l, "text_size", l.size))
        self.add_widget(self.result)

        self._set_category("长度")

    @staticmethod
    def _filter_number(text, from_undo):
        return "".join(ch for ch in text if ch.isdigit() or ch in ".-")

    def _set_category(self, name):
        self.category = name
        units = list(_UNIT_TABLES[name])
        self.from_spin.values = units
        self.to_spin.values = units
        self.from_spin.text = units[0]
        self.to_spin.text = units[1] if len(units) > 1 else units[0]
        for n, btn in self._cat_btns.items():
            btn.color = ORANGE if n == name else DARK
        self._update()

    def _update(self):
        try:
            value = float(self.input.text) if self.input.text not in ("", "-", ".") else 0.0
        except ValueError:
            self.result.text = ""
            return
        f, t = self.from_spin.text, self.to_spin.text
        table = _UNIT_TABLES[self.category]
        if f not in table or t not in table:
            self.result.text = ""
            return
        if self.category == "温度":
            celsius = {"摄氏度": value,
                       "华氏度": (value - 32) * 5 / 9,
                       "开尔文": value - 273.15}[f]
            out = {"摄氏度": celsius,
                   "华氏度": celsius * 9 / 5 + 32,
                   "开尔文": celsius + 273.15}[t]
        else:
            out = value * table[f] / table[t]
        self.result.text = format_number(out)


# ---------------------------------------------------------------- 主界面

_SCI_ROWS = [
    ["2nd", "deg", "sin", "cos", "tan"],
    ["x^y", "lg", "ln", "(", ")"],
    ["√x", "AC", "back", "%", "÷"],
    ["x!", "7", "8", "9", "×"],
    ["1/x", "4", "5", "6", "−"],
    ["π", "1", "2", "3", "+"],
    ["expand", "e", "0", ".", "="],
]

_BASIC_ROWS = [
    ["AC", "back", "%", "÷"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "−"],
    ["1", "2", "3", "+"],
    ["expand", "0", ".", "="],
]

_ORANGE_KEYS = {"AC", "back", "%", "÷", "×", "−", "+"}

# 2nd 模式下的替代显示与插入内容
_SECOND_LABELS = {"sin": "asin", "cos": "acos", "tan": "atan",
                  "lg": "10^x", "ln": "e^x", "√x": "x²"}
_SECOND_INSERT = {"sin": "asin(", "cos": "acos(", "tan": "atan(",
                  "lg": "10^", "ln": "e^", "√x": "^2"}

_INSERT = {"sin": "sin(", "cos": "cos(", "tan": "tan(", "lg": "lg(", "ln": "ln(",
           "√x": "√(", "x^y": "^", "x!": "!", "π": "π", "e": "e"}

# 退格时整体删除的片段（长的在前）
_BACK_CHUNKS = sorted(["asin(", "acos(", "atan(", "sin(", "cos(", "tan(",
                       "lg(", "ln(", "√(", "10^", "e^", "1÷("],
                      key=len, reverse=True)


class CalculatorRoot(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        self.expr = ""
        self.second = False
        self.deg = True
        self.basic_mode = False
        self.just_evaluated = False
        self.history = []

        self._build_topbar()
        self.pages = BoxLayout()
        self.add_widget(self.pages)

        self.calc_page = self._build_calc_page()
        self.converter_page = ConverterPage()
        self.show_page("calc")

    # ---------- 顶栏 ----------
    def _build_topbar(self):
        bar = BoxLayout(size_hint_y=None, height=dp(56), padding=(dp(6), 0))

        left = IconButton(kind="expand", size_hint_x=None, width=dp(52),
                          icon_color=DARK)
        left.bind(on_release=lambda *_: self.toggle_keypad())
        bar.add_widget(left)

        tabs = BoxLayout()
        self.tab_calc = Button(text="计算", background_normal="", background_color=(0, 0, 0, 0),
                               color=DARK, font_size=sp(17), bold=True, **_font_kwargs())
        self.tab_conv = Button(text="换算", background_normal="", background_color=(0, 0, 0, 0),
                               color=GRAY, font_size=sp(17), **_font_kwargs())
        self.tab_calc.bind(on_release=lambda *_: self.show_page("calc"))
        self.tab_conv.bind(on_release=lambda *_: self.show_page("conv"))
        tabs.add_widget(self.tab_calc)
        tabs.add_widget(self.tab_conv)
        bar.add_widget(tabs)

        menu = IconButton(kind="dots", size_hint_x=None, width=dp(52),
                          icon_color=DARK)
        menu.bind(on_release=lambda *_: self.show_history())
        bar.add_widget(menu)

        self.add_widget(bar)

    def show_page(self, which):
        self.pages.clear_widgets()
        if which == "calc":
            self.pages.add_widget(self.calc_page)
            self.tab_calc.color, self.tab_calc.bold = DARK, True
            self.tab_conv.color, self.tab_conv.bold = GRAY, False
        else:
            self.pages.add_widget(self.converter_page)
            self.tab_calc.color, self.tab_calc.bold = GRAY, False
            self.tab_conv.color, self.tab_conv.bold = DARK, True

    # ---------- 计算页 ----------
    def _build_calc_page(self):
        page = BoxLayout(orientation="vertical")
        self.display = Display(size_hint_y=0.30)
        page.add_widget(self.display)
        self.keypad = GridLayout(cols=5, spacing=dp(10),
                                 padding=(dp(14), dp(4), dp(14), dp(14)))
        page.add_widget(self.keypad)
        self._fill_keypad()
        return page

    def _fill_keypad(self):
        self.keypad.clear_widgets()
        rows = _BASIC_ROWS if self.basic_mode else _SCI_ROWS
        self.keypad.cols = 4 if self.basic_mode else 5
        self._sci_buttons = {}
        for row in rows:
            for key in row:
                self.keypad.add_widget(self._make_key(key))

    def _make_key(self, key):
        if key == "back":
            btn = IconButton(kind="back", icon_color=ORANGE)
        elif key == "expand":
            btn = IconButton(kind="expand", icon_color=ORANGE)
        else:
            label = key
            if self.second and key in _SECOND_LABELS:
                label = _SECOND_LABELS[key]
            if key == "deg":
                label = "deg" if self.deg else "rad"
            color = ORANGE if key in _ORANGE_KEYS else DARK
            if key == "=":
                btn = RoundedButton(text=label, color=WHITE, bg=ORANGE,
                                    font_size=sp(24), **_font_kwargs())
            else:
                btn = RoundedButton(text=label, color=color, font_size=sp(21),
                                    **_font_kwargs())
            self._sci_buttons[key] = btn
        btn.bind(on_release=lambda _b, k=key: self.on_key(k))
        return btn

    def toggle_keypad(self):
        self.basic_mode = not self.basic_mode
        self._fill_keypad()

    def _refresh_second(self):
        for key, label in _SECOND_LABELS.items():
            btn = self._sci_buttons.get(key)
            if btn is not None:
                btn.text = label if self.second else key
        btn = self._sci_buttons.get("2nd")
        if btn is not None:
            btn.color = WHITE if self.second else DARK
            btn.bg = ORANGE if self.second else WHITE

    # ---------- 按键逻辑 ----------
    def on_key(self, key):
        if key == "2nd":
            self.second = not self.second
            self._refresh_second()
            return
        if key == "deg":
            self.deg = not self.deg
            self._sci_buttons["deg"].text = "deg" if self.deg else "rad"
            return
        if key == "expand":
            self.toggle_keypad()
            return
        if key == "AC":
            self.expr = ""
            self.just_evaluated = False
            self._sync_display()
            return
        if key == "back":
            self._backspace()
            self._sync_display()
            return
        if key == "=":
            self._equals()
            return

        # 需要插入内容的键
        if self.second and key in _SECOND_INSERT:
            text = _SECOND_INSERT[key]
            self.second = False
            self._refresh_second()
        elif key == "1/x":
            self.expr = ("1÷(" + self.expr + ")") if self.expr else "1÷("
            self._sync_display()
            return
        else:
            text = _INSERT.get(key, key)

        if self.just_evaluated:
            result = self.display.main.text
            if text[0].isdigit() or text in (".", "(", "π", "e") or text.endswith("("):
                self.expr = ""          # 数字/函数 → 开始新算式
            else:
                self.expr = result      # 运算符 → 接着上次的答案算
            self.just_evaluated = False

        # 连续两个运算符时替换旧的
        if text in "+−×÷^" and self.expr and self.expr[-1] in "+−×÷^":
            self.expr = self.expr[:-1] + text
        else:
            self.expr += text
        self._sync_display()

    def _backspace(self):
        if self.just_evaluated:
            self.just_evaluated = False
            self.expr = ""
            return
        for chunk in _BACK_CHUNKS:
            if self.expr.endswith(chunk):
                self.expr = self.expr[:-len(chunk)]
                return
        self.expr = self.expr[:-1]

    def _equals(self):
        if not self.expr or self.just_evaluated:
            return
        try:
            result = format_number(evaluate(self.expr, self.deg))
        except CalcError as e:
            self.display.preview.text = str(e)
            return
        self.history.append((self.expr, result))
        self.display.preview.text = self.expr + " ="
        self.display.main.text = result
        self.just_evaluated = True

    def _sync_display(self):
        self.display.main.text = self.expr if self.expr else "0"
        if self.expr:
            try:
                self.display.preview.text = "= " + format_number(
                    evaluate(self.expr, self.deg))
            except CalcError:
                self.display.preview.text = ""
        else:
            self.display.preview.text = ""

    # ---------- 历史记录 ----------
    def show_history(self):
        body = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        scroll = ScrollView()
        lst = GridLayout(cols=1, size_hint_y=None, spacing=dp(4),
                         padding=(dp(4), dp(4)))
        lst.bind(minimum_height=lst.setter("height"))
        popup = Popup(title="历史记录", content=body, size_hint=(0.9, 0.75),
                      title_color=DARK, background="", separator_color=ORANGE,
                      **_font_kwargs())
        if not self.history:
            lst.add_widget(Label(text="暂无记录", color=GRAY, size_hint_y=None,
                                 height=dp(40), **_font_kwargs()))
        for expr, result in reversed(self.history[-50:]):
            item = Button(text=f"{expr} = {result}", halign="right",
                          background_normal="", background_color=(0, 0, 0, 0),
                          color=DARK, size_hint_y=None, height=dp(44),
                          **_font_kwargs())
            item.bind(on_release=lambda _b, r=result: self._recall(r, popup))
            lst.add_widget(item)
        scroll.add_widget(lst)
        clear = RoundedButton(text="清空历史", color=ORANGE, size_hint_y=None,
                              height=dp(44), **_font_kwargs())
        clear.bind(on_release=lambda *_: (self.history.clear(), popup.dismiss()))
        body.add_widget(scroll)
        body.add_widget(clear)
        popup.open()

    def _recall(self, result, popup):
        self.expr = result
        self.just_evaluated = False
        self._sync_display()
        popup.dismiss()
        self.show_page("calc")


# ---------------------------------------------------------------- App

class CalculatorApp(App):
    title = "计算器"

    def build(self):
        Window.clearcolor = BG
        if os.name == "nt":  # 桌面预览窗口尺寸
            Window.size = (380, 780)
        return CalculatorRoot()


if __name__ == "__main__":
    CalculatorApp().run()
