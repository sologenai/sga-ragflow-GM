import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  useImportKnowledgeGraph,
  usePreviewImportKnowledgeGraph,
} from '@/hooks/use-knowledge-request';
import { Upload } from 'lucide-react';
import React, { useRef, useState } from 'react';

type GraphImportPreview = {
  can_import: boolean;
  blocking_reasons?: string[];
  existing_graph?: boolean;
  source_document_count?: number;
  target_document_count?: number;
  matched_document_count?: number;
  missing_document_count?: number;
  extra_document_count?: number;
  conflict_count?: number;
  graph_record_count?: number;
  graph_kind_counts?: Record<string, number>;
  missing_documents?: Array<{ id: string; name: string }>;
  extra_documents?: Array<{ id: string; name: string }>;
  conflicts?: Array<{ source?: { name?: string }; candidate_count?: number }>;
};

function CountLine({
  label,
  value,
  danger,
}: {
  label: string;
  value?: number;
  danger?: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border-button px-3 py-2">
      <span className="text-text-secondary">{label}</span>
      <span
        className={danger ? 'text-state-error font-semibold' : 'font-semibold'}
      >
        {value ?? 0}
      </span>
    </div>
  );
}

export function GraphImportDialog({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState<GraphImportPreview>();
  const [overwrite, setOverwrite] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { loading: previewLoading, previewImportKnowledgeGraph } =
    usePreviewImportKnowledgeGraph();
  const { loading: importLoading, importKnowledgeGraph } =
    useImportKnowledgeGraph();

  const reset = () => {
    setFile(undefined);
    setPreview(undefined);
    setOverwrite(false);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const nextFile = event.target.files?.[0];
    setFile(nextFile);
    setPreview(undefined);
    setOverwrite(false);
    if (nextFile) {
      const ret = await previewImportKnowledgeGraph(nextFile);
      if (ret?.code === 0) {
        setPreview(ret.data);
      }
    }
  };

  const handleImport = async () => {
    if (!file || !preview?.can_import) {
      return;
    }
    const ret = await importKnowledgeGraph({ file, overwrite });
    if (ret?.code === 0) {
      setOpen(false);
      reset();
    }
  };

  const canImport =
    !!file &&
    !!preview?.can_import &&
    (!preview?.existing_graph || overwrite) &&
    !previewLoading &&
    !importLoading;

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) {
          reset();
        }
      }}
    >
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-w-3xl text-text-primary">
        <DialogHeader>
          <DialogTitle>导入知识图谱</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border border-dashed border-border-button p-4">
            <input
              ref={inputRef}
              type="file"
              accept=".zip,application/zip"
              onChange={handleFileChange}
            />
            <div className="mt-2 text-xs text-text-secondary">
              上传由“导出图谱”生成的 zip
              包。系统会先做文件映射预检，预检不通过不会写入图谱。
            </div>
          </div>

          {file && (
            <div className="text-sm text-text-secondary">
              当前文件：<span className="text-text-primary">{file.name}</span>
            </div>
          )}

          {previewLoading && (
            <div className="rounded-md bg-bg-card p-3 text-sm">
              正在检查图谱包和目标知识库文件映射...
            </div>
          )}

          {preview && (
            <div className="space-y-4">
              <div
                className={
                  preview.can_import
                    ? 'rounded-md bg-emerald-500/10 p-3 text-sm text-emerald-600'
                    : 'rounded-md bg-red-500/10 p-3 text-sm text-state-error'
                }
              >
                {preview.can_import
                  ? '预检通过：文件可以映射，允许导入。'
                  : '预检未通过：请先处理缺失文件或冲突文件。'}
              </div>

              {preview.blocking_reasons?.length ? (
                <div className="rounded-md border border-state-error/40 p-3 text-sm text-state-error">
                  {preview.blocking_reasons.map((reason) => (
                    <div key={reason}>{reason}</div>
                  ))}
                </div>
              ) : null}

              <div className="grid grid-cols-2 gap-3 text-sm">
                <CountLine
                  label="源文件数"
                  value={preview.source_document_count}
                />
                <CountLine
                  label="目标文件数"
                  value={preview.target_document_count}
                />
                <CountLine
                  label="已匹配"
                  value={preview.matched_document_count}
                />
                <CountLine
                  label="缺失文件"
                  value={preview.missing_document_count}
                  danger={(preview.missing_document_count ?? 0) > 0}
                />
                <CountLine
                  label="目标多出"
                  value={preview.extra_document_count}
                />
                <CountLine
                  label="冲突文件"
                  value={preview.conflict_count}
                  danger={(preview.conflict_count ?? 0) > 0}
                />
              </div>

              <div className="rounded-md bg-bg-card p-3 text-xs text-text-secondary">
                图谱记录：{preview.graph_record_count ?? 0}
                {preview.graph_kind_counts
                  ? `；分类：${Object.entries(preview.graph_kind_counts)
                      .map(([key, value]) => `${key} ${value}`)
                      .join('，')}`
                  : ''}
              </div>

              {preview.existing_graph && (
                <label className="flex items-center gap-2 rounded-md border border-border-button p-3 text-sm">
                  <input
                    type="checkbox"
                    checked={overwrite}
                    onChange={(event) => setOverwrite(event.target.checked)}
                  />
                  目标知识库已有图谱，导入时覆盖当前图谱
                </label>
              )}

              {(preview.missing_documents?.length ||
                preview.extra_documents?.length ||
                preview.conflicts?.length) && (
                <div className="max-h-48 overflow-auto rounded-md border border-border-button p-3 text-xs text-text-secondary">
                  {preview.missing_documents?.slice(0, 20).map((doc) => (
                    <div key={`missing-${doc.id}`} className="text-state-error">
                      缺失：{doc.name}
                    </div>
                  ))}
                  {preview.conflicts?.slice(0, 20).map((item, idx) => (
                    <div key={`conflict-${idx}`} className="text-state-error">
                      冲突：{item.source?.name || '未知文件'}，候选{' '}
                      {item.candidate_count ?? 0} 个
                    </div>
                  ))}
                  {preview.extra_documents?.slice(0, 20).map((doc) => (
                    <div key={`extra-${doc.id}`}>目标多出：{doc.name}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={importLoading}
          >
            取消
          </Button>
          <Button onClick={handleImport} disabled={!canImport}>
            <Upload className="size-4" />
            {importLoading ? '导入中...' : '确认导入'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
