import { Alert, Button, Flex, FlexItem, PageSection, Spinner, Title } from '@patternfly/react-core';
import { SyncIcon } from '@patternfly/react-icons';
import { createFileRoute } from '@tanstack/react-router';
import React, { useState } from 'react';
import { useModelsManagement } from '@/hooks/useModelsManagement';
import { NewProviderCard } from '@/components/NewProviderCard';
import { ProviderCard } from '@/components/ProviderCard';
import { useQueryClient } from '@tanstack/react-query';

export const Route = createFileRoute('/_protected/_admin/config/models')({
  component: Models,
});

function Models() {
  const queryClient = useQueryClient();
  const [lastFetchTime, setLastFetchTime] = useState<string>('');

  const {
    providers,
    models,
    isLoadingProviders,
    isLoading: isLoadingModels,
    providersError,
    error: modelsError,
    refreshModels,
  } = useModelsManagement();

  // Filter to only show inference providers
  const inferenceProviders = providers?.filter((p) => p.api === 'inference') || [];

  // Get dataUpdatedAt from the underlying query for timestamp tracking
  const { dataUpdatedAt } = queryClient.getQueryState(['modelsManagement']) || {};

  // Update timestamp when data is fetched
  React.useEffect(() => {
    if (dataUpdatedAt) {
      setLastFetchTime(new Date(dataUpdatedAt).toLocaleString());
    }
  }, [dataUpdatedAt]);

  const handleRefresh = () => {
    refreshModels();
  };

  const isLoading = isLoadingProviders || isLoadingModels;
  const hasError = providersError || modelsError;

  return (
    <PageSection>
      {/* Header with title, refresh button, and timestamp */}
      <Flex
        justifyContent={{ default: 'justifyContentSpaceBetween' }}
        alignItems={{ default: 'alignItemsCenter' }}
        className="pf-v6-u-mb-md"
      >
        <FlexItem>
          <Title headingLevel="h1">Model Providers</Title>
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
                isLoading={isLoading}
                aria-label="Refresh providers and models"
              >
                Refresh
              </Button>
            </FlexItem>
          </Flex>
        </FlexItem>
      </Flex>

      {/* Content */}
      {isLoading && <Spinner aria-label="Loading providers and models" />}
      {hasError && (
        <Alert
          variant="danger"
          title={providersError ? 'Error loading providers' : 'Error loading models'}
        >
          {(providersError || modelsError)?.message}
        </Alert>
      )}

      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        <NewProviderCard />

        {!isLoading &&
          !hasError &&
          inferenceProviders.length > 0 &&
          inferenceProviders.map((provider) => {
            // Filter models for this provider
            const providerModels =
              models?.filter((model) => model.provider_id === provider.provider_id) || [];

            return (
              <ProviderCard
                key={provider.provider_id}
                provider={provider}
                models={providerModels}
              />
            );
          })}

        {!isLoading && !hasError && inferenceProviders.length === 0 && (
          <p>No providers configured yet.</p>
        )}
      </Flex>
    </PageSection>
  );
}
