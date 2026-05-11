import { DateRange } from '@/components/originui/calendar/index';
import TimeRangePicker from '@/components/originui/time-range-picker';
import { PageHeader } from '@/components/page-header';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { SearchInput } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal/modal';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { Spin } from '@/components/ui/spin';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { useFetchChatLog, useFetchDialog } from '@/hooks/use-chat-request';
import {
  IAgentLogMessage,
  IAgentLogResponse,
} from '@/interfaces/database/agent';
import { useQueryClient } from '@tanstack/react-query';
import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router';

const getStartOfToday = (): Date => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
};

const getEndOfToday = (): Date => {
  const today = new Date();
  today.setHours(23, 59, 59, 999);
  return today;
};

const formatSeconds = (value?: number) => {
  if (!value) return '0.00s';
  return `${value.toFixed(2)}s`;
};

const formatDateTimeForApi = (value?: string | Date) => {
  if (!value) return value;
  if (typeof value === 'string') return value;
  const pad = (num: number) => String(num).padStart(2, '0');
  return (
    [value.getFullYear(), pad(value.getMonth() + 1), pad(value.getDate())].join(
      '-',
    ) +
    ` ${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`
  );
};

const getLogTitle = (record: IAgentLogResponse) => {
  return (
    record?.message?.find((item) => item.role === 'user')?.content ||
    record?.message?.[0]?.content ||
    record?.name ||
    ''
  );
};

const ChatLogPage: React.FC = () => {
  const { id: dialogId } = useParams();
  const { navigateToChatList, navigateToChat } = useNavigatePage();
  const { data: chatDetail } = useFetchDialog();
  const queryClient = useQueryClient();

  const initDateRange = useMemo(
    () => ({
      from: getStartOfToday(),
      to: getEndOfToday(),
    }),
    [],
  );

  const init = useMemo(
    () => ({
      keywords: '',
      from_date: formatDateTimeForApi(initDateRange.from),
      to_date: formatDateTimeForApi(initDateRange.to),
      orderby: 'create_time',
      desc: false,
      page: 1,
      page_size: 10,
      dsl: false,
    }),
    [initDateRange],
  );

  const [searchParams, setSearchParams] = useState(init);
  const { data: logData, loading } = useFetchChatLog(searchParams);
  const { sessions: data, total, summary } = logData || {};

  const [currentDate, setCurrentDate] = useState<DateRange>({
    from: initDateRange.from,
    to: initDateRange.to,
  });
  const [keywords, setKeywords] = useState(searchParams.keywords);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: total || 0,
  });
  const [sortConfig, setSortConfig] = useState<{
    orderby: string;
    desc: boolean;
  }>({ orderby: init.orderby, desc: init.desc });
  const [openModal, setOpenModal] = useState(false);
  const [modalData, setModalData] = useState<IAgentLogResponse>();

  useEffect(() => {
    setPagination((pre) => ({
      ...pre,
      total: total || 0,
    }));
  }, [total]);

  const handleSearch = () => {
    setSearchParams((pre) => ({
      ...pre,
      from_date: formatDateTimeForApi(currentDate.from as Date),
      to_date: formatDateTimeForApi(currentDate.to as Date),
      page: pagination.current,
      page_size: pagination.pageSize,
      orderby: sortConfig.orderby,
      desc: sortConfig.desc,
      keywords,
      dsl: false,
    }));
  };

  const handleClickSearch = () => {
    setPagination((pre) => ({ ...pre, current: 1 }));
    handleSearch();
    queryClient.invalidateQueries({
      queryKey: ['fetchChatLog'],
    });
  };

  useEffect(() => {
    handleSearch();
  }, [pagination.current, pagination.pageSize, sortConfig]);

  const handleDateRangeChange = ({
    from: startDate,
    to: endDate,
  }: DateRange) => {
    setCurrentDate({ from: startDate, to: endDate });
  };

  const handlePageChange = (current?: number, pageSize?: number) => {
    let page = current || 1;
    if (pagination.pageSize !== pageSize) {
      page = 1;
    }
    setPagination({
      ...pagination,
      current: page,
      pageSize: pageSize || 10,
    });
  };

  const handleSort = (key: string) => {
    let desc = false;
    if (sortConfig.orderby === key) {
      desc = !sortConfig.desc;
    }
    setSortConfig({ orderby: key, desc });
  };

  const handleReset = () => {
    setSearchParams(init);
    setKeywords(init.keywords);
    setCurrentDate({ from: initDateRange.from, to: initDateRange.to });
  };

  const summaryCards = [
    { label: '调用次数', value: summary?.total_calls ?? total ?? 0 },
    { label: '活跃用户', value: summary?.active_users ?? 0 },
    { label: 'Token 估算', value: summary?.total_tokens ?? 0 },
    { label: '平均耗时', value: formatSeconds(summary?.avg_duration) },
    { label: '总耗时', value: formatSeconds(summary?.total_duration) },
    { label: '错误次数', value: summary?.error_count ?? 0 },
  ];

  const columns = [
    {
      title: '用户',
      dataIndex: 'user_id',
      key: 'user_id',
    },
    {
      title: '问题',
      dataIndex: 'title',
      key: 'title',
      render: (_text, record: IAgentLogResponse) => (
        <span className="line-clamp-2">{getLogTitle(record)}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      render: (_text, record: IAgentLogResponse) => (
        <span className="flex items-center gap-2">
          <span
            className="size-2 rounded-full"
            style={{ backgroundColor: record.errors ? 'red' : 'green' }}
          ></span>
          {record.errors ? '失败' : '成功'}
        </span>
      ),
    },
    {
      title: '轮次',
      dataIndex: 'round',
      key: 'round',
    },
    {
      title: 'Token',
      dataIndex: 'tokens',
      key: 'tokens',
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      key: 'duration',
      sortable: true,
      render: (_text, record: IAgentLogResponse) =>
        formatSeconds(record.duration),
    },
    {
      title: '最新时间',
      dataIndex: 'update_date',
      key: 'update_date',
      sortable: true,
    },
    {
      title: '创建时间',
      dataIndex: 'create_date',
      key: 'create_date',
      sortable: true,
    },
  ];

  const showLogDetail = (item: IAgentLogResponse) => {
    setModalData(item);
    setOpenModal(true);
  };

  return (
    <div>
      <PageHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink onClick={navigateToChatList}>聊天</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbLink onClick={navigateToChat(dialogId as string)}>
                {chatDetail.name}
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>调用日志</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </PageHeader>
      <div className="p-4">
        <div className="mb-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {summaryCards.map((item) => (
            <div key={item.label} className="rounded-md border p-3">
              <div className="text-sm text-text-secondary">{item.label}</div>
              <div className="mt-1 text-xl font-semibold">{item.value}</div>
            </div>
          ))}
        </div>

        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">调用日志</h1>
          <div className="flex justify-end space-x-2 text-foreground">
            <div className="flex items-center space-x-2">
              <span>ID/问题</span>
              <SearchInput
                value={keywords}
                onChange={(e) => {
                  setKeywords(e.target.value);
                }}
                className="w-40"
              ></SearchInput>
            </div>
            <div className="flex items-center space-x-2">
              <span className="whitespace-nowrap">时间</span>
              <TimeRangePicker
                onSelect={handleDateRangeChange}
                selectDateRange={currentDate}
              />
            </div>
            <button
              type="button"
              className="rounded bg-foreground px-4 py-1 text-text-title-invert"
              onClick={handleClickSearch}
            >
              搜索
            </button>
            <button
              type="button"
              className="rounded border bg-transparent px-4 py-1 text-foreground"
              onClick={handleReset}
            >
              重置
            </button>
          </div>
        </div>

        <div className="overflow-auto rounded-md border">
          <Table rootClassName="max-h-[calc(100vh-280px)]">
            <TableHeader className="sticky top-0 z-10 bg-background shadow-sm">
              <TableRow>
                {columns.map((column) => (
                  <TableHead
                    key={column.dataIndex}
                    onClick={
                      column.sortable
                        ? () => handleSort(column.dataIndex)
                        : undefined
                    }
                    className={
                      column.sortable ? 'cursor-pointer hover:bg-muted/50' : ''
                    }
                  >
                    <div className="flex items-center">
                      {column.title}
                      {column.sortable &&
                        sortConfig.orderby === column.dataIndex && (
                          <span className="ml-1">
                            {sortConfig.desc ? '↓' : '↑'}
                          </span>
                        )}
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center"
                  >
                    <Spin size="large">
                      <span className="sr-only">Loading...</span>
                    </Spin>
                  </TableCell>
                </TableRow>
              )}
              {!loading &&
                data?.map((item) => (
                  <TableRow
                    key={item.id}
                    className="cursor-pointer"
                    onClick={() => showLogDetail(item)}
                  >
                    {columns.map((column) => (
                      <TableCell key={column.dataIndex}>
                        {column.render
                          ? column.render(item[column.dataIndex], item)
                          : item[column.dataIndex]}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              {!loading && (!data || data.length === 0) && (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center"
                  >
                    暂无数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        <div className="mt-4 flex w-full justify-end">
          <RAGFlowPagination
            {...pagination}
            total={pagination.total}
            onChange={(page, pageSize) => {
              handlePageChange(page, pageSize);
            }}
          ></RAGFlowPagination>
        </div>
      </div>
      <ChatLogDetailModal
        isOpen={openModal}
        message={modalData?.message as IAgentLogMessage[]}
        errors={modalData?.errors}
        onClose={() => setOpenModal(false)}
      />
    </div>
  );
};

const ChatLogDetailModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  message?: IAgentLogMessage[];
  errors?: string;
}> = ({ isOpen, onClose, message = [], errors }) => {
  const title = getLogTitle({ message } as IAgentLogResponse);

  return (
    <Modal
      open={isOpen}
      onCancel={onClose}
      showfooter={false}
      footer={null}
      title={title || '调用明细'}
      className="!w-[900px]"
    >
      <div className="flex flex-col gap-4">
        {errors && (
          <div className="rounded border border-red-300 bg-red-50 p-3 text-red-600">
            {errors}
          </div>
        )}
        {message.map((item, index) => (
          <div
            key={`${item.role}-${item.id || index}`}
            className="rounded-md border p-4"
          >
            <div className="mb-2 text-sm font-medium text-text-secondary">
              {item.role === 'user' ? '用户' : '助手'}
            </div>
            <div className="whitespace-pre-wrap break-words text-sm leading-6">
              {item.content}
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
};

export default ChatLogPage;
