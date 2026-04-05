import { useUpdateKnowledge } from '@/hooks/use-knowledge-request';
import {
  IKnowledge,
  KnowledgeBaseLabelValue,
} from '@/interfaces/database/knowledge';
import { useCallback } from 'react';

export const useLabelDataset = () => {
  const { saveKnowledgeConfiguration, loading } = useUpdateKnowledge(true);

  const labelDataset = useCallback(
    async (dataset: IKnowledge, label: KnowledgeBaseLabelValue) => {
      await saveKnowledgeConfiguration({
        kb_id: dataset.id,
        name: dataset.name,
        description: dataset.description ?? '',
        parser_id: dataset.parser_id,
        kb_label: label,
      });
    },
    [saveKnowledgeConfiguration],
  );

  return { labelDataset, loading };
};
