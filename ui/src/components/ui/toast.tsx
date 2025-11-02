import * as ToastPrimitives from '@radix-ui/react-toast';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const ToastProvider = ToastPrimitives.Provider;

const ToastViewport = ({ className, ...props }: ToastPrimitives.ToastViewportProps) => (
  <ToastPrimitives.Viewport
    className={cn('fixed bottom-4 right-4 z-[100] flex max-h-screen w-full max-w-sm flex-col gap-3', className)}
    {...props}
  />
);

const toastVariants = cva(
  'group pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden rounded-xl border border-border/80 bg-card/90 p-4 text-sm shadow-soft transition-all data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=open]:fade-in',
  {
    variants: {
      variant: {
        default: 'border-border/70',
        destructive: 'border-destructive/60 text-destructive-foreground',
        success: 'border-emerald-500/60 text-emerald-100',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

type ToastVariants = VariantProps<typeof toastVariants>;

const Toast = ({ className, variant, ...props }: ToastPrimitives.ToastProps & ToastVariants) => (
  <ToastPrimitives.Root className={cn(toastVariants({ variant }), className)} {...props} />
);

const ToastTitle = ({ className, ...props }: ToastPrimitives.ToastTitleProps) => (
  <ToastPrimitives.Title className={cn('text-sm font-semibold', className)} {...props} />
);

const ToastDescription = ({ className, ...props }: ToastPrimitives.ToastDescriptionProps) => (
  <ToastPrimitives.Description className={cn('text-xs text-muted-foreground', className)} {...props} />
);

const ToastAction = ToastPrimitives.Action;
const ToastClose = ToastPrimitives.Close;

export {
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastAction,
  ToastClose,
};

export type { ToastVariants };
