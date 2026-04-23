import { NewAgent } from '@/types/agent';
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
import { useAgents } from '@/hooks';
import { useState } from 'react';
import { AgentForm } from './agent-form';

export function NewAgentCard() {
  const [isOpen, setIsOpen] = useState(false);

  // Use agents hook for creating agents
  const { createAgent, isCreating, createError, resetCreateError } = useAgents();

  const handleCreateAgent = (values: NewAgent) => {
    void (async () => {
      try {
        await createAgent(values);
        setIsOpen(false);
      } catch (error) {
        console.error('Error creating agent:', error);
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
          selectableActionAriaLabelledby: 'clickable-card-example-title-1',
        }}
      >
        <CardTitle>
          {!isOpen ? (
            <Flex>
              <FlexItem>
                <PlusIcon />
              </FlexItem>
              <FlexItem>
                <Title headingLevel="h3">New Agent</Title>
              </FlexItem>
            </Flex>
          ) : (
            <Title headingLevel="h3">New Agent</Title>
          )}
        </CardTitle>
      </CardHeader>
      <CardExpandableContent style={{ overflow: 'visible' }}>
        <CardBody style={{ overflow: 'visible' }}>
          <AgentForm
            onSubmit={handleCreateAgent}
            isSubmitting={isCreating}
            onCancel={handleCancel}
            error={createError}
          />
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
