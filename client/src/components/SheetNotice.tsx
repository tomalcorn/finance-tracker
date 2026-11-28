import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';

type SheetNoticeProps = {
  /** What is missing, e.g. "You need a bank account to bank from." */
  message: string;
  /** Where to go to put it right. */
  detail: string;
  onClose: () => void;
};

/** A sheet's content in place of a form that can't be filled in yet, with a way to close it. */
export function SheetNotice({ message, detail, onClose }: SheetNoticeProps) {
  return (
    <>
      <AppText>{message}</AppText>
      <AppText tone="muted">{detail}</AppText>
      <Button title="Close" variant="plain" onPress={onClose} />
    </>
  );
}
