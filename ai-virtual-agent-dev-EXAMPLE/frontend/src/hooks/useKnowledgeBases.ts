import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { KnowledgeBase, KnowledgeBaseWithStatus } from '@/types';
import {
  fetchKnowledgeBasesWithStatus,
  createKnowledgeBase,
  deleteKnowledgeBase,
} from '@/services/knowledge-bases';

export const useKnowledgeBases = () => {
  const queryClient = useQueryClient();

  // Query for knowledge bases with status
  const knowledgeBasesQuery = useQuery<KnowledgeBaseWithStatus[], Error>({
    queryKey: ['knowledgeBases'],
    queryFn: fetchKnowledgeBasesWithStatus,
  });

  // Mutation for creating knowledge bases
  const createKnowledgeBaseMutation = useMutation<
    KnowledgeBase,
    Error,
    Omit<KnowledgeBase, 'created_at' | 'updated_at'>
  >({
    mutationFn: createKnowledgeBase,
    onSuccess: () => {
      // Invalidate all knowledge base queries
      void queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
    },
    onError: (error) => {
      console.error('Failed to create knowledge base:', error);
    },
  });

  // Mutation for deleting knowledge bases
  const deleteKnowledgeBaseMutation = useMutation<void, Error, string>({
    mutationFn: deleteKnowledgeBase,
    onSuccess: () => {
      // Invalidate all knowledge base queries
      void queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
    },
    onError: (error) => {
      console.error('Failed to delete knowledge base:', error);
    },
  });

  // Helper function to refresh knowledge bases
  const refreshKnowledgeBases = () => {
    void queryClient.invalidateQueries({ queryKey: ['knowledgeBases'] });
  };

  return {
    // Query data and states
    knowledgeBases: knowledgeBasesQuery.data,
    isLoading: knowledgeBasesQuery.isLoading,
    error: knowledgeBasesQuery.error,

    // Mutations
    createKnowledgeBase: createKnowledgeBaseMutation.mutateAsync,
    deleteKnowledgeBase: deleteKnowledgeBaseMutation.mutateAsync,

    // Mutation states
    isCreating: createKnowledgeBaseMutation.isPending,
    isDeleting: deleteKnowledgeBaseMutation.isPending,
    createError: createKnowledgeBaseMutation.error,
    deleteError: deleteKnowledgeBaseMutation.error,

    // Error reset functions
    resetCreateError: createKnowledgeBaseMutation.reset,
    resetDeleteError: deleteKnowledgeBaseMutation.reset,

    // Utilities
    refreshKnowledgeBases,
  };
};
