/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import {
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
  type ToastVariants,
} from '@/components/ui/toast';
import { Button } from '@/components/ui/button';

export type ToastMessage = {
  id: string;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  variant?: ToastVariants['variant'];
};

type ToastContextValue = {
  push: (toast: Omit<ToastMessage, 'id'>) => void;
};

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a Toaster');
  }
  return ctx;
}

export function Toaster({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const push = useCallback((toast: Omit<ToastMessage, 'id'>) => {
    setToasts((prev) => [...prev, { ...toast, id: crypto.randomUUID() }]);
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      <ToastProvider swipeDirection="right">
        {children}
        <ToastViewport />
        {toasts.map(({ id, title, description, actionLabel, onAction, variant }) => (
          <Toast key={id} variant={variant} onOpenChange={(open) => !open && dismiss(id)}>
            <div className="flex flex-1 flex-col gap-1">
              <ToastTitle>{title}</ToastTitle>
              {description ? <ToastDescription>{description}</ToastDescription> : null}
            </div>
            {actionLabel ? (
              <Button
                variant="ghost"
                size="sm"
                className="ml-2"
                onClick={() => {
                  onAction?.();
                  dismiss(id);
                }}
              >
                {actionLabel}
              </Button>
            ) : null}
            <ToastClose className="ml-2 text-muted-foreground">✕</ToastClose>
          </Toast>
        ))}
      </ToastProvider>
    </ToastContext.Provider>
  );
}
