import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Model, ModelCreate, ModelUpdate, ModelProvider, ProviderCreate } from '@/types/models';
import {
  fetchModels,
  createModel,
  updateModel,
  deleteModel,
  fetchModelProviders,
  createProvider,
} from '@/services/models-management';

export const useModelsManagement = () => {
  const queryClient = useQueryClient();

  // Query for models
  const modelsQuery = useQuery<Model[], Error>({
    queryKey: ['modelsManagement'],
    queryFn: fetchModels,
  });

  // Query for model providers
  const providersQuery = useQuery<ModelProvider[], Error>({
    queryKey: ['modelProviders'],
    queryFn: fetchModelProviders,
  });

  // Mutation for creating models
  const createModelMutation = useMutation<Model, Error, ModelCreate>({
    mutationFn: createModel,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['modelsManagement'] });
      void queryClient.invalidateQueries({ queryKey: ['models'] }); // Also invalidate the old models query
    },
    onError: (error) => {
      console.error('Failed to create model:', error);
    },
  });

  // Mutation for updating models
  const updateModelMutation = useMutation<
    Model,
    Error,
    { model_id: string; modelUpdate: ModelUpdate }
  >({
    mutationFn: ({ model_id, modelUpdate }) => updateModel(model_id, modelUpdate),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['modelsManagement'] });
      void queryClient.invalidateQueries({ queryKey: ['models'] }); // Also invalidate the old models query
    },
    onError: (error) => {
      console.error('Failed to update model:', error);
    },
  });

  // Mutation for deleting models
  const deleteModelMutation = useMutation<void, Error, string>({
    mutationFn: deleteModel,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['modelsManagement'] });
      void queryClient.invalidateQueries({ queryKey: ['models'] }); // Also invalidate the old models query
    },
    onError: (error) => {
      console.error('Failed to delete model:', error);
    },
  });

  // Mutation for creating providers
  const createProviderMutation = useMutation<ModelProvider, Error, ProviderCreate>({
    mutationFn: createProvider,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['modelProviders'] });
    },
    onError: (error) => {
      console.error('Failed to create provider:', error);
    },
  });

  // Helper function to refresh models and providers
  const refreshModels = () => {
    void queryClient.invalidateQueries({ queryKey: ['modelsManagement'] });
    void queryClient.invalidateQueries({ queryKey: ['models'] }); // Also invalidate the old models query
    void queryClient.invalidateQueries({ queryKey: ['modelProviders'] });
  };

  return {
    // Query data and states
    models: modelsQuery.data,
    providers: providersQuery.data,
    isLoading: modelsQuery.isLoading,
    isLoadingProviders: providersQuery.isLoading,
    error: modelsQuery.error,
    providersError: providersQuery.error,

    // Mutations
    createModel: createModelMutation.mutateAsync,
    updateModel: (model_id: string, modelUpdate: ModelUpdate) =>
      updateModelMutation.mutateAsync({ model_id, modelUpdate }),
    deleteModel: deleteModelMutation.mutateAsync,
    createProvider: createProviderMutation.mutateAsync,

    // Mutation states
    isCreating: createModelMutation.isPending,
    isUpdating: updateModelMutation.isPending,
    isDeleting: deleteModelMutation.isPending,
    isCreatingProvider: createProviderMutation.isPending,
    createError: createModelMutation.error,
    updateError: updateModelMutation.error,
    deleteError: deleteModelMutation.error,
    createProviderError: createProviderMutation.error,

    // Mutation resets
    resetCreateError: createModelMutation.reset,
    resetUpdateError: updateModelMutation.reset,
    resetDeleteError: deleteModelMutation.reset,
    resetCreateProviderError: createProviderMutation.reset,

    // Utilities
    refreshModels,
  };
};
