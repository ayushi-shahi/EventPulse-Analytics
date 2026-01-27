import React from 'react';
import { Inbox } from 'lucide-react';
import Button from './Button';

/**
 * Reusable Empty State Component
 */
const EmptyState = ({
  icon: Icon = Inbox,
  title = 'No data',
  description = 'Get started by creating a new item.',
  action = null,
  actionLabel = null,
  onAction = null,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="bg-gray-100 rounded-full p-4 mb-4">
        <Icon className="w-12 h-12 text-gray-400" />
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {title}
      </h3>

      <p className="text-sm text-gray-500 text-center max-w-sm mb-6">
        {description}
      </p>

      {action || (onAction && actionLabel) ? (
        action || (
          <Button onClick={onAction} variant="primary">
            {actionLabel}
          </Button>
        )
      ) : null}
    </div>
  );
};

export default EmptyState;