import { useTranslation } from 'react-i18next';
import { SwitchFormField } from './switch-fom-field';

interface UseKnowledgeGraphFormFieldProps {
  name: string;
}

export function UseKnowledgeGraphFormField({
  name,
}: UseKnowledgeGraphFormFieldProps) {
  const { t } = useTranslation();
  const tooltip = `${t('chat.useKnowledgeGraphTip')} ${t(
    'chat.useKnowledgeGraphAsEnhancement',
    {
      defaultValue:
        'Graph retrieval is an enhancement layer on top of standard retrieval.',
    },
  )}`;

  return (
    <SwitchFormField
      name={name}
      label={t('chat.useKnowledgeGraph')}
      tooltip={tooltip}
    ></SwitchFormField>
  );
}
