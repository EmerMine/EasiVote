import ctypes
import platform
import sys
from functools import partial
from tkinter import *
from tkinter import messagebox as msgbox
from tkinter.ttk import *


def enable_high_dpi():
    """
    跨平台启用高 DPI 支持：
    - Windows：优先使用 Per-Monitor V2，回退到 System DPI Aware，
               并设置 Tk 的 TkScale DPI 感知。
    - macOS / Linux：Tk 默认支持 Retina / Wayland/X11 HiDPI，这里保留调用点
                     以便后续扩展，并尝试启用 Tk 自带的缩放感知。
    """
    system = platform.system()

    if system == "Windows":
        try:
            # Windows 10 1703+ : Per-Monitor V2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                # 旧版 Windows：System DPI Aware
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except (AttributeError, OSError):
                try:
                    # Win7 / 更旧回退
                    ctypes.windll.user32.SetProcessDPIAware()
                except (AttributeError, OSError):
                    pass  # 无法设置则忽略，保持兼容

    # Tk 8.6 以上支持的 DPI 缩放提示（macOS 上也有效）
    if sys.version_info >= (3, 9):
        try:
            from tkinter import _tkinter
            _tkinter.set_interp_need(True)  # type: ignore[attr-defined]
        except Exception:
            pass


enable_high_dpi()

root = Tk()
try:
    # 让 Tk 自己按 DPI 缩放（部分 Tk 版本支持）
    root.tk.call("tk", "scaling", "-displayof", root.winfo_screen(), "1.0")
except TclError:
    try:
        root.tk.call("tk", "scaling", root.winfo_fpixels("1i") / 72.0)
    except TclError:
        pass

root.title("EasiVote")
root.geometry("500x700")
root.minsize(380, 480)
root.resizable(True, True)
voting_table = {}
voting_widgets = {}

# 用 grid 让主窗口可自由伸缩
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=0)  # 标题
root.rowconfigure(1, weight=0)  # 描述
root.rowconfigure(2, weight=1)  # voting：可伸缩区域
root.rowconfigure(3, weight=0)  # editor


def _update_scrollregion():
    """刷新 voting 可滚动区域大小。"""
    voting_canvas.configure(scrollregion=voting_canvas.bbox("all"))


def on_add_opt():
    opt_name = add_opt_entry.get().strip()
    if not opt_name:
        msgbox.showwarning("未输入选项名称",
                           "你没有输入选项名称或输入的选项名称为空，请重新输入。")
        return
    elif opt_name in voting_table.keys():
        msgbox.showwarning("选项名称重复",
                           "你输入的选项名称已经存在，请重新输入。")
        return

    add_opt_entry.delete(0, END)
    voting_table[opt_name] = 0

    voting_widgets[opt_name] = {
        "widget": (tmp_widget := Frame(voting_inner)),
        "label":  Label(tmp_widget,  text=opt_name, font=("Candara", 16)),
        "count":  Label(tmp_widget,  text="0",      font=("Candara", 20)),
        "add":    Button(tmp_widget, text="+", command=partial(on_voting_add, opt_name)),
        "sub":    Button(tmp_widget, text="-", command=partial(on_voting_sub, opt_name)),
        "clear":  Button(tmp_widget, text="×", command=partial(on_voting_clear, opt_name))
    }
    tmp_widget                       .pack(side="top",   padx=5, expand=False, fill="x", anchor="n", pady=2)
    voting_widgets[opt_name]["label"].pack(side="left",  padx=5)
    voting_widgets[opt_name]["clear"].pack(side="right", padx=5)
    voting_widgets[opt_name]["sub"]  .pack(side="right", padx=5)
    voting_widgets[opt_name]["add"]  .pack(side="right", padx=5)
    voting_widgets[opt_name]["count"].pack(side="right", padx=5)
    root.update_idletasks()
    _update_scrollregion()


def on_voting_add(name):
    voting_table[name] += 1
    voting_widgets[name]["count"].config(text=str(voting_table[name]))


def on_voting_sub(name):
    if voting_table[name] == 0:
        return
    voting_table[name] -= 1
    voting_widgets[name]["count"].config(text=str(voting_table[name]))


def on_voting_clear(name):
    voting_table[name] = 0
    voting_widgets[name]["count"].config(text=str(voting_table[name]))


title =       Label(root, text="EasiVote", font=("Candara", 50, "bold"))
description = Label(root, text="适用于多种场景的投票小工具 by MacrosMeng", font=("Candara", 15))
title      .grid(row=0, column=0, sticky="n",   padx=10, pady=(15, 0))
description.grid(row=1, column=0, sticky="n",   padx=10, pady=(0, 10))

# voting 区域：Canvas + Scrollbar 承载 voting_inner，让选项过多时可滚动
voting_wrapper = Frame(root)
voting_wrapper.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
voting_wrapper.columnconfigure(0, weight=1)
voting_wrapper.rowconfigure(0, weight=1)

voting_canvas = Canvas(voting_wrapper, highlightthickness=0)
voting_scroll = Scrollbar(voting_wrapper, orient="vertical", command=voting_canvas.yview)
voting_canvas.configure(yscrollcommand=voting_scroll.set)
voting_canvas .grid(row=0, column=0, sticky="nsew")
voting_scroll .grid(row=0, column=1, sticky="ns")

voting_inner = Frame(voting_canvas)
voting_canvas.create_window((0, 0), window=voting_inner, anchor="nw", tags="voting_inner")


def _on_canvas_configure(event):
    # 让内部 Frame 宽度跟随 Canvas 宽度，保证 fill="x" 生效
    voting_canvas.itemconfigure("voting_inner", width=event.width)


voting_canvas.bind("<Configure>", _on_canvas_configure)
voting_inner.bind("<Configure>", lambda e: _update_scrollregion())


def _on_mousewheel(event):
    # 跨平台鼠标滚轮滚动：Windows / macOS 使用 delta，Linux 使用 Button-4/5
    if platform.system() == "Linux":
        return
    delta = -1 if event.delta > 0 else 1
    voting_canvas.yview_scroll(delta, "units")


voting_canvas.bind_all("<MouseWheel>", _on_mousewheel)


def _on_linux_button4(_event):
    voting_canvas.yview_scroll(-1, "units")


def _on_linux_button5(_event):
    voting_canvas.yview_scroll(1, "units")


voting_canvas.bind_all("<Button-4>", _on_linux_button4)
voting_canvas.bind_all("<Button-5>", _on_linux_button5)

# editor 区域：使用 grid 让 Entry 可横向伸缩
editor = Frame(root)
editor.grid(row=3, column=0, sticky="ew", padx=0, pady=(5, 0))
editor.columnconfigure(1, weight=1)

add_opt_tip =   Label(editor,  text="添加选项", font=("Candara", 12))
add_opt_entry = Entry(editor,  font=("Candara", 12))
add_button =    Button(editor, text="添加", command=on_add_opt)
add_opt_tip  .grid(row=0, column=0, sticky="w", padx=(10, 0), pady=10)
add_opt_entry.grid(row=0, column=1, sticky="ew", padx=10,     pady=10)
add_button   .grid(row=0, column=2, sticky="e", padx=(0, 10), pady=10)

# 让 Enter 键也能添加选项
add_opt_entry.bind("<Return>", lambda e: on_add_opt())

root.mainloop()

