import { useMemo, useState, type ReactNode } from 'react';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  LucideActivity,
  LucideBot,
  LucideDownload,
  LucideFileSpreadsheet,
  LucideMessageSquare,
  LucideNetwork,
  LucideRefreshCcw,
  LucideSearch,
  LucideUsersRound,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  exportAgentUsage,
  getAgentUsageSummary,
} from '@/services/admin-service';

const numberFormatter = new Intl.NumberFormat('zh-CN');

const EXPORT_SECTIONS = [
  { value: 'overview', label: '总览' },
  { value: 'trend', label: '趋势' },
  { value: 'by_app', label: '按智能体/聊天' },
  { value: 'by_user', label: '按用户' },
  { value: 'chat_graphs', label: '聊天图谱' },
  { value: 'detail', label: '调用明细' },
];

const formatNumber = (value?: number) => numberFormatter.format(value || 0);
const formatSeconds = (value?: number) => `${(value || 0).toFixed(2)}s`;
const filterInputClass =
  'h-10 w-full border-border bg-bg-input text-text-primary placeholder:text-text-secondary/80';
const filterSelectClass =
  'h-10 w-full rounded-md border border-border bg-bg-input px-3 pr-9 text-sm text-text-primary outline-none [color-scheme:dark] focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 [&>option]:bg-slate-950 [&>option]:text-slate-100';
const filterDateClass = `${filterInputClass} [color-scheme:dark]`;

function KpiCard({
  title,
  value,
  description,
  icon,
  tone = 'cyan',
}: {
  title: string;
  value: string;
  description: string;
  icon: ReactNode;
  tone?: 'cyan' | 'emerald' | 'amber' | 'rose' | 'blue' | 'violet';
}) {
  const toneClass = {
    cyan: 'from-cyan-500/20 to-sky-500/5 text-cyan-500',
    emerald: 'from-emerald-500/20 to-green-500/5 text-emerald-500',
    amber: 'from-amber-500/20 to-orange-500/5 text-amber-500',
    rose: 'from-rose-500/20 to-red-500/5 text-rose-500',
    blue: 'from-blue-500/20 to-indigo-500/5 text-blue-500',
    violet: 'from-violet-500/20 to-fuchsia-500/5 text-violet-500',
  }[tone];

  return (
    <Card className="overflow-hidden border-border/70 bg-bg-card/80 shadow-sm">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm text-text-secondary">{title}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight">
              {value}
            </p>
            <p className="mt-2 text-xs text-text-secondary">{description}</p>
          </div>
          <div className={`rounded-2xl bg-gradient-to-br p-3 ${toneClass}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ProgressSplit({
  label,
  value,
  total,
  className,
}: {
  label: string;
  value: number;
  total: number;
  className: string;
}) {
  const percent = total ? Math.round((value / total) * 100) : 0;
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-text-secondary">{label}</span>
        <span className="font-medium">{formatNumber(value)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-bg-base">
        <div
          className={`h-full rounded-full ${className}`}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
    </div>
  );
}

function ExportDialog({
  open,
  scope,
  sections,
  exporting,
  onChangeSections,
  onClose,
  onSubmit,
}: {
  open: boolean;
  scope: 'current' | 'all';
  sections: string[];
  exporting: boolean;
  onChangeSections: (sections: string[]) => void;
  onClose: () => void;
  onSubmit: () => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-[520px] rounded-2xl border border-border bg-bg-card p-6 shadow-2xl">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xl font-semibold">导出 Excel</h3>
            <p className="mt-2 text-sm text-text-secondary">
              {scope === 'all'
                ? '全量导出会忽略时间范围，导出上线以来的数据。'
                : '当前导出会保留页面上的时间、类型、关键词和用户筛选。'}
            </p>
          </div>
          <Badge variant="outline">{scope === 'all' ? '全量' : '当前'}</Badge>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3">
          {EXPORT_SECTIONS.map((item) => (
            <label
              key={item.value}
              className="flex cursor-pointer items-center gap-3 rounded-lg border border-border bg-bg-base px-3 py-2 text-sm"
            >
              <input
                type="checkbox"
                checked={sections.includes(item.value)}
                onChange={(e) => {
                  if (e.target.checked) {
                    onChangeSections([...sections, item.value]);
                  } else {
                    onChangeSections(
                      sections.filter((value) => value !== item.value),
                    );
                  }
                }}
              />
              {item.label}
            </label>
          ))}
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose} disabled={exporting}>
            取消
          </Button>
          <Button
            onClick={onSubmit}
            disabled={exporting || sections.length === 0}
          >
            {exporting ? '导出中...' : '确认导出'}
          </Button>
        </div>
      </div>
    </div>
  );
}

function AgentUsageDashboard() {
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [source, setSource] = useState<'all' | 'agent' | 'dialog'>('all');
  const [granularity, setGranularity] = useState<'day' | 'week' | 'month'>(
    'day',
  );
  const [keyword, setKeyword] = useState('');
  const [userKeyword, setUserKeyword] = useState('');
  const [exportOpen, setExportOpen] = useState(false);
  const [exportScope, setExportScope] = useState<'current' | 'all'>('current');
  const [exportSections, setExportSections] = useState(
    EXPORT_SECTIONS.map((item) => item.value),
  );
  const [exporting, setExporting] = useState(false);

  const params = useMemo(
    () => ({
      from_date: fromDate || undefined,
      to_date: toDate || undefined,
      source,
      keyword: keyword || undefined,
      user_id: userKeyword || undefined,
      granularity,
    }),
    [fromDate, granularity, keyword, source, toDate, userKeyword],
  );

  const { data, isFetching, refetch } = useQuery({
    queryKey: ['admin/agentUsage', params],
    queryFn: async () => (await getAgentUsageSummary(params)).data.data,
    placeholderData: keepPreviousData,
    retry: false,
  });

  const overview = data?.overview;
  const trend = data?.trend ?? [];
  const byApp = data?.by_app ?? [];
  const byUser = data?.by_user ?? [];
  const chatGraphs = data?.chat_graphs ?? [];
  const details = data?.detail ?? [];
  const totalSessions = overview?.total_sessions || 0;

  const openExport = (scope: 'current' | 'all') => {
    setExportScope(scope);
    setExportSections(EXPORT_SECTIONS.map((item) => item.value));
    setExportOpen(true);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await exportAgentUsage({
        ...params,
        scope: exportScope,
        sections: exportSections.join(','),
      });
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `agent_usage_${Date.now()}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setExportOpen(false);
    } finally {
      setExporting(false);
    }
  };

  return (
    <ScrollArea className="h-full">
      <div className="min-h-full rounded-3xl bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.16),transparent_34%),radial-gradient(circle_at_70%_10%,rgba(59,130,246,0.12),transparent_28%)] p-6">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-cyan-500/15 p-3 text-cyan-500">
                <LucideActivity className="size-6" />
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight">
                  智能体使用看板
                </h1>
                <p className="mt-1 text-sm text-text-secondary">
                  覆盖智能体与聊天调用，统计会话、轮次、Token、耗时、失败和聊天图谱生成。
                </p>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => refetch()}>
              <LucideRefreshCcw className="mr-2 size-4" />
              刷新
            </Button>
            <Button variant="outline" onClick={() => openExport('current')}>
              <LucideDownload className="mr-2 size-4" />
              导出当前
            </Button>
            <Button onClick={() => openExport('all')}>
              <LucideFileSpreadsheet className="mr-2 size-4" />
              全量导出
            </Button>
          </div>
        </div>

        <Card className="mb-6 border-border/70 bg-bg-card/80 shadow-sm">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="relative w-full min-w-[260px] xl:w-[310px]">
                <LucideSearch className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" />
                <Input
                  className={`${filterInputClass} pl-9`}
                  placeholder="按智能体/聊天名称、ID、问题、错误搜索"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                />
              </div>
              <div className="w-full min-w-[240px] xl:w-[270px]">
                <Input
                  className={filterInputClass}
                  placeholder="按用户名称、邮箱或ID过滤"
                  value={userKeyword}
                  onChange={(e) => setUserKeyword(e.target.value)}
                />
              </div>
              <div className="w-[200px]">
                <select
                  className={filterSelectClass}
                  value={source}
                  onChange={(e) =>
                    setSource(e.target.value as 'all' | 'agent' | 'dialog')
                  }
                >
                  <option value="all">全部来源</option>
                  <option value="agent">仅智能体</option>
                  <option value="dialog">仅聊天</option>
                </select>
              </div>
              <div className="w-[160px]">
                <select
                  className={filterSelectClass}
                  value={granularity}
                  onChange={(e) =>
                    setGranularity(e.target.value as 'day' | 'week' | 'month')
                  }
                >
                  <option value="day">按日</option>
                  <option value="week">按周</option>
                  <option value="month">按月</option>
                </select>
              </div>
              <div className="w-[185px]">
                <Input
                  className={filterDateClass}
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                />
              </div>
              <div className="flex w-full min-w-[260px] gap-2 xl:w-[270px]">
                <Input
                  className={filterDateClass}
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                />
                <Button
                  variant="outline"
                  onClick={() => {
                    setFromDate('');
                    setToDate('');
                    setKeyword('');
                    setUserKeyword('');
                    setSource('all');
                    setGranularity('day');
                  }}
                >
                  重置
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <KpiCard
            title="总会话数"
            value={formatNumber(overview?.total_sessions)}
            description="智能体和聊天调用会话"
            icon={<LucideMessageSquare className="size-5" />}
          />
          <KpiCard
            title="总对话轮数"
            value={formatNumber(overview?.total_rounds)}
            description="累计多轮对话轮次"
            icon={<LucideActivity className="size-5" />}
            tone="emerald"
          />
          <KpiCard
            title="活跃用户"
            value={formatNumber(overview?.active_users)}
            description="按用户ID去重"
            icon={<LucideUsersRound className="size-5" />}
            tone="blue"
          />
          <KpiCard
            title="Token 估算"
            value={formatNumber(overview?.total_tokens)}
            description="调用日志累计 token"
            icon={<LucideBot className="size-5" />}
            tone="violet"
          />
          <KpiCard
            title="平均耗时"
            value={formatSeconds(overview?.avg_duration)}
            description={`总耗时 ${formatSeconds(overview?.total_duration)}`}
            icon={<LucideActivity className="size-5" />}
            tone="amber"
          />
          <KpiCard
            title="聊天图谱生成"
            value={formatNumber(overview?.chat_graph_count)}
            description="只统计聊天中生成的图谱"
            icon={<LucideNetwork className="size-5" />}
            tone="rose"
          />
        </div>

        <div className="mb-6 grid gap-4 xl:grid-cols-[2fr_1fr]">
          <Card className="border-border/70 bg-bg-card/80 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>调用趋势</span>
                {isFetching && (
                  <Badge variant="outline" className="font-normal">
                    更新中
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trend}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="sessions"
                    name="会话"
                    stroke="#06b6d4"
                    strokeWidth={3}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="rounds"
                    name="轮次"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="chat_graphs"
                    name="聊天图谱"
                    stroke="#f97316"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-bg-card/80 shadow-sm">
            <CardHeader>
              <CardTitle>来源结构</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <ProgressSplit
                label="智能体会话"
                value={overview?.agent_sessions || 0}
                total={totalSessions}
                className="bg-cyan-500"
              />
              <ProgressSplit
                label="聊天会话"
                value={overview?.dialog_sessions || 0}
                total={totalSessions}
                className="bg-emerald-500"
              />
              <ProgressSplit
                label="失败调用"
                value={overview?.error_count || 0}
                total={totalSessions}
                className="bg-rose-500"
              />
              <div className="rounded-2xl border border-border/70 bg-bg-base/50 p-4">
                <p className="text-sm text-text-secondary">当前筛选 Token</p>
                <p className="mt-2 text-2xl font-semibold">
                  {formatNumber(overview?.total_tokens)}
                </p>
                <p className="mt-1 text-xs text-text-secondary">
                  Token 明细在趋势图和下方表格中查看
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <Card className="border-border/70 bg-bg-card/80 shadow-sm">
            <CardHeader>
              <CardTitle>按智能体/聊天归类</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-[360px] overflow-auto rounded-xl border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead className="text-right">会话</TableHead>
                      <TableHead className="text-right">轮次</TableHead>
                      <TableHead className="text-right">用户</TableHead>
                      <TableHead className="text-right">平均耗时</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {byApp.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="py-10 text-center">
                          暂无数据
                        </TableCell>
                      </TableRow>
                    ) : (
                      byApp.map((item) => (
                        <TableRow key={`${item.source}-${item.app_id}`}>
                          <TableCell className="max-w-[260px] truncate font-medium">
                            {item.app_name}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{item.app_type}</Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            {formatNumber(item.total_sessions)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatNumber(item.total_rounds)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatNumber(item.active_users)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatSeconds(item.avg_duration)}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-bg-card/80 shadow-sm">
            <CardHeader>
              <CardTitle>按用户归类</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-[360px] overflow-auto rounded-xl border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>用户</TableHead>
                      <TableHead className="text-right">会话</TableHead>
                      <TableHead className="text-right">轮次</TableHead>
                      <TableHead className="text-right">使用应用</TableHead>
                      <TableHead className="text-right">聊天图谱</TableHead>
                      <TableHead className="text-right">平均耗时</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {byUser.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="py-10 text-center">
                          暂无数据
                        </TableCell>
                      </TableRow>
                    ) : (
                      byUser.map((item) => (
                        <TableRow key={item.user_id}>
                          <TableCell>
                            <div className="font-medium">{item.user_name}</div>
                            <div className="text-xs text-text-secondary">
                              {item.user_email || item.user_id}
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            {formatNumber(item.total_sessions)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatNumber(item.total_rounds)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatNumber(item.used_apps)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatNumber(item.chat_graph_count)}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatSeconds(item.avg_duration)}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1.2fr]">
          <Card className="border-border/70 bg-bg-card/80 shadow-sm">
            <CardHeader>
              <CardTitle>聊天图谱生成记录</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {chatGraphs.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-border py-10 text-center text-text-secondary">
                    暂无聊天图谱生成记录
                  </div>
                ) : (
                  chatGraphs.slice(0, 8).map((item) => (
                    <div
                      key={item.id}
                      className="rounded-xl border border-border bg-bg-base/60 p-4"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="truncate font-medium">
                            {item.name}
                          </div>
                          <div className="mt-1 text-xs text-text-secondary">
                            {item.user_name} · {item.create_date}
                          </div>
                        </div>
                        <Badge variant="outline">
                          {formatNumber(item.doc_num)} 文件
                        </Badge>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-text-secondary">
                        <span>分块 {formatNumber(item.chunk_num)}</span>
                        <span>Token {formatNumber(item.token_num)}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/70 bg-bg-card/80 shadow-sm">
            <CardHeader>
              <CardTitle>最近调用明细</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-[480px] overflow-auto rounded-xl border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>时间</TableHead>
                      <TableHead>来源</TableHead>
                      <TableHead>用户</TableHead>
                      <TableHead>问题</TableHead>
                      <TableHead className="text-right">Token</TableHead>
                      <TableHead>状态</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {details.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="py-10 text-center">
                          暂无数据
                        </TableCell>
                      </TableRow>
                    ) : (
                      details.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="whitespace-nowrap text-xs">
                            {item.create_date}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{item.app_type}</Badge>
                          </TableCell>
                          <TableCell className="max-w-[160px] truncate">
                            {item.user_name}
                          </TableCell>
                          <TableCell className="max-w-[320px] truncate">
                            {item.question || item.app_name}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatNumber(item.tokens)}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={
                                item.status === '失败'
                                  ? 'border-rose-500/40 text-rose-500'
                                  : 'border-emerald-500/40 text-emerald-500'
                              }
                            >
                              {item.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <ExportDialog
        open={exportOpen}
        scope={exportScope}
        sections={exportSections}
        exporting={exporting}
        onChangeSections={setExportSections}
        onClose={() => setExportOpen(false)}
        onSubmit={handleExport}
      />
    </ScrollArea>
  );
}

export default AgentUsageDashboard;
