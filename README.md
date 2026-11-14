# PoseMetaEditor — 姿态库元数据编辑器

一个轻量的桌面小工具，用来浏览并编辑 [PoseWearStudio](https://github.com/excelwong/PoseWearStudio) 姿态库的 `_metadata.csv`。基于 Python 标准库 `tkinter` + `Pillow`，无需数据库或后端。

---

## 界面

页面三等分：

| 区域 | 内容 |
|---|---|
| 左 | 姿态列表（`id` + 姿态名），占满整列高度 |
| 中 | 当前姿态对应的图片；图片下方是固定的「头部朝向参考」文本框，仅作参考，**不随姿态切换、不写回 CSV** |
| 右 | 上「姿态描述_中文」、下「姿态描述_英文」，均可编辑 |

底部「保存」按钮把修改后的中英文描述写回 CSV。写回采用**临时文件 + 原子替换**，保持原有列顺序、UTF-8 编码、LF 换行和最小引号，不会打乱 CSV 结构。

## 运行

直接双击 `run.bat`，或：

```bash
python app.py
```

依赖只有 `Pillow`（用于显示姿态图）：

```bash
pip install Pillow
```

`run.bat` 默认使用 ComfyUI 自带的 Python（`C:/AI/ComfyUI-aki-v3/python/python.exe`），找不到时回退到系统 `python`。

## 使用前必读：两处本机路径

本项目没有配置文件，路径直接写在源码里，换机器时需要改两处：

1. `app.py` 顶部的 `CSV_PATH` —— 指向 `PoseWearStudio/姿态库/_metadata.csv` 的绝对路径。
2. `run.bat` 里的 `set PY=...` —— 本机 Python 解释器路径。

`LIB_ROOT` 由 `CSV_PATH` 自动推导，图片路径按 `系统/分类/原图` 三级拼接，不需要单独设置。

## 数据说明

- 编辑器只读写两个可编辑列：`姿态描述_中文`、`姿态描述_英文`；其余列（`id`、`系统`、`分类`、`姿态编号`、`姿态名`、`角度`、`提示词`、`原图`）原样保留。
- **姿态图片不随本项目提供**。克隆后请把 PoseWearStudio 的 `姿态库/` 放到 `CSV_PATH` 对应的位置，否则中间栏不会显示图片，但列表与文本编辑仍可正常使用。
- CSV 的 `姿态描述_中文` / `姿态描述_英文` 会被桌面版 `workflow.py` 与安卓版 `Prompt.kt` 用作提示词里姿态参考句的内容，因此这里改完会直接影响生成结果。
