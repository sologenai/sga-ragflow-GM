import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog';
import { Button } from '@/components/ui/button';
import message from '@/components/ui/message';
import {
  useExportKnowledgeGraph,
  useFetchKnowledgeGraph,
} from '@/hooks/use-knowledge-request';
import isEmpty from 'lodash/isEmpty';
import { Download, Trash2, Upload } from 'lucide-react';
import React, { startTransition, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ForceGraph from './force-graph';
import { GraphImportDialog } from './graph-import-dialog';
import { useDeleteKnowledgeGraph } from './use-delete-graph';

const KnowledgeGraph: React.FC = () => {
  const [graphLimit, setGraphLimit] = useState({
    max_nodes: 2000,
    max_edges: 4000,
  });
  const { data, loading } = useFetchKnowledgeGraph(graphLimit);
  const { t } = useTranslation();
  const { handleDeleteKnowledgeGraph } = useDeleteKnowledgeGraph();
  const { loading: exporting, exportKnowledgeGraph } =
    useExportKnowledgeGraph();
  const graphPayload = data?.graph;
  const graphMeta = graphPayload?.graph || {};
  const hasGraph =
    graphMeta.has_graph ||
    !isEmpty(graphPayload?.nodes) ||
    !isEmpty(graphPayload?.edges) ||
    graphMeta.total_nodes > 0 ||
    graphMeta.total_edges > 0;

  const handleExportKnowledgeGraph = useCallback(async () => {
    const ret = (await exportKnowledgeGraph()) as any;
    const response = ret?.response || ret;
    const blob =
      ret?.data instanceof Blob
        ? ret.data
        : response?.blob
          ? await response.blob()
          : undefined;
    if (!blob) {
      message.error('图谱导出失败：没有拿到导出文件');
      return;
    }
    const disposition = response?.headers?.get?.('content-disposition') || '';
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match?.[1] || `ragflow-graphrag-${Date.now()}.zip`;
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }, [exportKnowledgeGraph]);

  const handleRequestMore = useCallback(
    (nextLimit: { max_nodes: number; max_edges: number }) => {
      startTransition(() => {
        setGraphLimit((current) => {
          if (
            nextLimit.max_nodes <= current.max_nodes &&
            nextLimit.max_edges <= current.max_edges
          ) {
            return current;
          }
          return {
            max_nodes: Math.max(current.max_nodes, nextLimit.max_nodes),
            max_edges: Math.max(current.max_edges, nextLimit.max_edges),
          };
        });
      });
    },
    [],
  );

  return (
    <section className={'w-full h-[90dvh] relative p-6'}>
      <div className="absolute right-6 top-6 z-[100] flex max-w-[calc(100%-3rem)] flex-wrap justify-end gap-2 rounded-lg border border-border-button bg-background/80 p-2 shadow-lg backdrop-blur">
        <GraphImportDialog>
          <Button variant="outline" size={'sm'}>
            <Upload className="size-4" /> 导入图谱
          </Button>
        </GraphImportDialog>
        {hasGraph && (
          <Button
            variant="outline"
            size={'sm'}
            disabled={exporting}
            onClick={handleExportKnowledgeGraph}
          >
            <Download className="size-4" />
            {exporting ? '导出中...' : '导出图谱'}
          </Button>
        )}
        {hasGraph && (
          <ConfirmDeleteDialog onOk={handleDeleteKnowledgeGraph}>
            <Button variant="outline" size={'sm'}>
              <Trash2 /> {t('common.delete')}
            </Button>
          </ConfirmDeleteDialog>
        )}
      </div>
      {hasGraph || loading ? (
        <ForceGraph
          data={graphPayload}
          loading={loading}
          onRequestMore={handleRequestMore}
          show
        ></ForceGraph>
      ) : (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-xl rounded-2xl border border-border-button bg-bg-base p-8 text-center shadow-sm">
            <div className="text-xl font-semibold text-text-primary">
              当前知识库尚未生成知识图谱
            </div>
            <div className="mt-3 text-sm leading-6 text-text-secondary">
              可以在文件列表页点击“生成”构建图谱；如果已有其他环境导出的图谱包，也可以直接导入，系统会先检查文件映射，缺文件或冲突时不会写入。
            </div>
            <div className="mt-6 flex justify-center">
              <GraphImportDialog>
                <Button>
                  <Upload className="size-4" /> 导入图谱
                </Button>
              </GraphImportDialog>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default KnowledgeGraph;
