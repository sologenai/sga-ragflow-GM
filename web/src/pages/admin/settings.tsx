import { useTranslation } from 'react-i18next';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LucideInfo } from 'lucide-react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import {
  getSystemSettings,
  updateSystemSettings,
} from '@/services/admin-service';

const AdminSettings = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = useQuery({
    queryKey: ['admin/systemSettings'],
    queryFn: async () => {
      const res = await getSystemSettings();
      return res?.data?.data;
    },
  });

  const updateMutation = useMutation({
    mutationFn: updateSystemSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin/systemSettings'] });
    },
  });

  const handleGlobalLlmToggle = (checked: boolean) => {
    updateMutation.mutate({ global_llm_enabled: checked });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>{t('admin.systemSettings')}</CardTitle>
        <CardDescription>
          {t('admin.systemSettingsDescription')}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Global LLM Switch */}
        <div className="flex items-center justify-between p-4 border rounded-lg">
          <div className="flex items-center gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Label
                  htmlFor="global-llm-switch"
                  className="text-base font-medium"
                >
                  {t('admin.globalLlmEnabled')}
                </Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <LucideInfo className="size-4 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-xs">
                    <p>{t('admin.globalLlmEnabledTip')}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-sm text-muted-foreground">
                {settings?.global_llm_enabled
                  ? t('admin.globalLlmEnabledDesc')
                  : t('admin.globalLlmDisabledDesc')}
              </p>
            </div>
          </div>
          <Switch
            id="global-llm-switch"
            checked={settings?.global_llm_enabled ?? true}
            onCheckedChange={handleGlobalLlmToggle}
            disabled={updateMutation.isPending}
          />
        </div>
      </CardContent>
    </Card>
  );
};

export default AdminSettings;
