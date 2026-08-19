# 班主任综合管理系统

面向初中班主任个人使用的 Windows 本地桌面软件。程序基于 Python、PySide6、SQLAlchemy 和 SQLite，无需联网，学生与考试数据保存在本机。

## 当前功能

- 学生数据中心：班级、学生档案、多个家长联系人、搜索筛选、Excel 导入与导出。
- 综合素质评价：六学期五维度 A/B/C/N/A 评价、按九下名单独立排名、比例分档、教师复核锁定及完整 Excel 档案。
- 成绩管理：按实际参加科目导入成绩、班级/年级排名、学生与班级趋势、学科趋势、偏科分析。
- 请假与考勤：病假、事假、迟到、早退、缺勤登记，支持按班级、类型、日期与关键词查询，并可导出 Excel。
- 德育评价：集体活动、获奖荣誉、志愿服务、班级服务等记录，支持手动积分、学生累计统计和 Excel 导出。
- 课程表与日历：独立教学班、学期和自定义课时管理；教学班可选关联学生班级，支持按颜色汇总查看；可记录班级日程和全局提醒，并在日历中按颜色标记。
- 数据备份与恢复：完整 SQLite 快照 ZIP、带学期信息的归档包、每天或每周定时备份、恢复前安全备份和一键恢复。
- 今日班级工作台：启动后集中显示当天课程、日程、考勤、德育记录，以及同学期最近两次考试的学生进退步和相关成绩；顶部日期为只读的系统当天日期。
- 现代桌面工作台：侧栏、主面板和成绩详情可拖动调整大小；表格列可调宽、移动并会记住分栏尺寸。
- 教师个性化：首次使用可填写教师姓名、学校、任教学科、常用班级和默认学期；首页问候与侧栏个人标记会同步更新。当前开发版本为 `v0.9.0`。

## 启动

已安装项目依赖后，双击 [启动班主任管理系统.bat](启动班主任管理系统.bat) 即可运行当前版本。

首次启动会显示教师信息设置窗口。可以先跳过，之后点击首页问候语或侧栏底部个人标记再次填写。

首次在新电脑部署时，在项目目录执行：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

## 数据位置

- 源码运行时：`data/class_manager.db`
- 打包运行时：`%LOCALAPPDATA%\LocalClassManager\class_manager.db`
- 默认备份目录：源码运行时为 `backups/`；打包运行时为 `%LOCALAPPDATA%\LocalClassManager\backups\`
- Excel 模板：`resources/templates/`

请勿直接编辑、替换或删除数据库文件。请使用“数据备份与恢复”模块创建 ZIP 备份；恢复前系统会自动保存当前数据的一份安全备份。

## 打包 exe

双击 [打包当前版本.bat](打包当前版本.bat)，脚本会按需安装 PyInstaller，并生成当前 Python 版程序到：

```text
dist-python/ClassTeacherManager/ClassTeacherManager.exe
```

## 文档与测试

- 完整日常使用说明：[docs/使用说明.md](docs/使用说明.md)
- 自动化测试：

```powershell
.venv\Scripts\python.exe tests\smoke_test.py
.venv\Scripts\python.exe tests\quality_smoke_test.py
.venv\Scripts\python.exe tests\quality_import_smoke_test.py
.venv\Scripts\python.exe tests\quality_finalization_smoke_test.py
.venv\Scripts\python.exe tests\score_smoke_test.py
.venv\Scripts\python.exe tests\attendance_smoke_test.py
.venv\Scripts\python.exe tests\moral_smoke_test.py
.venv\Scripts\python.exe tests\planner_smoke_test.py
.venv\Scripts\python.exe tests\teaching_schedule_smoke_test.py
.venv\Scripts\python.exe tests\teaching_schedule_ui_smoke_test.py
.venv\Scripts\python.exe tests\backup_smoke_test.py
.venv\Scripts\python.exe tests\backup_ui_smoke_test.py
.venv\Scripts\python.exe tests\teacher_profile_smoke_test.py
```

## 项目结构

```text
main.py              程序入口
config.py            本地路径与数据库配置
database/            SQLite 连接与初始化
models/              SQLAlchemy 数据模型
controllers/         业务逻辑
views/               PySide6 界面
utils/               Excel、评分与界面工具
resources/           样式与 Excel 模板
tests/               自动化测试
docs/                使用说明
```
