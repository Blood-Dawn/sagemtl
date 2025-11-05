import * as React from 'react';
import * as CheckboxPrimitives from '@radix-ui/react-checkbox';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

type CheckboxProps = React.ComponentPropsWithoutRef<typeof CheckboxPrimitives.Root> & {
  className?: string;
};

const Checkbox = React.forwardRef<React.ElementRef<typeof CheckboxPrimitives.Root>, CheckboxProps>(
  ({ className, children, ...props }, ref) => (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <CheckboxPrimitives.Root
        ref={ref}
        className={cn(
          'inline-flex h-4 w-4 shrink-0 appearance-none items-center justify-center rounded-sm border border-input bg-background text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        )}
        {...props}
      >
        <CheckboxPrimitives.Indicator>
          <Check className="h-3 w-3" />
        </CheckboxPrimitives.Indicator>
      </CheckboxPrimitives.Root>
      {children}
    </div>
  ),
);
Checkbox.displayName = CheckboxPrimitives.Root.displayName;

export { Checkbox };
