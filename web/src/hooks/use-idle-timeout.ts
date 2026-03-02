import { Routes } from '@/routes';
import storage from '@/utils/authorization-util';
import { useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';

const IDLE_TIMEOUT = 55 * 60 * 1000; // 55 minutes (slightly less than backend 60min)
const ACTIVITY_EVENTS = [
  'mousedown',
  'keydown',
  'scroll',
  'touchstart',
] as const;

export function useIdleTimeout() {
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const navigate = useNavigate();

  const handleTimeout = useCallback(() => {
    storage.removeAll();
    navigate(Routes.Login);
  }, [navigate]);

  const resetTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(handleTimeout, IDLE_TIMEOUT);
  }, [handleTimeout]);

  useEffect(() => {
    ACTIVITY_EVENTS.forEach((evt) => window.addEventListener(evt, resetTimer));
    resetTimer();
    return () => {
      ACTIVITY_EVENTS.forEach((evt) =>
        window.removeEventListener(evt, resetTimer),
      );
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [resetTimer]);
}
