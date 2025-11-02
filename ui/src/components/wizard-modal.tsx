import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

export type WizardStep = {
  title: string;
  description?: string;
  content: React.ReactNode;
};

export type WizardModalProps = {
  trigger: React.ReactNode;
  steps: WizardStep[];
  onFinish: () => void;
};

export function WizardModal({ trigger, steps, onFinish }: WizardModalProps) {
  const [open, setOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const current = steps[stepIndex];

  const next = () => {
    if (stepIndex < steps.length - 1) {
      setStepIndex((index) => index + 1);
    } else {
      onFinish();
      setOpen(false);
      setStepIndex(0);
    }
  };

  const back = () => {
    if (stepIndex === 0) return;
    setStepIndex((index) => index - 1);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        if (!value) {
          setStepIndex(0);
        }
      }}
    >
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{current.title}</DialogTitle>
          {current.description ? <DialogDescription>{current.description}</DialogDescription> : null}
        </DialogHeader>
        <Separator className="my-2" />
        <div className="space-y-4">{current.content}</div>
        <DialogFooter>
          <div className="flex flex-1 items-center justify-between">
            <div className="text-xs text-muted-foreground">
              Step {stepIndex + 1} of {steps.length}
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={back} disabled={stepIndex === 0}>
                Back
              </Button>
              <Button onClick={next}>{stepIndex === steps.length - 1 ? 'Finish' : 'Next'}</Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
