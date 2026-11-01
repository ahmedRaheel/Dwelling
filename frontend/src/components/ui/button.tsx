import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-[3px] font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#a66849] disabled:pointer-events-none',
  {
    variants: {
      variant: {
        default: 'bg-[#283d31] text-white hover:bg-[#3b5343]',
        outline: 'border border-[#d8d6cc] bg-white text-[#2a3a2d] hover:bg-[#f1eee7]',
        ghost: 'text-[#3d4e40] hover:bg-[#edeae1]',
        destructive: 'bg-[#a34e3d] text-white hover:bg-[#893e30]',
      },
      size: { default: 'h-11 px-5 text-sm', sm: 'h-9 px-3 text-xs', lg: 'h-12 px-7 text-base', icon: 'size-10' },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
);

type ButtonProps = React.ComponentProps<'button'> & VariantProps<typeof buttonVariants> & { asChild?: boolean };
export function Button({ className, variant, size, asChild, ...props }: ButtonProps) {
  const Component = asChild ? Slot : 'button';
  return <Component data-slot="button" className={cn(buttonVariants({ variant, size }), className)} {...props}/>;
}
