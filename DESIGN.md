# DESIGN

## Product Type

- Type: 本地 SaaS 风格校园后台工作台。
- Main business object: 班级和学生。
- Selected recipe: `recipes/saas-dashboard.md`。
- Reference files: `references/saas-dashboard-ui.md` 与五份 UI/风险检查清单。
- Selected patterns: `shadcn-dashboard-shell`、`faceted-filter-table`、`loading-empty-error-set`。
- User role: 同时管理多个班级的班主任或任课教师。
- Primary task: 找到需要处理的班级/学生，完成记录或复核，并掌握成绩与综合素质变化。

## Pattern Commitments

| Pattern | Where It Applies | What To Imitate | What Not To Copy |
|---|---|---|---|
| `shadcn-dashboard-shell` | 主窗口、导航、标题区、工作台 | 稳定 shell、轻量导航、模块上下文、克制指标区 | React 结构、品牌配色、认证计费模块 |
| `faceted-filter-table` | 学生、考勤、德育、成绩、综合素质 | 搜索筛选贴近数据、字段优先级、选中行与详情关联 | 前端表格依赖、无关批量操作 |
| `loading-empty-error-set` | 所有空表、禁用操作、错误提示 | 真实原因、下一步、重试/清筛选路径 | 泛化占位和假加载动画 |

## Design Goals

- Goal 1: 教师进入任一模块后，5 秒内明确当前班级/范围、关键状态和主操作。
- Goal 2: 桌面端保持高效双栏，390px 紧凑窗口切换为单列且主要功能可达。
- Goal 3: 将字体、间距、颜色、圆角、表格、按钮、弹窗和状态收敛为可维护的统一语言。

## Screen Structure

- Navigation: 宽屏使用 224px 轻色侧栏；窄屏隐藏侧栏，在标题栏提供模块菜单。
- Main content: 顶部为页面上下文；学生页单独显示搜索/班级/导入导出/新增；其余模块使用一致工具栏。
- Secondary panel / details: 宽屏为可拖动双栏；窄屏改为纵向，详情面板可滚动。
- Primary action: 每页最多一个实心主按钮，如“新增学生”“导入成绩”“新增记录”。
- Risk / confirmation area: 删除使用危险样式并二次确认；导出继续经过范围选择和文件路径确认；恢复继续显示影响说明。

## Component Plan

| Component | Purpose | Desktop Behavior | Mobile Behavior |
|---|---|---|---|
| App sidebar | 全局模块切换与教师入口 | 轻色固定侧栏、明确选中态 | 隐藏，标题栏菜单替代 |
| Context header | 页面标题、说明、日期/班级 | 单行左右布局 | 隐藏次要说明与日期，保留菜单和标题 |
| Filter toolbar | 搜索、筛选、主次操作 | 一行紧凑排列 | 搜索独占一行，筛选与主操作第二行，次操作收进“更多” |
| Data table | 高频可扫读数据 | 44px 行高、完整关键列、详情双栏 | 隐藏低优先级列，保留受控横向滚动 |
| Detail pane | 学生或记录上下文 | 可拖动宽度 | 纵向排列并滚动 |
| Empty state | 无数据/无结果说明 | 表格区域居中，提供下一步 | 高度收敛，文案可换行 |
| Dialog/form | 新增、编辑、设置和复核 | 统一控件与按钮区 | 最大宽度受窗口约束，内容可滚动 |

## State Plan

- Loading: 导入导出期间设置忙碌光标并防止重复点击；本地查询不展示无意义骨架。
- Empty: “尚未建立数据”显示建立/导入方向；“筛选无结果”显示清除筛选方向。
- Error: 继续使用区块/弹窗级错误，文案不暴露路径、SQL 或堆栈。
- Disabled: 未选择对象时禁用编辑、删除、保存，并提供原因工具提示。
- Hover: 仅可点击项有浅主色反馈。
- Selected: 主导航、页签、表格行和筛选条件统一使用主色浅背景。
- Needs human review: 导出、删除、恢复和最终锁定均不能自动执行。

## Visual System

- Typography: Microsoft YaHei UI / Segoe UI；页面标题 22px，区块标题 15px，正文/表格 13px，辅助 12px。
- Color: 中性灰白承载结构；主色 `#2F64D6`；成功 `#168263`、警告 `#B66A11`、错误 `#C74653`；侧栏不再使用整块饱和蓝。
- Spacing: 8/12/16/24px；工作台卡片间距 12px。
- Radius / shadow / border: 6-8px 圆角、`#DDE3EA` 细边框、仅弹窗保留轻微系统阴影。
- Density: 控件 40px，表格行 44px；首页不再增加卡片数量。

## Responsive Plan

- Desktop viewport: 1440×900，侧栏 + 双栏详情，内容边距 20-24px。
- Mobile viewport: 390×844，视为桌面软件紧凑窗口而非独立手机应用。
- Expected mobile layout: 顶部模块菜单、紧凑标题、工具栏两行、列表/详情纵向、工作台指标两列并允许页面纵向滚动。
- Overflow prevention: 隐藏低优先级列；工具栏重排；日期与辅助说明按宽度隐藏；只有数据表允许受控横向滚动。

## Safety Plan

- Customer data: QA 使用临时 SQLite 和明确演示数据，不读取正式数据库。
- Permissions: 不新增虚假权限入口。
- Secrets: 不新增网络服务或密钥字段。
- Bulk send / export / writeback: 无群发和外部写回；导出必须经过教师主动选择。
- External links: 仅允许打开本地模板。
- Human confirmation: 删除、恢复、综合素质锁定和导出均保留现有人工步骤。

## Implementation Notes

- Files to edit: `views/main_window.py`、`views/workbench_view.py`、`views/students_view.py`、`views/student_detail_pane.py`、`views/attendance_view.py`、`views/scores_view.py`、`views/moral_view.py`、`views/quality_view.py`、`utils/ui_layout.py`、`resources/styles.qss`、视觉 QA 测试与报告。
- Files to avoid: 控制器、ORM 模型、数据库协议和 Excel 字段映射，除非 UI 运行被其阻断。
- Existing design patterns to preserve: 可拖动 `QSplitter`、Lucide 图标、本地 QSettings 布局记忆、真实控制器数据、现有确认弹窗。
- Pattern files to keep open while editing: 三个选中 pattern 的 `pattern.md` 与 `code/README.md`。
- License / source constraints: 仅迁移信息架构和交互思想；不复制 React/Tailwind 实现，无新增第三方 UI 依赖。
