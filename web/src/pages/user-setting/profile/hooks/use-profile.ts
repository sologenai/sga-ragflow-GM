// src/hooks/useProfile.ts
import message from '@/components/ui/message';
import {
  useFetchUserInfo,
  useSaveSetting,
} from '@/hooks/use-user-setting-request';
import { rsaPsw } from '@/utils';
import { useCallback, useEffect, useState } from 'react';

interface ProfileData {
  userName: string;
  timeZone: string;
  currPasswd?: string;
  newPasswd?: string;
  avatar: string;
  email: string;
  confirmPasswd?: string;
}

export const EditType = {
  editName: 'editName',
  editTimeZone: 'editTimeZone',
  editPassword: 'editPassword',
} as const;

export type IEditType = keyof typeof EditType;

export const modalTitle = {
  [EditType.editName]: 'Edit Name',
  [EditType.editTimeZone]: 'Edit Time Zone',
  [EditType.editPassword]: 'Edit Password',
} as const;

export const useProfile = () => {
  const { data: userInfo } = useFetchUserInfo();
  const [profile, setProfile] = useState<ProfileData>({
    userName: '',
    avatar: '',
    timeZone: '',
    email: '',
    currPasswd: '',
  });

  const [editType, setEditType] = useState<IEditType>(EditType.editName);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<ProfileData>>({});
  const { saveSetting, loading: submitLoading } = useSaveSetting();

  useEffect(() => {
    // form.setValue('currPasswd', ''); // current password
    const profile = {
      userName: userInfo.nickname,
      timeZone: userInfo.timezone,
      avatar: userInfo.avatar || '',
      email: userInfo.email,
      currPasswd: userInfo.password,
    };
    setProfile(profile);
  }, [userInfo, setProfile]);

  const onSubmit = async (newProfile: ProfileData) => {
    const payload: Partial<{
      nickname: string;
      password: string;
      new_password: string;
      avatar: string;
      timezone: string;
    }> = {
      nickname: newProfile.userName,
      avatar: newProfile.avatar,
      timezone: newProfile.timeZone,
    };

    if (
      'currPasswd' in newProfile &&
      'newPasswd' in newProfile &&
      newProfile.currPasswd &&
      newProfile.newPasswd
    ) {
      payload.password = rsaPsw(newProfile.currPasswd!) as string;
      payload.new_password = rsaPsw(newProfile.newPasswd!) as string;
    }

    if (editType === EditType.editName && payload.nickname) {
      const code = await saveSetting({ nickname: payload.nickname });
      return code;
    }

    if (editType === EditType.editTimeZone && payload.timezone) {
      const code = await saveSetting({ timezone: payload.timezone });
      return code;
    }

    if (editType === EditType.editPassword && payload.password) {
      const code = await saveSetting({
        password: payload.password,
        new_password: payload.new_password,
      });
      return code;
    }

    message.error('Failed to submit profile changes.');
    return undefined;
  };

  const handleEditClick = useCallback(
    (type: IEditType) => {
      setEditForm(profile);
      setEditType(type);
      setIsEditing(true);
    },
    [profile],
  );

  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setEditForm({});
  }, []);

  const handleSave = async (data: ProfileData) => {
    const newProfile = { ...profile, ...data };

    try {
      const code = await onSubmit(newProfile);
      if (code === 0) {
        setIsEditing(false);
        setEditForm({});
        setProfile(newProfile);
      }
    } catch (_error) {
      message.error('Failed to save profile changes.');
    }
  };

  const handleAvatarUpload = (avatar: string) => {
    setProfile((prev) => ({ ...prev, avatar }));
    saveSetting({ avatar });
  };

  return {
    profile,
    setProfile,
    submitLoading: submitLoading,
    isEditing,
    editType,
    editForm,
    handleEditClick,
    handleCancel,
    handleSave,
    handleAvatarUpload,
  };
};
