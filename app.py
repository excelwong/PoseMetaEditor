# -*- coding: utf-8 -*-
"""
PoseWear 姿态库元数据编辑器
================================
桌面应用：浏览并编辑 PoseWearStudio 姿态库的 _metadata.csv

布局（页面三等分）：
  - 左：姿态列表（id + 姿态名），占满整列高度
  - 中：选中姿态 id 对应的姿态图片；图片下方为固定的头部朝向参考文本框（不随姿态切换、不写回 CSV）
  - 右：上=姿态描述_中文（可编辑），下=姿态描述_英文（可编辑）
底部：保存按钮，将修改后的中文/英文描述写回 _metadata.csv

运行：直接双击 run.bat（或 python app.py）
"""

import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# ----------------------------------------------------------------------------
# 配置
# ----------------------------------------------------------------------------
CSV_PATH = r"C:\Users\excel\WorkBuddy\Claw\PoseWearStudio\姿态库\_metadata.csv"
FIELDNAMES = [
    "id", "系统", "分类", "姿态编号", "姿态名",
    "角度", "提示词", "原图", "姿态描述_中文", "姿态描述_英文",
]
EDIT_COLS = ("姿态描述_中文", "姿态描述_英文")
LIB_ROOT = os.path.dirname(CSV_PATH)  # ...\PoseWearStudio\姿态库

CN_FONT = ("Microsoft YaHei", 10)
CN_FONT_BOLD = ("Microsoft YaHei", 10, "bold")


def image_path_for(row):
    """根据 系统 / 分类 / 原图 拼出图片绝对路径。"""
    p = os.path.join(LIB_ROOT, row.get("系统", ""), row.get("分类", ""), row.get("原图", ""))
    return p if os.path.exists(p) else None


def load_rows():
    """读取 CSV，返回 (rows, by_id)。"""
    rows = []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    by_id = {r["id"]: r for r in rows}
    return rows, by_id


def write_rows(rows):
    """原子写回 CSV，保持列顺序 / UTF-8 / LF / 最小引号。"""
    tmp = CSV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDNAMES})
    os.replace(tmp, CSV_PATH)


# ----------------------------------------------------------------------------
# 应用主体
# ----------------------------------------------------------------------------
class PoseEditor:
    def __init__(self, root):
        self.root = root
        self.rows, self.by_id = load_rows()
        self.display_order = sorted(self.by_id.keys())
        self.current_id = None
        self.dirty = False
        self._loading = False
        self.current_pil = None
        self.photo = None

        self._build_ui()
        # 默认选中第一条
        if self.display_order:
            self.tree.selection_set(self.display_order[0])
            self.tree.see(self.display_order[0])
            self._on_select()

    # ----------------------------- UI 构建 -----------------------------
    def _build_ui(self):
        self.root.title("PoseWear 姿态库编辑器  —  _metadata.csv")
        self.root.geometry("1500x920")
        self.root.minsize(1120, 680)

        style = ttk.Style()
        style.configure("Treeview", font=CN_FONT, rowheight=24)
        style.configure("Treeview.Heading", font=CN_FONT_BOLD)
        style.configure("TLabel", font=CN_FONT)
        style.configure("TButton", font=CN_FONT_BOLD)
        style.configure("Header.TLabel", font=CN_FONT_BOLD)

        # 主区域：三等分
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.columnconfigure(0, weight=1)

        main = ttk.Frame(self.root)
        main.grid(row=0, column=0, sticky="nsew")
        main.rowconfigure(0, weight=1)
        for c in range(3):
            main.columnconfigure(c, weight=1, uniform="col")

        self._build_left(main)
        self._build_middle(main)
        self._build_right(main)
        self._build_bottom()

        # 快捷键
        self.root.bind("<Control-s>", lambda e: self._do_save())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_left(self, parent):
        f = ttk.Frame(parent)
        f.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        tree = ttk.Treeview(f, columns=("id", "name"), show="headings", selectmode="browse")
        tree.heading("id", text="id")
        tree.heading("name", text="姿态名")
        tree.column("id", width=200, anchor="w")
        tree.column("name", width=180, anchor="w")
        vsb = ttk.Scrollbar(f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree = tree
        self._populate("")

    def _build_middle(self, parent):
        f = ttk.Frame(parent)
        f.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        f.rowconfigure(0, weight=1)        # 图片（占满剩余空间）
        f.columnconfigure(0, weight=1)

        self.img_label = ttk.Label(f, anchor="center", text="（未选择姿态）")
        self.img_label.grid(row=0, column=0, sticky="nsew")
        self.img_label.bind("<Configure>", lambda e: self._refit())

        self.caption = ttk.Label(f, text="", style="Header.TLabel", anchor="center")
        self.caption.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        # 固定的头部朝向参考文本框：内容固定、不随姿态切换、不写回 CSV
        ref = ttk.LabelFrame(f, text="参考 · 头部朝向（固定，不写入 CSV）")
        ref.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ref.columnconfigure(0, weight=1)

        ref_lines = [
            "抬头朝上看    Head raised,looking up",
            "脸正对镜头    Face forward,looking at viewer",
            "低头朝下看    Head lowered,looking down",
        ]
        self.ref_texts = []
        for i, line in enumerate(ref_lines):
            t = tk.Text(ref, wrap="word", font=CN_FONT, height=2, state="disabled")
            t.grid(row=i, column=0, sticky="ew", pady=(2, 2), padx=2)
            t.configure(state="normal")
            t.insert("1.0", line)
            t.configure(state="disabled")   # 只读：固定参考文本
            self.ref_texts.append(t)

    def _build_right(self, parent):
        f = ttk.Frame(parent)
        f.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)
        f.rowconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)
        f.columnconfigure(0, weight=1)

        self.zh_text = self._build_editor(f, "姿态描述_中文", 0)
        self.en_text = self._build_editor(f, "姿态描述_英文", 1)

    def _build_editor(self, parent, title, row):
        sub = ttk.Frame(parent)
        sub.grid(row=row, column=0, sticky="nsew", pady=2)
        sub.rowconfigure(1, weight=1)
        sub.columnconfigure(0, weight=1)
        ttk.Label(sub, text=title, style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 2))
        txt = tk.Text(sub, wrap="word", font=CN_FONT, undo=True)
        vsb = ttk.Scrollbar(sub, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        txt.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        txt.bind("<<Modified>>", self._on_modified)
        return txt

    def _build_bottom(self):
        bar = ttk.Frame(self.root)
        bar.grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        bar.columnconfigure(0, weight=1)

        self.status = ttk.Label(bar, text="就绪", anchor="w")
        self.status.grid(row=0, column=0, sticky="ew")

        save_btn = ttk.Button(bar, text="　保存修改　", command=self._do_save)
        save_btn.grid(row=0, column=1, sticky="e", padx=(10, 0))

    # ----------------------------- 逻辑 -----------------------------
    def _populate(self, q=""):
        if getattr(self, "tree", None) is None:
            return
        self.tree.delete(*self.tree.get_children())
        q = q.strip().lower()
        for rid in self.display_order:
            row = self.by_id[rid]
            name = row.get("姿态名", "")
            if q and q not in rid.lower() and q not in name.lower():
                continue
            self.tree.insert("", "end", iid=rid, values=(rid, name))

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        new_id = sel[0]
        # 直接切换：未保存的改动静默丢弃，不做任何提示
        self.current_id = new_id
        row = self.by_id[new_id]
        self._show_image(row)
        self._load_text(row)
        self.dirty = False
        self._set_status(f"已加载：{new_id}")

    def _show_image(self, row):
        p = image_path_for(row)
        if p:
            try:
                self.current_pil = Image.open(p)
            except Exception:
                self.current_pil = None
            self.caption.configure(
                text=f"id: {row['id']}   原图: {row['原图']}   "
                      f"{row.get('系统','')} / {row.get('分类','')} / {row.get('角度','')}"
            )
            self._refit()
        else:
            self.current_pil = None
            self.photo = None
            self.img_label.configure(image="", text="（未找到图片）")
            self.caption.configure(text=f"id: {row['id']}   （图片缺失：{row.get('原图','')}）")

    def _refit(self):
        if self.current_pil is None:
            return
        w = self.img_label.winfo_width() or 460
        h = self.img_label.winfo_height() or 760
        if w < 10 or h < 10:
            return
        pw, ph = self.current_pil.size
        scale = min(w / pw, h / ph, 1.0)
        nw, nh = max(1, int(pw * scale)), max(1, int(ph * scale))
        img = self.current_pil.resize((nw, nh), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.img_label.configure(image=self.photo, text="")

    def _load_text(self, row):
        # 加载期间屏蔽 <<Modified>>，避免误判“有未保存的修改”
        self._loading = True
        self.zh_text.delete("1.0", "end")
        self.zh_text.insert("1.0", row.get("姿态描述_中文", "") or "")
        self.zh_text.edit_modified(False)
        self.en_text.delete("1.0", "end")
        self.en_text.insert("1.0", row.get("姿态描述_英文", "") or "")
        self.en_text.edit_modified(False)
        self._loading = False
        self.dirty = False

    def _on_modified(self, event):
        if getattr(self, "_loading", False):
            return
        self.dirty = True
        event.widget.edit_modified(False)
        self._set_status("● 有未保存的修改", dirty=True)

    def _do_save(self):
        if self.current_id is None:
            self._set_status("没有选中的姿态，无法保存")
            return
        row = self.by_id[self.current_id]
        row["姿态描述_中文"] = self.zh_text.get("1.0", "end-1c")
        row["姿态描述_英文"] = self.en_text.get("1.0", "end-1c")
        try:
            write_rows(self.rows)
            self.dirty = False
            self.zh_text.edit_modified(False)
            self.en_text.edit_modified(False)
            self._set_status(f"✓ 已保存：{self.current_id}", normal=True)
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            self._set_status("保存失败：" + str(e))

    def _on_close(self):
        # 直接退出，不做任何保存提示
        self.root.destroy()

    def _set_status(self, text, dirty=False, normal=False):
        self.status.configure(text=text)


def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"找不到元数据文件：{CSV_PATH}")
    root = tk.Tk()
    PoseEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
