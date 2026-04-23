import { Alert, Button, Flex, FlexItem, Spinner, Title } from '@patternfly/react-core';
import { SyncIcon } from '@patternfly/react-icons';
import { useModelsManagement } from '@/hooks/useModelsManagement';
import React, { useState } from 'react';
import { ModelCard } from '@/components/ModelCard';
import { useQueryClient } from '@tanstack/react-query';

export function ModelList() {
  const queryClient = useQueryClient();
  const [lastFetchTime, setLastFetchTime] = useState<string>('');

  // Use custom models hook
  const {
    models,
    isLoading: isLoadingModels,
    error: modelsError,
    deleteModel,
    isDeleting,
    deleteError,
    resetDeleteError,
    refreshModels,
  } = useModelsManagement();

  // Get dataUpdatedAt from the underlying query for timestamp tracking
  const { dataUpdatedAt } = queryClient.getQueryState(['modelsManagement']) || {};

  // Update timestamp when data is fetched
  React.useEffect(() => {
    if (dataUpdatedAt) {
      setLastFetchTime(new Date(dataUpdatedAt).toLocaleString());
    }
  }, [dataUpdatedAt]);

  const handleDeleteModel = (model_id: string) => {
    void (async () => {
      try {
        await deleteModel(model_id);
        console.log('Model deleted successfully');
      } catch (error) {
        console.error('Error deleting model:', error);
      }
    })();
  };

  const handleRefresh = () => {
    refreshModels();
  };

  return (
    <div>
      {/* Header with title, refresh button, and timestamp */}
      <Flex
        justifyContent={{ default: 'justifyContentSpaceBetween' }}
        alignItems={{ default: 'alignItemsCenter' }}
        className="pf-v6-u-mb-md"
      >
        <FlexItem>
          <Title headingLevel="h2">Models</Title>
        </FlexItem>
        <FlexItem>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
            {lastFetchTime && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle pf-v6-u-font-size-sm">
                  Last updated: {lastFetchTime}
                </span>
              </FlexItem>
            )}
            <FlexItem>
              <Button
                variant="plain"
                icon={<SyncIcon />}
                onClick={handleRefresh}
                isLoading={isLoadingModels}
                aria-label="Refresh models"
              >
                Refresh
              </Button>
            </FlexItem>
          </Flex>
        </FlexItem>
      </Flex>

      {/* Content */}
      {isLoadingModels && <Spinner aria-label="Loading models" />}
      {modelsError && (
        <Alert variant="danger" title="Error loading models">
          {modelsError.message}
        </Alert>
      )}
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        {!isLoadingModels &&
          !modelsError &&
          models &&
          models.length > 0 &&
          models
            .sort((a, b) => Date.parse(b.created_at ?? '') - Date.parse(a.created_at ?? ''))
            .map((model) => (
              <ModelCard
                key={model.model_id}
                model={model}
                onDelete={handleDeleteModel}
                isDeleting={isDeleting}
                deleteError={deleteError}
                resetDeleteError={resetDeleteError}
              />
            ))}
        {!isLoadingModels && !modelsError && models && models.length === 0 && (
          <p>
            No models auto-registered yet. Models will appear here when providers discover them.
          </p>
        )}
      </Flex>
    </div>
  );
}
