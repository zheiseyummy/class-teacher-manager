# PATTERN MATCH

## Summary

- Product type: 本地运行的 SaaS 风格后台管理工作台（PySide6 桌面端）。
- Main business object: 班级、学生，以及挂接在学生上的成绩、考勤、德育和综合素质记录。
- Selected recipe: `recipes/saas-dashboard.md`。
- Selected patterns: `app-shell/shadcn-dashboard-shell`、`data-table/faceted-filter-table`、`states/loading-empty-error-set`。
- Patterns deliberately not selected: `vite-shadcn-admin-shell` 与现有 PySide6 技术栈不匹配；`tremor-kpi-chart-grid` 会让统计卡片压过教师日常处理任务；CRM、AI 和移动笔记模式与业务对象不符。

## Product Type Decision

| Signal | Evidence | Decision Impact |
|---|---|---|
| User role | 初中班主任，长期、高频、重复使用 | 优先效率、清晰度和低视觉负担 |
| Primary task | 查学生、录考勤、导成绩、复核评价、看当天安排 | 首屏突出异常、待办和快速入口 |
| Data object | 班级和学生是主对象，其他记录均围绕其展开 | 列表和详情保持上下文，不重写数据模型 |
| Risk level | 学生姓名、家长电话、成绩和行为记录属于敏感数据 | 截图只用演示数据，导出、删除和恢复保留人工确认 |
| Mobile need | 软件以桌面端为主，但需支持 390px 紧凑窗口 | 侧栏切换为菜单，工具栏重排，表格保留受控横向滚动或关键列 |

## Recipe Selection

- Recipe: `saas-dashboard.md`。
- Why this recipe: 系统有稳定导航、多业务模块、搜索筛选、表格详情、导入导出和设置，符合后台工作台而非营销页面。
- References to read: `references/saas-dashboard-ui.md`。
- Checklists to read: UI audit、visual QA、product risk、mobile responsive、customer data safety。

## Pattern Selection

| Pattern | Role In This Redesign | Why Selected | What To Imitate | What Not To Copy |
|---|---|---|---|---|
| `shadcn-dashboard-shell` | Main | 需要稳定的侧栏、上下文标题和主内容层级 | 轻量侧栏、页面标题区、概览到列表的顺序、窄屏菜单 | React 组件、认证/计费、多租户和品牌样式 |
| `faceted-filter-table` | Secondary | 学生、考勤、成绩和评价均依赖高频筛选与列表详情 | 搜索和筛选贴近表格、选中行清晰、详情保持上下文、字段优先级 | TanStack 状态层、演示字段、无关批量操作 |
| `loading-empty-error-set` | State | 当前大量空表只有白屏，禁用原因不清楚 | 区分无数据与无搜索结果、明确下一步、区块级错误和可见焦点 | 只写“暂无数据”的泛化占位和无业务阻断的假状态 |

## Business Object Mapping

| Target Project Object | Pattern Object | Fields / Components To Map | Notes |
|---|---|---|---|
| 班级 | Workspace context | 当前班级筛选、班级人数、今日情况 | 工作台和列表共享明确上下文 |
| 学生 | Table row + detail sheet | 姓名、学号、班级、年级、座号、联系人摘要 | 宽屏列表详情双栏，窄屏纵向排列 |
| 考勤/德育记录 | Filtered record table | 学生、班级、类型、状态、日期、事由 | 删除继续二次确认 |
| 考试与评价 | Context selector + analysis table | 考试批次、排名、科目、学期、五维状态 | 原始成绩和锁定逻辑不变 |

## State Coverage From Patterns

- Loading: 本地查询保持界面结构稳定；长耗时导入导出使用忙碌光标和禁用按钮。
- Empty: 分为“尚未建立数据”和“当前筛选无结果”，提供创建、导入或清除筛选方向。
- Error: 保留现有区块/弹窗错误，不显示堆栈、路径或数据库细节。
- Disabled: 编辑、删除、保存等在未选择对象时禁用，并提供工具提示。
- Hover: 导航、按钮、表格行、标签和详情入口统一反馈。
- Selected: 当前模块、表格行、页签、筛选状态使用稳定主色和浅色背景。
- Needs human review: 导出文件范围、删除、恢复、最终综合素质锁定继续由教师确认。

## License And Source Risk

| Pattern | Source | License | Risk / Required Action |
|---|---|---|---|
| `shadcn-dashboard-shell` | shadcn/ui blocks | MIT | 只迁移布局关系和 token，不复制 React 源码或品牌资产 |
| `faceted-filter-table` | OpenStatus / shadcn data table | MIT | 只借鉴筛选和详情结构，不引入前端依赖 |
| `loading-empty-error-set` | Kit internal pattern | Project-local | 可按 PySide6 原生组件实现 |

## Human Confirmation Required

- [x] Customer data: 截图仅使用测试脚本生成的虚拟姓名和无真实联系方式数据。
- [ ] Permissions: 当前版本没有账户和权限模块，不虚构实现。
- [x] Bulk send / export / writeback: 导出仍需教师选择范围与文件路径；没有自动群发或外部写回。
- [x] External links: 仅打开本地 Excel 模板，不新增外部链接。
- [x] Delete / irreversible actions: 学生、记录和恢复操作保留二次确认。
- [x] Secrets / API keys / internal links: 软件离线运行，不增加密钥或内部服务地址。
- [x] Final copy / dates / recipients: 工作台日期来自本机，软件不发送真实消息。

## Decision

- Proceed with selected patterns: 是，以 Qt 原生方式适配。
- Need more source verification: 否，不复制上游代码。
- Must avoid: 宣传页式首屏、卡片套卡片、饱和蓝色大墙、无意义动画、把未实现功能画进界面。
