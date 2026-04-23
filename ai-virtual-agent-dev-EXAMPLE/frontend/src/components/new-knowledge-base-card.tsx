import { KnowledgeBase } from '@/types';
import {
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Title,
} from '@patternfly/react-core';
import { PlusIcon } from '@patternfly/react-icons';
import { useState } from 'react';
import { KnowledgeBaseForm } from './knowledge-base-form';
import { useModels, useKnowledgeBases } from '@/hooks';

export function NewKnowledgeBaseCard() {
  const [isOpen, setIsOpen] = useState(false);

  // Use custom hooks
  const {
    embeddingModels,
    isLoadingEmbeddingModels,
    embeddingModelsError,
    providers,
    isLoadingProviders,
    providersError,
  } = useModels();
  const { createKnowledgeBase, isCreating, createError, resetCreateError } = useKnowledgeBases();

  const handleCreateKb = (values: KnowledgeBase) => {
    // Strip out fields that shouldn't be sent to the API
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { created_at, updated_at, ...createPayload } = values;
    void (async () => {
      try {
        await createKnowledgeBase(createPayload);
        setIsOpen(false);
        console.log('Knowledge base created successfully');
      } catch (error) {
        console.error('Error creating knowledge base:', error);
      }
    })();
  };

  const handleCancel = () => {
    resetCreateError();
    setIsOpen(false);
  };

  return (
    <Card isExpanded={isOpen} isClickable={!isOpen} style={{ overflow: 'visible' }}>
      <CardHeader
        selectableActions={{
          onClickAction: () => setIsOpen(!isOpen),
          selectableActionAriaLabelledby: 'clickable-kb-card-title-1',
        }}
      >
        <CardTitle>
          {!isOpen ? (
            <Flex>
              <FlexItem>
                <PlusIcon />
              </FlexItem>
              <FlexItem>
                <Title headingLevel="h3">New Knowledge Base</Title>
              </FlexItem>
            </Flex>
          ) : (
            <Title headingLevel="h3">New Knowledge Base</Title>
          )}
        </CardTitle>
      </CardHeader>
      <CardExpandableContent style={{ overflow: 'visible' }}>
        <CardBody style={{ overflow: 'visible' }}>
          <KnowledgeBaseForm
            embeddingModelProps={{
              models: embeddingModels ?? [],
              isLoadingModels: isLoadingEmbeddingModels,
              modelsError: embeddingModelsError,
            }}
            providersProps={{
              providers: providers ?? [],
              isLoadingProviders,
              providersError,
            }}
            isSubmitting={isCreating}
            onSubmit={handleCreateKb}
            onCancel={handleCancel}
            error={createError}
          />
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
