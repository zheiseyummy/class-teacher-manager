# UI AUDIT

## Summary

- Product type: 本地校园管理 SaaS 风格后台工作台。
- User role: 班主任，长期管理多个班级和学生。
- Primary task: 快速确认当天情况，查找学生，录入与复核记录，比较成绩并导出学期档案。
- Current UI quality: 功能完整、已有统一基础样式，但信息结构仍偏原型；真正窄屏不可用，空状态和操作层级不完整。

## Findings

| Priority | Area | Issue | Evidence | Recommended Fix |
|---|---|---|---|---|
| P1 | 响应式 | 主窗口最小宽度为 1120px，390px 无法使用 | `MainWindow.setMinimumSize(1120, 700)`，各模块工具栏为固定单行 | 增加紧凑导航菜单、工具栏重排、双栏转纵向和关键列模式 |
| P1 | 全局导航 | 大面积高饱和蓝色侧栏持续抢占注意力 | 侧栏 208-310px 且整块 `#1d67d4` | 改为轻量中性侧栏，主色只用于选中态和主操作 |
| P1 | 数据空状态 | 多数表格无数据时只显示大片白色区域 | 学生、考勤、成绩、评价直接将 row count 设为 0 | 区分未建数据与筛选无结果，给出下一步入口 |
| P1 | 工具栏 | 页面标题与模块内部标题重复，主次操作混排 | Shell 已显示“成绩管理”，内容区再次显示同名标题 | 内容区改为上下文/范围栏，主操作靠右，次要操作收入口菜单 |
| P1 | 列表详情 | 学生、考勤、成绩和综合评价在小宽度仍强制左右双栏 | 多个水平 `QSplitter` 且 childrenCollapsible=False | 窄屏切换纵向；详情区可滚动并保留列表上下文 |
| P2 | 视觉一致性 | 字号、按钮高度、圆角和状态色较多且存在重复规则 | QSS 中 `#sectionTitle` 重复定义，部分按钮无对象角色 | 收敛为 12/13/15/22px、40px 控件、6-8px 圆角和统一语义色 |
| P2 | 学生可扫读性 | ID、备注等低优先级列占据首屏，姓名和班级不够突出 | 学生表默认展示 9 列 | 宽屏优化列宽；窄屏只保留姓名、学号、班级关键字段 |
| P2 | 状态反馈 | 禁用按钮缺少原因，筛选选中和焦点仅靠细边框 | 未选择学生时按钮灰显但无统一说明 | 加工具提示、清晰焦点边框、选中行和筛选状态反馈 |
| P2 | 隐私 | 视觉测试目前输出到 `docs/`，缺少专门 QA 边界 | 测试使用虚拟姓名，但截图目录与说明分散 | 统一输出 `.design/screenshots/`，报告声明仅含演示数据 |

## Information Architecture

- Current structure: 左侧八模块导航；顶部页面标题；首页为指标与四块信息面板；业务页各自维护工具栏、表格和详情。
- Missing structure: 紧凑模式导航、页面内一致的“范围/筛选/主操作”层级、空结果解释和统一状态说明。
- Suggested structure: App shell → contextual header → compact toolbar/filter bar → data surface → detail surface；首页为关键状态 → 今日任务 → 近期异常。

## Component Review

- Navigation: 模块完整，但视觉权重过高且不能折叠。
- Tables / lists / cards: 表格交互基础完备；缺空状态、字段优先级和窄屏策略。首页卡片数量可接受，不继续增加。
- Forms / inputs: 基本一致，但需要统一 40px 高度、标签和焦点反馈。
- Buttons / actions: 主按钮已有蓝色角色；危险操作、导出和次操作需要更清晰隔离。
- Status indicators: 工作台已有语义徽标；其他模块状态主要为纯文本，可通过模型颜色和统一标签规则增强。

## Visual Review

- Typography: 页面标题和表格层级基本清楚，但同一页面存在重复标题。
- Color: 侧栏蓝色面积过大；内容区状态色较丰富但语义可进一步统一。
- Spacing: 主要使用 10-22px，接近合理；需统一到 8/12/16/24px。
- Borders / shadows / radius: 当前无夸张阴影，方向正确；圆角与边框可进一步收敛。
- Density: 桌面端适中；空数据时显得过空，紧凑端则发生挤压。

## State Coverage

- Loading: 本地同步查询暂无显式状态，导入导出期间缺忙碌反馈。
- Empty: 工作台有空状态，数据表模块不足。
- Error: 主要通过安全的 `QMessageBox`，不会泄露技术细节。
- Disabled: 存在但原因不透明。
- Hover: 按钮、导航、表格行已有基础反馈。
- Selected: 导航和表格行清楚，筛选条件缺“已应用”提示。

## Mobile Review

- Layout: 当前最小宽度 1120px，未达到 390px 要求。
- Text overflow: 1120px 下页标题已有截断风险，390px 会更严重。
- Button size: 35px 偏小，窄屏触控目标需提升至 40-44px。
- Horizontal scroll: 表格有受控横向滚动，但工具栏和双栏不是受控溢出。
- Fixed bars / safe area: 无固定底栏；顶部栏需在紧凑模式减少控件。

## Risk Review

- Customer data: 学生、家长、成绩和行为信息均为敏感数据；截图只用测试数据库。
- Permissions: 当前单机个人版没有账户权限模型，不在 UI 中伪造。
- Secrets: 无联网与 API 密钥。
- Bulk send / export / writeback: 有 Excel 导入导出，没有通知发送或外部写回；文件选择步骤必须保留。
- External links: 仅本地模板文件。
- Human confirmation needed: 删除学生/记录、数据库恢复、综合素质最终锁定和所有导出范围。

## Decision

- Proceed with redesign: 是。
- Must fix before delivery: 390px 紧凑模式、全局壳层层级、学生/记录工具栏与双栏、自解释空状态、统一 token。
- Optional follow-up: 后续若增加通知或家校沟通，必须先设计权限和发送前复核，不在本阶段提前搭空壳。
