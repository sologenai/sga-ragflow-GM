import { ConfirmDeleteDialog } from '@/components/confirm-delete-dialog';
import { Button } from '@/components/ui/button';
import { useFetchKnowledgeGraph } from '@/hooks/use-knowledge-request';
import { Trash2 } from 'lucide-react';
import React, { startTransition, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ForceGraph from './force-graph';
import { useDeleteKnowledgeGraph } from './use-delete-graph';

const KnowledgeGraph: React.FC = () => {
  const [graphLimit, setGraphLimit] = useState({
    max_nodes: 2000,
    max_edges: 4000,
  });
  const { data, loading } = useFetchKnowledgeGraph(graphLimit);
  const { t } = useTranslation();
  const { handleDeleteKnowledgeGraph } = useDeleteKnowledgeGraph();
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
      <ConfirmDeleteDialog onOk={handleDeleteKnowledgeGraph}>
        <Button
          variant="outline"
          size={'sm'}
          className="absolute right-0 top-0 z-50"
        >
          <Trash2 /> {t('common.delete')}
        </Button>
      </ConfirmDeleteDialog>
      <ForceGraph
        data={data?.graph}
        loading={loading}
        onRequestMore={handleRequestMore}
        show
      ></ForceGraph>
    </section>
  );
};

export default KnowledgeGraph;
