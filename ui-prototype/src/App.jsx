import { useMemo, useState } from "react";
import {
  Activity,
  ArchiveRestore,
  Award,
  BadgeCheck,
  BarChart3,
  BellRing,
  BookOpenCheck,
  Calendar,
  CalendarClock,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  Clock3,
  CloudDownload,
  DatabaseBackup,
  Download,
  FileDown,
  FileSpreadsheet,
  FileUp,
  Filter,
  GraduationCap,
  HardDrive,
  LayoutDashboard,
  LockKeyhole,
  Menu,
  Minus,
  MoreHorizontal,
  Palette,
  PencilLine,
  Phone,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Upload,
  UserCheck,
  UserPlus,
  UsersRound,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const navItems = [
  { id: "dashboard", label: "今日班级工作台", icon: LayoutDashboard },
  { id: "students", label: "学生数据中心", icon: UsersRound },
  { id: "quality", label: "综合素质评价", icon: ShieldCheck },
  { id: "scores", label: "成绩管理", icon: BarChart3 },
  { id: "moral", label: "德育评价", icon: Award },
  { id: "attendance", label: "请假与考勤", icon: CalendarClock },
  { id: "schedule", label: "课程表与日历", icon: CalendarDays },
  { id: "backup", label: "数据备份与恢复", icon: DatabaseBackup },
];

const moduleSubtitles = {
  dashboard: "今天的课程、事项和班级动态",
  students: "学生档案、家长联系人与班级信息",
  quality: "六学期五维评价、汇总排名与等级核对",
  scores: "考试导入、趋势对比与学生个体分析",
  moral: "集体活动、奖项与德育记录",
  attendance: "请假、迟到与出勤情况",
  schedule: "多班级课程安排与学期日历",
  backup: "本地数据归档、定期备份与恢复",
};

const classes = ["全部任教班级", "初三（1）班", "初三（2）班", "初三（3）班", "初三（4）班"];

const classSizes = {
  "全部任教班级": 184,
  "初三（1）班": 46,
  "初三（2）班": 45,
  "初三（3）班": 47,
  "初三（4）班": 46,
};

const students = [
  { no: "20230101", name: "张雨桐", gender: "女", className: "初三（1）班", seat: 1, phone: "138 6218 4521", relation: "母亲", status: "在读" },
  { no: "20230102", name: "李明轩", gender: "男", className: "初三（1）班", seat: 2, phone: "139 5136 2048", relation: "父亲", status: "在读" },
  { no: "20230103", name: "王思远", gender: "男", className: "初三（1）班", seat: 3, phone: "136 8821 9076", relation: "母亲", status: "在读" },
  { no: "20230208", name: "陈佳宁", gender: "女", className: "初三（2）班", seat: 8, phone: "137 0542 1163", relation: "父亲", status: "在读" },
  { no: "20230212", name: "赵一诺", gender: "女", className: "初三（2）班", seat: 12, phone: "158 6247 3980", relation: "母亲", status: "在读" },
  { no: "20230305", name: "周子涵", gender: "男", className: "初三（3）班", seat: 5, phone: "159 8794 2216", relation: "父亲", status: "在读" },
  { no: "20230417", name: "刘诗琪", gender: "女", className: "初三（4）班", seat: 17, phone: "135 7612 5840", relation: "母亲", status: "转入" },
];

const qualityRows = [
  { name: "张雨桐", ethics: "A", study: "A", health: "B", art: "A", practice: "A", total: 28.9, rank: 1, eligible: true },
  { name: "李明轩", ethics: "A", study: "B", health: "A", art: "B", practice: "A", total: 27.6, rank: 2, eligible: true },
  { name: "王思远", ethics: "B", study: "A", health: "B", art: "B", practice: "A", total: 26.8, rank: 3, eligible: true },
  { name: "陈佳宁", ethics: "A", study: "B", health: "A", art: "A", practice: "B", total: 26.5, rank: 4, eligible: true },
  { name: "赵一诺", ethics: "B", study: "B", health: "A", art: "A", practice: "B", total: 25.7, rank: 5, eligible: true },
  { name: "刘诗琪", ethics: "A", study: "B", health: "B", art: "A", practice: "B", total: 19.4, rank: 16, eligible: false },
];

const scoreTrend = [
  { exam: "九上期中", average: 618, gradeAverage: 603 },
  { exam: "九上一模", average: 625, gradeAverage: 608 },
  { exam: "九上期末", average: 631, gradeAverage: 615 },
  { exam: "九下二模", average: 642, gradeAverage: 621 },
];

const subjectScores = [
  { subject: "语文", classScore: 82.4, gradeScore: 80.6 },
  { subject: "数学", classScore: 86.8, gradeScore: 82.5 },
  { subject: "英语", classScore: 88.1, gradeScore: 84.2 },
  { subject: "物理", classScore: 79.6, gradeScore: 78.1 },
  { subject: "化学", classScore: 84.3, gradeScore: 81.9 },
  { subject: "政治", classScore: 76.8, gradeScore: 75.7 },
  { subject: "历史", classScore: 80.2, gradeScore: 77.6 },
];

const progressStudents = [
  { name: "张雨桐", classRank: 2, change: 12, gradeRank: 18, subject: "数学" },
  { name: "王思远", classRank: 8, change: 9, gradeRank: 52, subject: "英语" },
  { name: "陈佳宁", classRank: 13, change: 7, gradeRank: 86, subject: "物理" },
  { name: "周子涵", classRank: 21, change: -8, gradeRank: 126, subject: "语文" },
  { name: "刘诗琪", classRank: 31, change: -11, gradeRank: 164, subject: "数学" },
];

const weeklySchedule = [
  [
    { subject: "语文", className: "初三（1）班", tone: "blue" },
    { subject: "语文", className: "初三（2）班", tone: "green" },
    null,
    { subject: "班会", className: "初三（1）班", tone: "blue" },
    { subject: "语文", className: "初三（4）班", tone: "orange" },
  ],
  [
    { subject: "语文", className: "初三（3）班", tone: "purple" },
    null,
    { subject: "语文", className: "初三（1）班", tone: "blue" },
    { subject: "语文", className: "初三（2）班", tone: "green" },
    null,
  ],
  [
    null,
    { subject: "语文", className: "初三（4）班", tone: "orange" },
    { subject: "教研活动", className: "语文组", tone: "gray" },
    null,
    { subject: "语文", className: "初三（3）班", tone: "purple" },
  ],
  [
    { subject: "语文", className: "初三（2）班", tone: "green" },
    { subject: "语文", className: "初三（1）班", tone: "blue" },
    null,
    { subject: "语文", className: "初三（4）班", tone: "orange" },
    { subject: "语文", className: "初三（1）班", tone: "blue" },
  ],
  [
    { subject: "语文", className: "初三（4）班", tone: "orange" },
    null,
    { subject: "语文", className: "初三（2）班", tone: "green" },
    { subject: "语文", className: "初三（3）班", tone: "purple" },
    null,
  ],
  [null, { subject: "语文", className: "初三（3）班", tone: "purple" }, null, null, { subject: "社团指导", className: "校级", tone: "gray" }],
];

const initialTasks = [
  { id: 1, title: "核对二模成绩异常数据", meta: "成绩管理 · 12:00 前", level: "high", done: false },
  { id: 2, title: "审批学生请假申请", meta: "请假与考勤 · 2 条", level: "medium", done: false },
  { id: 3, title: "确认九下综合素质等级", meta: "综合素质评价 · 初三（1）班", level: "high", done: false },
  { id: 4, title: "整理本周班级活动记录", meta: "德育评价 · 本周", level: "normal", done: true },
];

function AppSelect({ value, onChange, children, ariaLabel, compact = false }) {
  return (
    <label className={`select-wrap ${compact ? "compact" : ""}`}>
      <select aria-label={ariaLabel} value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
      <ChevronDown size={15} aria-hidden="true" />
    </label>
  );
}

function IconButton({ label, children, onClick, className = "", disabled = false }) {
  return (
    <button className={`icon-button ${className}`} type="button" title={label} aria-label={label} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

function ActionButton({ children, icon: Icon, onClick, variant = "secondary", disabled = false }) {
  return (
    <button className={`action-button ${variant}`} type="button" onClick={onClick} disabled={disabled}>
      {Icon ? <Icon size={16} aria-hidden="true" /> : null}
      <span>{children}</span>
    </button>
  );
}

function Panel({ title, eyebrow, action, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      <header className="panel-header">
        <div>
          {eyebrow ? <span className="panel-eyebrow">{eyebrow}</span> : null}
          <h2>{title}</h2>
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

function MetricCard({ icon: Icon, tone, label, value, note, direction = "up" }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon ${tone}`}>
        <Icon size={21} strokeWidth={2.1} aria-hidden="true" />
      </div>
      <div className="metric-body">
        <span className="metric-label">{label}</span>
        <strong>{value}</strong>
        <span className={`metric-note ${direction}`}>
          {direction === "up" ? <TrendingUp size={14} /> : direction === "down" ? <TrendingDown size={14} /> : <Minus size={14} />}
          {note}
        </span>
      </div>
    </article>
  );
}

function GradeBadge({ grade }) {
  return <span className={`grade-badge grade-${grade.toLowerCase()}`}>{grade}</span>;
}

function StatusBadge({ children, tone = "neutral" }) {
  return <span className={`status-badge ${tone}`}>{children}</span>;
}

function Sidebar({ active, onChange, collapsed, onToggle }) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="brand">
        <div className="brand-mark"><GraduationCap size={30} strokeWidth={2.2} /></div>
        <div className="brand-copy">
          <strong>班主任工作台</strong>
          <span>本地综合管理系统</span>
        </div>
      </div>
      <nav className="main-nav" aria-label="主要模块">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className={active === item.id ? "active" : ""}
              onClick={() => onChange(item.id)}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={20} strokeWidth={2} aria-hidden="true" />
              <span>{item.label}</span>
              {item.id === "attendance" ? <i>2</i> : null}
            </button>
          );
        })}
      </nav>
      <div className="sidebar-spacer" />
      <div className="class-brief">
        <span>当前学期</span>
        <strong>2025—2026 学年 下学期</strong>
        <dl>
          <div><dt>任教班级</dt><dd>4 个</dd></div>
          <div><dt>学生总数</dt><dd>184 人</dd></div>
        </dl>
      </div>
      <button className="collapse-button" type="button" onClick={onToggle} title={collapsed ? "展开侧栏" : "收起侧栏"}>
        <Menu size={18} />
        <span>收起菜单</span>
      </button>
    </aside>
  );
}

function Topbar({ active, selectedClass, setSelectedClass, selectedDate, setSelectedDate, onRefresh, sidebarCollapsed, onToggleSidebar }) {
  const selectedModule = navItems.find((item) => item.id === active);
  const formattedDate = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(new Date(`${selectedDate}T12:00:00`));

  return (
    <header className="topbar">
      <div className="topbar-title">
        {sidebarCollapsed ? (
          <IconButton label="展开侧栏" className="mobile-menu-button" onClick={onToggleSidebar}>
            <Menu size={19} />
          </IconButton>
        ) : null}
        <div>
          <h1>{active === "dashboard" ? "您好，李老师！" : selectedModule.label}</h1>
          <p>{active === "dashboard" ? `今天是 ${formattedDate}` : moduleSubtitles[active]}</p>
        </div>
      </div>
      <div className="topbar-actions">
        <AppSelect value={selectedClass} onChange={setSelectedClass} ariaLabel="选择班级">
          {classes.map((name) => <option key={name}>{name}</option>)}
        </AppSelect>
        <label className="date-control">
          <Calendar size={16} aria-hidden="true" />
          <input aria-label="选择日期" type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
        </label>
        <IconButton label="刷新数据" onClick={onRefresh}><RefreshCw size={18} /></IconButton>
      </div>
    </header>
  );
}

function Dashboard({ selectedClass, tasks, setTasks, notify }) {
  const studentCount = classSizes[selectedClass];
  const attendanceData = selectedClass === "全部任教班级"
    ? [
        { name: "正常", value: 178, color: "#2369e8" },
        { name: "请假", value: 4, color: "#f4a62a" },
        { name: "迟到", value: 2, color: "#ef5a5a" },
      ]
    : [
        { name: "正常", value: Math.max(studentCount - 2, 0), color: "#2369e8" },
        { name: "请假", value: 1, color: "#f4a62a" },
        { name: "迟到", value: 1, color: "#ef5a5a" },
      ];
  const trend = [
    { week: "第1周", value: 96.1 },
    { week: "第2周", value: 97.4 },
    { week: "第3周", value: 96.8 },
    { week: "第4周", value: 98.2 },
    { week: "第5周", value: 97.7 },
    { week: "本周", value: 98.4 },
  ];
  const schedule = [
    { period: "第 1 节", time: "08:00—08:45", subject: "语文", className: "初三（1）班", room: "教学楼 A201", state: "已完成" },
    { period: "第 3 节", time: "10:05—10:50", subject: "语文", className: "初三（3）班", room: "教学楼 A305", state: "进行中" },
    { period: "第 5 节", time: "14:00—14:45", subject: "语文", className: "初三（2）班", room: "教学楼 A204", state: "未开始" },
    { period: "第 7 节", time: "15:55—16:40", subject: "班会", className: "初三（1）班", room: "教学楼 A201", state: "未开始" },
  ];

  const toggleTask = (id) => setTasks((current) => current.map((task) => task.id === id ? { ...task, done: !task.done } : task));

  return (
    <div className="page-stack">
      <div className="metric-grid five-columns">
        <MetricCard icon={UsersRound} tone="blue" label="在册学生" value={`${studentCount} 人`} note="数据完整" direction="steady" />
        <MetricCard icon={BookOpenCheck} tone="green" label="今日课程" value="4 节" note="下一节 10:05" direction="steady" />
        <MetricCard icon={UserCheck} tone="purple" label="今日出勤率" value="98.4%" note="较昨日 0.6%" />
        <MetricCard icon={ClipboardCheck} tone="orange" label="待处理事项" value={`${tasks.filter((task) => !task.done).length} 项`} note="2 项优先" direction="steady" />
        <MetricCard icon={Award} tone="red" label="本周德育记录" value="18 条" note="新增 5 条" />
      </div>

      <div className="dashboard-grid">
        <Panel
          title="今日课程"
          action={<button className="text-button" type="button" onClick={() => notify("已切换到课程表与日历")}>查看课表 <ChevronRight size={15} /></button>}
          className="schedule-panel"
        >
          <div className="schedule-list">
            {schedule.map((item) => (
              <button className="schedule-row" type="button" key={`${item.period}-${item.className}`} onClick={() => notify(`${item.period} ${item.className} · ${item.subject}`)}>
                <span className="period-block"><strong>{item.period}</strong><small>{item.time}</small></span>
                <span className="subject-mark">{item.subject.slice(0, 1)}</span>
                <span className="course-copy"><strong>{item.subject}</strong><small>{item.className} · {item.room}</small></span>
                <StatusBadge tone={item.state === "进行中" ? "success" : item.state === "已完成" ? "blue" : "neutral"}>{item.state}</StatusBadge>
              </button>
            ))}
          </div>
        </Panel>

        <Panel
          title="今日待办"
          action={<ActionButton icon={Plus} onClick={() => notify("新建待办窗口已准备")}>新建</ActionButton>}
          className="tasks-panel"
        >
          <div className="task-list">
            {tasks.map((task) => (
              <div className={`task-row ${task.done ? "done" : ""}`} key={task.id}>
                <button className="task-check" type="button" aria-label={task.done ? "恢复待办" : "完成待办"} onClick={() => toggleTask(task.id)}>
                  {task.done ? <Check size={15} /> : null}
                </button>
                <button className="task-copy" type="button" onClick={() => notify(task.title)}>
                  <strong>{task.title}</strong>
                  <span>{task.meta}</span>
                </button>
                <span className={`priority-dot ${task.level}`} title="优先级" />
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="今日出勤情况" action={<button className="text-button" type="button" onClick={() => notify("已打开考勤明细")}>查看明细 <ChevronRight size={15} /></button>}>
          <div className="chart-split">
            <div className="donut-wrap">
              <ResponsiveContainer width="100%" height={210}>
                <PieChart>
                  <Pie data={attendanceData} dataKey="value" nameKey="name" innerRadius={58} outerRadius={84} paddingAngle={2} stroke="none">
                    {attendanceData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 6, borderColor: "#e3e8ef", boxShadow: "0 8px 24px rgba(32,51,84,.12)" }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="donut-center"><strong>{studentCount}</strong><span>应到人数</span></div>
            </div>
            <div className="chart-legend">
              {attendanceData.map((entry) => (
                <div key={entry.name}>
                  <span className="legend-dot" style={{ backgroundColor: entry.color }} />
                  <span>{entry.name}</span>
                  <strong>{entry.value} 人</strong>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="近六周出勤趋势" action={<StatusBadge tone="success">总体稳定</StatusBadge>}>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={trend} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="attendanceFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2369e8" stopOpacity={0.22} />
                    <stop offset="100%" stopColor="#2369e8" stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#edf0f5" vertical={false} />
                <XAxis dataKey="week" tick={{ fill: "#718096", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis domain={[94, 100]} tick={{ fill: "#718096", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(value) => [`${value}%`, "出勤率"]} contentStyle={{ borderRadius: 6, borderColor: "#e3e8ef" }} />
                <Area type="monotone" dataKey="value" stroke="#2369e8" strokeWidth={2.5} fill="url(#attendanceFill)" dot={{ r: 3.5, fill: "#fff", strokeWidth: 2.5 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <Panel title="近期学习动态" action={<button className="text-button" type="button" onClick={() => notify("已切换到成绩个体分析")}>学生分析 <ChevronRight size={15} /></button>}>
        <div className="compact-table-wrap">
          <table className="data-table compact">
            <thead><tr><th>学生</th><th>最新考试</th><th>班级排名</th><th>较上次</th><th>年级排名</th><th>重点变化</th><th>状态</th></tr></thead>
            <tbody>
              {progressStudents.slice(0, 4).map((item) => (
                <tr key={item.name}>
                  <td><span className="student-name"><i>{item.name.slice(-1)}</i><strong>{item.name}</strong></span></td>
                  <td>九下二模</td><td>{item.classRank}</td>
                  <td><span className={item.change > 0 ? "rank-up" : "rank-down"}>{item.change > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}{Math.abs(item.change)} 名</span></td>
                  <td>{item.gradeRank}</td><td>{item.subject}</td>
                  <td><StatusBadge tone={item.change > 0 ? "success" : "warning"}>{item.change > 0 ? "明显进步" : "需要关注"}</StatusBadge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function StudentsPage({ selectedClass, notify }) {
  const [query, setQuery] = useState("");
  const filtered = students.filter((student) => {
    const classMatch = selectedClass === "全部任教班级" || student.className === selectedClass;
    const queryMatch = [student.name, student.no, student.phone].some((value) => value.includes(query.trim()));
    return classMatch && queryMatch;
  });

  return (
    <div className="page-stack">
      <div className="metric-grid four-columns">
        <MetricCard icon={UsersRound} tone="blue" label="学生总数" value={`${classSizes[selectedClass]} 人`} note="4 个班级" direction="steady" />
        <MetricCard icon={BadgeCheck} tone="green" label="档案完整" value="96.7%" note="较上月 2.1%" />
        <MetricCard icon={Phone} tone="purple" label="家长联系人" value="312 人" note="平均 1.7 人/生" direction="steady" />
        <MetricCard icon={CircleAlert} tone="orange" label="待补充档案" value="6 人" note="身份证号等" direction="steady" />
      </div>
      <Panel
        title="学生名单"
        action={
          <div className="button-group">
            <ActionButton icon={FileUp} onClick={() => notify("已打开 Excel 导入流程")}>导入 Excel</ActionButton>
            <ActionButton icon={FileDown} onClick={() => notify("已生成当前筛选名单")}>导出</ActionButton>
            <ActionButton icon={UserPlus} variant="primary" onClick={() => notify("已打开新建学生档案")}>新建学生</ActionButton>
          </div>
        }
      >
        <div className="table-toolbar">
          <label className="search-field">
            <Search size={17} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索姓名、学号或家长电话" />
            {query ? <button type="button" aria-label="清除搜索" onClick={() => setQuery("")}><X size={15} /></button> : null}
          </label>
          <div className="toolbar-meta">当前显示 <strong>{filtered.length}</strong> 条</div>
          <IconButton label="筛选字段" onClick={() => notify("筛选面板已准备")}><Filter size={17} /></IconButton>
          <IconButton label="表格设置" onClick={() => notify("表格字段设置已准备")}><Settings2 size={17} /></IconButton>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th><input type="checkbox" aria-label="全选" /></th><th>学号</th><th>姓名</th><th>性别</th><th>班级</th><th>座号</th><th>主要联系人</th><th>联系电话</th><th>学籍状态</th><th /></tr></thead>
            <tbody>
              {filtered.map((student) => (
                <tr key={student.no} onClick={() => notify(`已选择 ${student.name} 的学生档案`)}>
                  <td onClick={(event) => event.stopPropagation()}><input type="checkbox" aria-label={`选择${student.name}`} /></td>
                  <td className="mono">{student.no}</td>
                  <td><span className="student-name"><i>{student.name.slice(-1)}</i><strong>{student.name}</strong></span></td>
                  <td>{student.gender}</td><td>{student.className}</td><td>{student.seat}</td><td>{student.relation}</td><td>{student.phone}</td>
                  <td><StatusBadge tone={student.status === "在读" ? "success" : "warning"}>{student.status}</StatusBadge></td>
                  <td><IconButton label="更多操作"><MoreHorizontal size={17} /></IconButton></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filtered.length ? <div className="empty-state"><Search size={28} /><strong>没有匹配的学生</strong><span>请调整搜索条件或班级范围</span></div> : null}
        </div>
      </Panel>
    </div>
  );
}

function QualityPage({ notify }) {
  const [semester, setSemester] = useState("九年级下学期");
  const [view, setView] = useState("summary");
  const dimensions = [
    { name: "思想品德", a: 27, b: 16, c: 3, color: "#2369e8" },
    { name: "学业水平", a: 26, b: 17, c: 3, color: "#35b98b" },
    { name: "身心健康", a: 25, b: 18, c: 3, color: "#8b5ce6" },
    { name: "艺术素养", a: 27, b: 16, c: 3, color: "#f2a52b" },
    { name: "实践与创新", a: 26, b: 17, c: 3, color: "#ef6262" },
  ];

  return (
    <div className="page-stack">
      <div className="section-commandbar">
        <div className="segmented-control" role="group" aria-label="评价视图">
          <button type="button" className={view === "summary" ? "active" : ""} onClick={() => setView("summary")}>学期汇总</button>
          <button type="button" className={view === "archive" ? "active" : ""} onClick={() => setView("archive")}>六学期档案</button>
          <button type="button" className={view === "review" ? "active" : ""} onClick={() => setView("review")}>教师核对</button>
        </div>
        <div className="command-spacer" />
        <AppSelect value={semester} onChange={setSemester} ariaLabel="选择学期" compact>
          {["七年级上学期", "七年级下学期", "八年级上学期", "八年级下学期", "九年级上学期", "九年级下学期"].map((item) => <option key={item}>{item}</option>)}
        </AppSelect>
        <ActionButton icon={FileUp} onClick={() => notify(`导入 ${semester} 综合素质底册`)}>导入底册</ActionButton>
        <ActionButton icon={FileDown} variant="primary" onClick={() => notify("已准备导出综合素质档案")}>导出档案</ActionButton>
      </div>

      <div className="metric-grid four-columns">
        <MetricCard icon={UsersRound} tone="blue" label="参评学生" value="46 人" note="名单已匹配" direction="steady" />
        <MetricCard icon={BadgeCheck} tone="green" label="资料完整" value="43 人" note="3 人含 N/A" direction="steady" />
        <MetricCard icon={ShieldCheck} tone="purple" label="均衡生资格" value="42 人" note="4 人已标注" direction="steady" />
        <MetricCard icon={LockKeyhole} tone="orange" label="核对状态" value={view === "review" ? "待确认" : "未锁定"} note="教师确认后锁定" direction="steady" />
      </div>

      {view === "archive" ? (
        <QualityArchive notify={notify} />
      ) : (
        <div className="quality-grid">
          <Panel title="五维等级分布" eyebrow={semester}>
            <div className="dimension-list">
              {dimensions.map((dimension) => (
                <div className="dimension-row" key={dimension.name}>
                  <div className="dimension-label"><strong>{dimension.name}</strong><span>共 46 人</span></div>
                  <div className="stacked-bar" aria-label={`${dimension.name}等级分布`}>
                    <span className="a" style={{ width: `${(dimension.a / 46) * 100}%` }} />
                    <span className="b" style={{ width: `${(dimension.b / 46) * 100}%` }} />
                    <span className="c" style={{ width: `${(dimension.c / 46) * 100}%` }} />
                  </div>
                  <div className="dimension-counts"><span>A {dimension.a}</span><span>B {dimension.b}</span><span>C {dimension.c}</span></div>
                </div>
              ))}
            </div>
            <div className="distribution-legend"><span><i className="a" />A 等级</span><span><i className="b" />B 等级</span><span><i className="c" />C 等级</span></div>
          </Panel>
          <Panel title="评价进度" action={<StatusBadge tone="warning">尚未锁定</StatusBadge>}>
            <div className="progress-ring-row">
              <div className="css-ring" style={{ "--progress": "82%" }}><strong>82%</strong><span>完成度</span></div>
              <dl className="quality-stats">
                <div><dt>已导入</dt><dd>46 人</dd></div>
                <div><dt>系统匹配</dt><dd>43 人</dd></div>
                <div><dt>含 N/A</dt><dd>3 人</dd></div>
                <div><dt>待核对</dt><dd>8 人</dd></div>
              </dl>
            </div>
            <ActionButton icon={view === "review" ? LockKeyhole : ClipboardCheck} variant="primary" onClick={() => notify(view === "review" ? "核对完成后可锁定" : "已进入教师核对视图")}>{view === "review" ? "确认并锁定" : "开始核对"}</ActionButton>
          </Panel>
        </div>
      )}

      <Panel title={view === "archive" ? "学生最终评价档案" : "学生评价汇总"} action={<div className="toolbar-meta">按五维总分排序</div>}>
        <div className="table-scroll">
          <table className="data-table quality-table">
            <thead><tr><th>排名</th><th>学生</th><th>思想品德</th><th>学业水平</th><th>身心健康</th><th>艺术素养</th><th>实践与创新</th><th>五维总分</th><th>均衡生资格</th><th>核对</th></tr></thead>
            <tbody>
              {qualityRows.map((student) => (
                <tr key={student.name}>
                  <td><span className={`rank-number ${student.rank <= 3 ? "top" : ""}`}>{student.rank}</span></td>
                  <td><span className="student-name"><i>{student.name.slice(-1)}</i><strong>{student.name}</strong></span></td>
                  {[student.ethics, student.study, student.health, student.art, student.practice].map((grade, index) => <td key={`${student.name}-${index}`}><GradeBadge grade={grade} /></td>)}
                  <td><strong>{student.total.toFixed(1)}</strong></td>
                  <td><StatusBadge tone={student.eligible ? "success" : "warning"}>{student.eligible ? "符合" : "不符合"}</StatusBadge></td>
                  <td>{view === "review" ? <button className="inline-edit" type="button" onClick={() => notify(`修改 ${student.name} 的最终等级`)}><PencilLine size={14} />修改等级</button> : <CheckCircle2 className="verified-icon" size={18} />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function QualityArchive({ notify }) {
  const semesterHeaders = ["七上", "七下", "八上", "八下", "九上", "九下"];
  return (
    <Panel title="六学期评价完整度" eyebrow="30 项评价数据" action={<button className="text-button" type="button" onClick={() => notify("已筛选含 N/A 的学生")}>仅看 N/A <Filter size={14} /></button>}>
      <div className="archive-matrix">
        <div className="archive-labels"><span>学生</span>{semesterHeaders.map((item) => <span key={item}>{item}</span>)}<span>完整度</span></div>
        {qualityRows.slice(0, 5).map((student, rowIndex) => (
          <div className="archive-row" key={student.name}>
            <strong>{student.name}</strong>
            {semesterHeaders.map((semester, index) => {
              const missing = rowIndex === 4 && index < 2;
              return <span className={missing ? "missing" : "complete"} key={semester}>{missing ? "N/A" : <Check size={14} />}</span>;
            })}
            <span className="archive-percent">{rowIndex === 4 ? "67%" : "100%"}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function ScoresPage({ notify }) {
  const [exam, setExam] = useState("九下二模");
  const [threshold, setThreshold] = useState(8);
  const [mode, setMode] = useState("class");
  const flagged = progressStudents.filter((item) => Math.abs(item.change) >= threshold);
  return (
    <div className="page-stack">
      <div className="section-commandbar">
        <div className="segmented-control">
          <button type="button" className={mode === "class" ? "active" : ""} onClick={() => setMode("class")}>班级分析</button>
          <button type="button" className={mode === "grade" ? "active" : ""} onClick={() => setMode("grade")}>年级对比</button>
          <button type="button" className={mode === "student" ? "active" : ""} onClick={() => setMode("student")}>学生个体</button>
        </div>
        <div className="command-spacer" />
        <AppSelect value={exam} onChange={setExam} ariaLabel="选择考试" compact>
          {["九上期中", "九上一模", "九上期末", "九下二模"].map((item) => <option key={item}>{item}</option>)}
        </AppSelect>
        <ActionButton icon={FileSpreadsheet} onClick={() => notify(`导入 ${exam} 成绩表`)}>导入成绩</ActionButton>
        <ActionButton icon={FileDown} variant="primary" onClick={() => notify("已准备导出成绩分析")}>导出分析</ActionButton>
      </div>
      <div className="metric-grid five-columns">
        <MetricCard icon={Target} tone="blue" label="班级平均分" value="642.3" note="较上次 11.2" />
        <MetricCard icon={TrendingUp} tone="green" label="年级均分差" value="+21.3" note="优势扩大 4.6" />
        <MetricCard icon={BadgeCheck} tone="purple" label="年级前 50" value="13 人" note="新增 2 人" />
        <MetricCard icon={Activity} tone="orange" label="明显进步" value="8 人" note={`阈值 ${threshold} 名`} direction="steady" />
        <MetricCard icon={BellRing} tone="red" label="重点关注" value="5 人" note="偏科或退步" direction="down" />
      </div>
      <div className="dashboard-grid score-grid">
        <Panel title="班级与年级均分趋势" eyebrow={exam}>
          <div className="chart-box large">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={scoreTrend} margin={{ top: 20, right: 14, left: -14, bottom: 0 }}>
                <CartesianGrid stroke="#edf0f5" vertical={false} />
                <XAxis dataKey="exam" tick={{ fill: "#718096", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis domain={[580, 660]} tick={{ fill: "#718096", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 6, borderColor: "#e3e8ef" }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Line name="班级均分" type="monotone" dataKey="average" stroke="#2369e8" strokeWidth={2.5} dot={{ r: 4, fill: "#fff", strokeWidth: 2.5 }} />
                <Line name="年级均分" type="monotone" dataKey="gradeAverage" stroke="#9aa8ba" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3, fill: "#fff", strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="各学科均分对比" eyebrow="按百分制折算">
          <div className="chart-box large">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={subjectScores} margin={{ top: 20, right: 10, left: -20, bottom: 0 }} barGap={3}>
                <CartesianGrid stroke="#edf0f5" vertical={false} />
                <XAxis dataKey="subject" tick={{ fill: "#718096", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis domain={[60, 95]} tick={{ fill: "#718096", fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 6, borderColor: "#e3e8ef" }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Bar name="班级均分" dataKey="classScore" fill="#2369e8" radius={[4, 4, 0, 0]} />
                <Bar name="年级均分" dataKey="gradeScore" fill="#b8c3d2" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
      <Panel
        title="进退步重点名单"
        action={
          <label className="threshold-control">
            <span>变化阈值</span>
            <button type="button" className="threshold-step" aria-label="降低变化阈值" disabled={threshold <= 3} onClick={() => setThreshold((value) => Math.max(3, value - 1))}><Minus size={13} /></button>
            <input type="range" min="3" max="15" value={threshold} onChange={(event) => setThreshold(Number(event.target.value))} />
            <button type="button" className="threshold-step" aria-label="提高变化阈值" disabled={threshold >= 15} onClick={() => setThreshold((value) => Math.min(15, value + 1))}><Plus size={13} /></button>
            <strong>{threshold} 名</strong>
          </label>
        }
      >
        <div className="compact-table-wrap">
          <table className="data-table compact">
            <thead><tr><th>学生</th><th>班级排名</th><th>排名变化</th><th>年级排名</th><th>重点学科</th><th>分析结论</th><th /></tr></thead>
            <tbody>
              {flagged.map((item) => (
                <tr key={item.name}>
                  <td><span className="student-name"><i>{item.name.slice(-1)}</i><strong>{item.name}</strong></span></td>
                  <td>{item.classRank}</td>
                  <td><span className={item.change > 0 ? "rank-up" : "rank-down"}>{item.change > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}{item.change > 0 ? "+" : ""}{item.change}</span></td>
                  <td>{item.gradeRank}</td><td>{item.subject}</td>
                  <td>{item.change > 0 ? "连续两次考试上升" : "本次波动较明显"}</td>
                  <td><button className="text-button" type="button" onClick={() => notify(`查看 ${item.name} 的个体分析`)}>个体分析 <ChevronRight size={14} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!flagged.length ? <div className="empty-state"><CheckCircle2 size={28} /><strong>当前阈值下无重点名单</strong></div> : null}
        </div>
      </Panel>
    </div>
  );
}

function MoralPage({ notify }) {
  const records = [
    { date: "07-22", student: "张雨桐", type: "集体活动", detail: "校庆志愿服务", level: "校级", result: "+3" },
    { date: "07-20", student: "李明轩", type: "获奖记录", detail: "校园征文比赛一等奖", level: "校级", result: "+5" },
    { date: "07-18", student: "王思远", type: "集体活动", detail: "班级图书角整理", level: "班级", result: "+2" },
    { date: "07-16", student: "陈佳宁", type: "社会实践", detail: "社区公益讲解", level: "区级", result: "+4" },
    { date: "07-15", student: "赵一诺", type: "获奖记录", detail: "艺术节合唱优秀个人", level: "校级", result: "+3" },
  ];
  return (
    <div className="page-stack">
      <div className="metric-grid four-columns">
        <MetricCard icon={Award} tone="blue" label="本学期记录" value="126 条" note="本周新增 18 条" />
        <MetricCard icon={Sparkles} tone="green" label="集体活动" value="58 次" note="参与 172 人次" />
        <MetricCard icon={BadgeCheck} tone="purple" label="学生奖项" value="42 项" note="校级以上 28 项" />
        <MetricCard icon={Target} tone="orange" label="社会实践" value="26 次" note="参与率 91.3%" />
      </div>
      <Panel title="德育记录" action={<div className="button-group"><ActionButton icon={FileUp} onClick={() => notify("已打开德育记录导入")}>批量导入</ActionButton><ActionButton icon={Plus} variant="primary" onClick={() => notify("已打开新增德育记录")}>新增记录</ActionButton></div>}>
        <div className="table-toolbar"><label className="search-field"><Search size={17} /><input placeholder="搜索学生或记录内容" /></label><AppSelect value="全部类型" onChange={() => {}} ariaLabel="记录类型" compact><option>全部类型</option><option>集体活动</option><option>获奖记录</option><option>社会实践</option></AppSelect></div>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>日期</th><th>学生</th><th>记录类型</th><th>内容</th><th>级别</th><th>积分</th><th>状态</th><th /></tr></thead><tbody>{records.map((record) => <tr key={`${record.date}-${record.student}`}><td>{record.date}</td><td><span className="student-name"><i>{record.student.slice(-1)}</i><strong>{record.student}</strong></span></td><td>{record.type}</td><td>{record.detail}</td><td>{record.level}</td><td><strong className="positive-score">{record.result}</strong></td><td><StatusBadge tone="success">已确认</StatusBadge></td><td><IconButton label="编辑记录" onClick={() => notify(`编辑 ${record.student} 的记录`)}><PencilLine size={16} /></IconButton></td></tr>)}</tbody></table></div>
      </Panel>
    </div>
  );
}

function AttendancePage({ notify }) {
  const [tab, setTab] = useState("leave");
  const requests = [
    { name: "李明轩", type: "病假", range: "07-23 08:00 — 07-23 17:00", duration: "1 天", reason: "发热就医", status: "待处理" },
    { name: "陈佳宁", type: "事假", range: "07-24 13:30 — 07-24 17:00", duration: "半天", reason: "家庭事务", status: "待处理" },
    { name: "王思远", type: "迟到", range: "07-22 08:12", duration: "12 分钟", reason: "交通拥堵", status: "已登记" },
  ];
  return (
    <div className="page-stack">
      <div className="metric-grid four-columns">
        <MetricCard icon={UserCheck} tone="green" label="今日正常出勤" value="178 人" note="出勤率 98.4%" />
        <MetricCard icon={CalendarClock} tone="orange" label="今日请假" value="4 人" note="待审批 2 条" direction="steady" />
        <MetricCard icon={Clock3} tone="red" label="今日迟到" value="2 人" note="均已登记" direction="steady" />
        <MetricCard icon={Activity} tone="blue" label="本月出勤率" value="97.8%" note="较上月 0.5%" />
      </div>
      <Panel title="请假与考勤记录" action={<ActionButton icon={Plus} variant="primary" onClick={() => notify("已打开新增请假记录")}>新增记录</ActionButton>}>
        <div className="table-toolbar"><div className="segmented-control"><button type="button" className={tab === "leave" ? "active" : ""} onClick={() => setTab("leave")}>请假申请</button><button type="button" className={tab === "attendance" ? "active" : ""} onClick={() => setTab("attendance")}>考勤记录</button><button type="button" className={tab === "stats" ? "active" : ""} onClick={() => setTab("stats")}>月度统计</button></div><div className="command-spacer" /><ActionButton icon={FileDown} onClick={() => notify("已准备导出考勤表")}>导出</ActionButton></div>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>学生</th><th>类型</th><th>时间</th><th>时长</th><th>原因</th><th>状态</th><th>操作</th></tr></thead><tbody>{requests.map((request) => <tr key={`${request.name}-${request.type}`}><td><span className="student-name"><i>{request.name.slice(-1)}</i><strong>{request.name}</strong></span></td><td>{request.type}</td><td>{request.range}</td><td>{request.duration}</td><td>{request.reason}</td><td><StatusBadge tone={request.status === "待处理" ? "warning" : "success"}>{request.status}</StatusBadge></td><td>{request.status === "待处理" ? <button className="inline-edit" type="button" onClick={() => notify(`已审批 ${request.name} 的${request.type}`)}><Check size={14} />审批</button> : <button className="text-button" type="button" onClick={() => notify("已打开记录详情")}>详情</button>}</td></tr>)}</tbody></table></div>
      </Panel>
    </div>
  );
}

function SchedulePage({ notify }) {
  const [week, setWeek] = useState(1);
  const [editing, setEditing] = useState(false);
  const periods = ["08:00—08:45", "08:55—09:40", "10:05—10:50", "11:00—11:45", "14:00—14:45", "14:55—15:40"];
  const days = ["星期一", "星期二", "星期三", "星期四", "星期五"];
  return (
    <div className="page-stack">
      <div className="section-commandbar">
        <AppSelect value="2025—2026 学年 下学期" onChange={() => {}} ariaLabel="选择学期" compact><option>2025—2026 学年 下学期</option><option>2025—2026 学年 上学期</option></AppSelect>
        <div className="week-stepper"><IconButton label="上一周" disabled={week === 1} onClick={() => setWeek((value) => Math.max(1, value - 1))}><ChevronLeft size={17} /></IconButton><strong>第 {week} 周</strong><IconButton label="下一周" onClick={() => setWeek((value) => value + 1)}><ChevronRight size={17} /></IconButton></div>
        <div className="command-spacer" />
        <label className="toggle-control"><input type="checkbox" checked={editing} onChange={(event) => setEditing(event.target.checked)} /><span /><strong>编辑课表</strong></label>
        <ActionButton icon={Settings2} onClick={() => notify("已打开每日节次与时间设置")}>节次设置</ActionButton>
        <ActionButton icon={Save} variant="primary" onClick={() => notify("课程表已保存")}>保存</ActionButton>
      </div>
      <Panel title="教师周课表" eyebrow={`第 ${week} 周 · 2026年7月20日—7月24日`} action={<div className="class-color-legend"><span><i className="blue" />1班</span><span><i className="green" />2班</span><span><i className="purple" />3班</span><span><i className="orange" />4班</span></div>}>
        <div className={`schedule-board ${editing ? "editing" : ""}`}>
          <div className="schedule-head"><span>节次</span>{days.map((day) => <strong key={day}>{day}</strong>)}</div>
          {periods.map((time, rowIndex) => (
            <div className="schedule-board-row" key={time}>
              <div className="time-slot"><strong>第 {rowIndex + 1} 节</strong><span>{time}</span></div>
              {weeklySchedule[rowIndex].map((course, colIndex) => (
                <button className={`course-cell ${course ? course.tone : "empty"}`} type="button" key={`${rowIndex}-${colIndex}`} onClick={() => notify(course ? `${course.subject} · ${course.className}` : editing ? "添加课程" : "该时段无课程") }>
                  {course ? <><strong>{course.subject}</strong><span>{course.className}</span>{editing ? <PencilLine size={13} /> : null}</> : editing ? <Plus size={17} /> : null}
                </button>
              ))}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function BackupPage({ notify }) {
  const [autoBackup, setAutoBackup] = useState(true);
  const [scope, setScope] = useState("全部数据");
  return (
    <div className="page-stack">
      <div className="metric-grid four-columns">
        <MetricCard icon={HardDrive} tone="blue" label="数据库大小" value="48.6 MB" note="本地存储正常" direction="steady" />
        <MetricCard icon={DatabaseBackup} tone="green" label="最近备份" value="今天 08:00" note="自动备份成功" />
        <MetricCard icon={CloudDownload} tone="purple" label="备份档案" value="12 份" note="占用 386 MB" direction="steady" />
        <MetricCard icon={ShieldCheck} tone="orange" label="完整性检查" value="正常" note="刚刚检查" direction="steady" />
      </div>
      <div className="backup-grid">
        <Panel title="一键备份" eyebrow="导出为 ZIP 档案">
          <div className="form-stack">
            <label className="field-label"><span>备份范围</span><AppSelect value={scope} onChange={setScope} ariaLabel="备份范围"><option>全部数据</option><option>2025—2026 学年 下学期</option><option>学生基础数据</option><option>成绩与综合素质</option></AppSelect></label>
            <div className="backup-file-preview"><ArchiveRestore size={25} /><div><strong>班主任工作台_2026-07-23.zip</strong><span>{scope} · 预计 51.2 MB</span></div><CheckCircle2 size={18} /></div>
            <ActionButton icon={Download} variant="primary" onClick={() => notify(`${scope}备份已生成`)}>立即生成备份</ActionButton>
          </div>
        </Panel>
        <Panel title="定期备份" action={<label className="toggle-control icon-only"><input type="checkbox" checked={autoBackup} onChange={(event) => setAutoBackup(event.target.checked)} /><span /></label>}>
          <div className={`form-stack ${!autoBackup ? "disabled-section" : ""}`}>
            <div className="settings-row"><span>备份频率</span><AppSelect value="每天" onChange={() => {}} ariaLabel="备份频率" compact><option>每天</option><option>每周</option><option>每月</option></AppSelect></div>
            <div className="settings-row"><span>执行时间</span><input className="time-input" type="time" value="08:00" onChange={() => {}} /></div>
            <div className="settings-row"><span>保留数量</span><AppSelect value="最近 12 份" onChange={() => {}} ariaLabel="保留备份数" compact><option>最近 6 份</option><option>最近 12 份</option><option>最近 24 份</option></AppSelect></div>
            <div className="settings-status"><CheckCircle2 size={17} /><span>{autoBackup ? "下次备份：明天 08:00" : "自动备份已关闭"}</span></div>
          </div>
        </Panel>
      </div>
      <Panel title="备份记录" action={<ActionButton icon={Upload} onClick={() => notify("请选择要恢复的 ZIP 备份")}>导入并恢复</ActionButton>}>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>备份时间</th><th>档案名称</th><th>范围</th><th>大小</th><th>方式</th><th>状态</th><th>操作</th></tr></thead><tbody>{[
          ["2026-07-23 08:00", "自动备份_2026-07-23.zip", "全部数据", "48.6 MB", "自动"],
          ["2026-07-20 17:42", "九下学期归档_2026-07-20.zip", "九年级下学期", "31.2 MB", "手动"],
          ["2026-07-16 08:00", "自动备份_2026-07-16.zip", "全部数据", "47.9 MB", "自动"],
        ].map((item) => <tr key={item[0]}><td>{item[0]}</td><td><span className="file-name"><HardDrive size={16} />{item[1]}</span></td><td>{item[2]}</td><td>{item[3]}</td><td>{item[4]}</td><td><StatusBadge tone="success">完整</StatusBadge></td><td><div className="row-actions"><IconButton label="恢复此备份" onClick={() => notify(`准备恢复 ${item[1]}`)}><ArchiveRestore size={16} /></IconButton><IconButton label="导出备份" onClick={() => notify(`已导出 ${item[1]}`)}><Download size={16} /></IconButton></div></td></tr>)}</tbody></table></div>
      </Panel>
    </div>
  );
}

function Toast({ message, onClose }) {
  if (!message) return null;
  return (
    <div className="toast" role="status">
      <CheckCircle2 size={18} />
      <span>{message}</span>
      <button type="button" aria-label="关闭提示" onClick={onClose}><X size={15} /></button>
    </div>
  );
}

export function App() {
  const [active, setActive] = useState("dashboard");
  const [selectedClass, setSelectedClass] = useState("全部任教班级");
  const [selectedDate, setSelectedDate] = useState("2026-07-23");
  const [tasks, setTasks] = useState(initialTasks);
  const [toast, setToast] = useState("");
  const [collapsed, setCollapsed] = useState(false);

  const notify = (message) => {
    setToast(message);
    window.clearTimeout(window.__teacherToastTimer);
    window.__teacherToastTimer = window.setTimeout(() => setToast(""), 2600);
  };

  const page = useMemo(() => {
    switch (active) {
      case "students": return <StudentsPage selectedClass={selectedClass} notify={notify} />;
      case "quality": return <QualityPage notify={notify} />;
      case "scores": return <ScoresPage notify={notify} />;
      case "moral": return <MoralPage notify={notify} />;
      case "attendance": return <AttendancePage notify={notify} />;
      case "schedule": return <SchedulePage notify={notify} />;
      case "backup": return <BackupPage notify={notify} />;
      default: return <Dashboard selectedClass={selectedClass} tasks={tasks} setTasks={setTasks} notify={notify} />;
    }
  }, [active, selectedClass, tasks]);

  const changeModule = (id) => {
    setActive(id);
    document.querySelector(".workspace-scroll")?.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar active={active} onChange={changeModule} collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      <main className="workspace">
        <Topbar
          active={active}
          selectedClass={selectedClass}
          setSelectedClass={setSelectedClass}
          selectedDate={selectedDate}
          setSelectedDate={setSelectedDate}
          onRefresh={() => notify("数据已刷新")}
          sidebarCollapsed={collapsed}
          onToggleSidebar={() => setCollapsed(false)}
        />
        <div className="workspace-scroll">{page}</div>
      </main>
      <Toast message={toast} onClose={() => setToast("")} />
    </div>
  );
}
