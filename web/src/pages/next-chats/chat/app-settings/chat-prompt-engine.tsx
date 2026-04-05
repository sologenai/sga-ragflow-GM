'use client';

import { CrossLanguageFormField } from '@/components/cross-language-form-field';
import { RerankFormFields } from '@/components/rerank';
import { SimilaritySliderFormField } from '@/components/similarity-slider';
import { SwitchFormField } from '@/components/switch-fom-field';
import { TopNFormField } from '@/components/top-n-item';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { RAGFlowSelect } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { UseKnowledgeGraphFormField } from '@/components/use-knowledge-graph-item';
import { useTranslate } from '@/hooks/common-hooks';
import { useFormContext } from 'react-hook-form';
import { DynamicVariableForm } from './dynamic-variable';

export function ChatPromptEngine() {
  const { t } = useTranslate('chat');
  const form = useFormContext();

  return (
    <div className="space-y-8">
      <FormField
        control={form.control}
        name="prompt_config.system"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('system')}</FormLabel>
            <FormControl>
              <Textarea
                {...field}
                rows={8}
                placeholder={t('messagePlaceholder')}
                className="overflow-y-auto"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <SimilaritySliderFormField isTooltipShown></SimilaritySliderFormField>
      <TopNFormField></TopNFormField>
      <SwitchFormField
        name={'prompt_config.refine_multiturn'}
        label={t('multiTurn')}
        tooltip={t('multiTurnTip')}
      ></SwitchFormField>
      <FormField
        control={form.control}
        name="prompt_config.retrieval_mode"
        render={({ field }) => (
          <FormItem>
            <FormLabel tooltip={t('retrievalModeTip')}>
              {t('retrievalMode')}
            </FormLabel>
            <FormControl>
              <RAGFlowSelect
                value={field.value || 'auto'}
                onChange={field.onChange}
                options={[
                  { label: t('retrievalModeAuto'), value: 'auto' },
                  { label: t('retrievalModeAlways'), value: 'always' },
                  { label: t('retrievalModeOff'), value: 'off' },
                ]}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <UseKnowledgeGraphFormField name="prompt_config.use_kg"></UseKnowledgeGraphFormField>
      <RerankFormFields></RerankFormFields>
      <CrossLanguageFormField></CrossLanguageFormField>
      <DynamicVariableForm></DynamicVariableForm>
    </div>
  );
}
