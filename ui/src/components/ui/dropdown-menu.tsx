import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu';
import { cn } from '@/lib/utils';

const DropdownMenu = DropdownMenuPrimitive.Root;
const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
const DropdownMenuGroup = DropdownMenuPrimitive.Group;
const DropdownMenuPortal = DropdownMenuPrimitive.Portal;
const DropdownMenuSub = DropdownMenuPrimitive.Sub;
const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup;

const DropdownMenuSubTrigger = ({ className, inset, ...props }: DropdownMenuPrimitive.DropdownMenuSubTriggerProps & { inset?: boolean }) => (
  <DropdownMenuPrimitive.SubTrigger
    className={cn(
      'flex cursor-pointer select-none items-center rounded-md px-2 py-1.5 text-sm outline-none focus:bg-secondary/70 data-[state=open]:bg-secondary/80',
      inset && 'pl-8',
      className,
    )}
    {...props}
  />
);

const DropdownMenuSubContent = ({ className, ...props }: DropdownMenuPrimitive.DropdownMenuSubContentProps) => (
  <DropdownMenuPrimitive.SubContent
    className={cn('z-50 min-w-[8rem] overflow-hidden rounded-xl border border-border/60 bg-card/90 p-1 text-foreground shadow-soft', className)}
    {...props}
  />
);

const DropdownMenuContent = ({ className, sideOffset = 6, ...props }: DropdownMenuPrimitive.DropdownMenuContentProps) => (
  <DropdownMenuPrimitive.Portal>
    <DropdownMenuPrimitive.Content
      sideOffset={sideOffset}
      className={cn('z-50 min-w-[12rem] overflow-hidden rounded-xl border border-border/60 bg-card/90 p-1 text-foreground shadow-soft backdrop-blur', className)}
      {...props}
    />
  </DropdownMenuPrimitive.Portal>
);

const DropdownMenuItem = ({ className, inset, ...props }: DropdownMenuPrimitive.DropdownMenuItemProps & { inset?: boolean }) => (
  <DropdownMenuPrimitive.Item
    className={cn('relative flex cursor-pointer select-none items-center rounded-md px-2 py-1.5 text-sm outline-none transition-colors focus:bg-secondary/70 focus:text-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50', inset && 'pl-8', className)}
    {...props}
  />
);

const DropdownMenuLabel = ({ className, inset, ...props }: DropdownMenuPrimitive.DropdownMenuLabelProps & { inset?: boolean }) => (
  <DropdownMenuPrimitive.Label
    className={cn('px-2 py-1.5 text-xs font-semibold text-muted-foreground', inset && 'pl-8', className)}
    {...props}
  />
);

const DropdownMenuSeparator = ({ className, ...props }: DropdownMenuPrimitive.DropdownMenuSeparatorProps) => (
  <DropdownMenuPrimitive.Separator className={cn('my-1 h-px bg-border/60', className)} {...props} />
);

const DropdownMenuShortcut = ({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) => (
  <span className={cn('ml-auto text-xs tracking-widest text-muted-foreground', className)} {...props} />
);

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuGroup,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuRadioGroup,
};
