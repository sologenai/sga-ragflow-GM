import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { LucideSearch } from 'lucide-react';

import Spotlight from '@/components/spotlight';
import { TableEmpty } from '@/components/table-skeleton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { RAGFlowPagination } from '@/components/ui/ragflow-pagination';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { listAuditLogs } from '@/services/admin-service';

const ACTION_TYPE_OPTIONS = [
  { value: '', label: 'admin.all' },
  { value: 'login_success', label: 'admin.auditLoginSuccess' },
  { value: 'login_failed', label: 'admin.auditLoginFailed' },
  { value: 'logout', label: 'admin.auditLogout' },
  { value: 'account_locked', label: 'admin.auditAccountLocked' },
  { value: 'session_kicked', label: 'admin.auditSessionKicked' },
  { value: 'user_created', label: 'admin.auditUserCreated' },
  { value: 'user_deleted', label: 'admin.auditUserDeleted' },
  { value: 'password_changed', label: 'admin.auditPasswordChanged' },
  { value: 'password_reset', label: 'admin.auditPasswordReset' },
  { value: 'kb_created', label: 'admin.auditKbCreated' },
  { value: 'kb_deleted', label: 'admin.auditKbDeleted' },
  { value: 'document_uploaded', label: 'admin.auditDocUploaded' },
  { value: 'document_deleted', label: 'admin.auditDocDeleted' },
];

function AdminAuditLogs() {
  const { t } = useTranslation();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [actionType, setActionType] = useState('');
  const [emailSearch, setEmailSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['admin/auditLogs', page, pageSize, actionType, emailSearch],
    queryFn: async () => {
      const res = await listAuditLogs({
        page,
        page_size: pageSize,
        action_type: actionType || undefined,
        user_email: emailSearch || undefined,
      });
      return res.data.data;
    },
    placeholderData: keepPreviousData,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const formatTime = (v: string) => {
    if (!v) return '-';
    try {
      return new Date(v).toLocaleString();
    } catch {
      return v;
    }
  };

  const formatDetail = (v: string | null | undefined) => {
    if (!v) return '-';
    try {
      const obj = JSON.parse(v);
      return obj.description || obj.reason || JSON.stringify(obj);
    } catch {
      return v;
    }
  };

  return (
    <>
      <Spotlight opcity={0.2} coverage={40} color="rgb(128, 255, 248)" />

      <ScrollArea className="h-full">
        <Card className="border-0 shadow-none bg-transparent">
          <CardHeader className="pb-4">
            <CardTitle className="text-2xl font-bold">
              {t('admin.auditLogs')}
            </CardTitle>
          </CardHeader>

          <CardContent>
            {/* Filters */}
            <div className="flex items-center gap-4 mb-6">
              <div className="relative flex-1 max-w-xs">
                <LucideSearch className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-text-secondary" />
                <Input
                  placeholder={t('admin.searchByEmail')}
                  className="pl-9"
                  value={emailSearch}
                  onChange={(e) => {
                    setEmailSearch(e.target.value);
                    setPage(1);
                  }}
                />
              </div>

              <Select
                value={actionType}
                onValueChange={(v) => {
                  setActionType(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder={t('admin.filterByAction')} />
                </SelectTrigger>
                <SelectContent className="bg-bg-base">
                  {ACTION_TYPE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {t(opt.label)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEmailSearch('');
                  setActionType('');
                  setPage(1);
                }}
              >
                {t('common.reset')}
              </Button>
            </div>

            {/* Table */}
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[170px]">
                      {t('admin.auditTime')}
                    </TableHead>
                    <TableHead>{t('admin.auditUser')}</TableHead>
                    <TableHead>{t('admin.auditAction')}</TableHead>
                    <TableHead>{t('admin.auditResource')}</TableHead>
                    <TableHead>{t('admin.auditIp')}</TableHead>
                    <TableHead className="max-w-[300px]">
                      {t('admin.auditDetail')}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading || items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <TableEmpty loading={isLoading} />
                      </TableCell>
                    </TableRow>
                  ) : (
                    items.map((item: Record<string, any>) => (
                      <TableRow key={item.id}>
                        <TableCell className="text-xs">
                          {formatTime(item.create_time)}
                        </TableCell>
                        <TableCell>{item.user_email || '-'}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{item.action_type}</Badge>
                        </TableCell>
                        <TableCell>
                          {item.resource_type
                            ? `${item.resource_type}${item.resource_id ? `: ${item.resource_id}` : ''}`
                            : '-'}
                        </TableCell>
                        <TableCell className="text-xs text-text-secondary">
                          {item.ip_address || '-'}
                        </TableCell>
                        <TableCell className="max-w-[300px] truncate text-xs">
                          {formatDetail(item.detail)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>

          <CardFooter className="justify-end">
            <RAGFlowPagination
              total={total}
              current={page}
              pageSize={pageSize}
              showSizeChanger
              pageSizeOptions={[10, 20, 50]}
              onChange={(p, ps) => {
                setPage(p);
                setPageSize(ps);
              }}
            />
          </CardFooter>
        </Card>
      </ScrollArea>
    </>
  );
}

export default AdminAuditLogs;
