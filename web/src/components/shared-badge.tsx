import { PropsWithChildren } from 'react';

export function SharedBadge({ children }: PropsWithChildren) {
  if (!children) {
    return null;
  }

  return <span className="bg-bg-card rounded-sm px-1 text-xs">{children}</span>;
}
