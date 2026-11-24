import { Alert, Button } from '@/components/ui';
import { ApiError } from '@/lib/api';

export function ErrorPanel({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  if (!error) return null;
  const message = error instanceof ApiError ? error.message : 'Something went wrong. Please try again.';
  return (
    <Alert variant="error" title="Unable to load this section" className="mb-4">
      <p>{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      )}
    </Alert>
  );
}
