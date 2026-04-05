import { SwitchLogicOperator } from '@/constants/agent';
import { buildOptions } from '@/utils/form';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

const modelTypeFallbackLabels: Record<string, string> = {
  chat: 'Chat',
  embedding: 'Embedding',
  rerank: 'Rerank',
  sequence2text: 'Sequence2Text',
  tts: 'TTS',
  image2text: 'OCR',
  speech2text: 'ASR',
};

export function useBuildSwitchLogicOperatorOptions() {
  const { t } = useTranslation();
  return buildOptions(
    SwitchLogicOperator,
    t,
    'flow.switchLogicOperatorOptions',
  );
}

export function useBuildModelTypeOptions() {
  const { t } = useTranslation();

  const buildModelTypeOptions = useCallback(
    (list: string[]) => {
      return list.map((x) => ({
        value: x,
        label: (() => {
          const key = `setting.modelTypes.${x}`;
          const translated = t(key);
          return translated === key
            ? modelTypeFallbackLabels[x] || x
            : translated;
        })(),
      }));
    },
    [t],
  );

  return {
    buildModelTypeOptions,
  };
}
