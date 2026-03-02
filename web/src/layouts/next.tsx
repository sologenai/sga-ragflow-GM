import { useIdleTimeout } from '@/hooks/use-idle-timeout';
import { Outlet } from 'react-router';
import { Header } from './next-header';

export default function NextLayout() {
  useIdleTimeout();

  return (
    <main className="h-full flex flex-col">
      <Header />
      <Outlet />
    </main>
  );
}
