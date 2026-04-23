import { MCPServer, MCPServerCreate } from '@/types';
import {
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Title,
  Alert,
  FormGroup,
  FormSelect,
  FormSelectOption,
} from '@patternfly/react-core';
import { PlusIcon } from '@patternfly/react-icons';
import { useState, useEffect } from 'react';
import { MCPServerForm } from './MCPServerForm';
import { useMCPServers, useDiscoveredMCPServers } from '@/hooks';

interface NewMCPServerCardProps {
  editingServer?: MCPServer | null;
  onEditComplete?: () => void;
}

export function NewMCPServerCard({ editingServer, onEditComplete }: NewMCPServerCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedDiscoveredServer, setSelectedDiscoveredServer] = useState<string>('');
  const [formDefaults, setFormDefaults] = useState<MCPServer | undefined>(undefined);

  // Use custom hooks
  const {
    createMCPServer,
    updateMCPServer,
    isCreating,
    isUpdating,
    createError,
    updateError,
    resetCreateError,
    resetUpdateError,
  } = useMCPServers();

  // Discover MCP servers only when creating new server (not editing)
  const { discoveredServers, discoverError } = useDiscoveredMCPServers(isOpen && !editingServer);

  // Open card when editing server is set
  useEffect(() => {
    if (editingServer) {
      setIsOpen(true);
    }
  }, [editingServer]);

  // Clear errors when switching between create/edit or changing which server is being edited
  useEffect(() => {
    resetCreateError();
    resetUpdateError();
  }, [editingServer, resetCreateError, resetUpdateError]);

  // Handle discovered server selection
  const handleDiscoveredServerChange = (
    _event: React.FormEvent<HTMLSelectElement>,
    value: string
  ) => {
    setSelectedDiscoveredServer(value);

    if (value === '') {
      // Clear form defaults when "Select..." is chosen
      setFormDefaults(undefined);
      return;
    }

    const server = discoveredServers?.find((s) => s.name === value);
    if (server) {
      // Auto-fill form with discovered server data
      // Note: toolgroup_id will be auto-generated from name in the form
      setFormDefaults({
        toolgroup_id: `mcp::${server.name}`, // Will be auto-generated but set for consistency
        name: server.name,
        description: server.description,
        endpoint_url: server.endpoint_url,
        configuration: {},
        provider_id: 'model-context-protocol', // Required by MCPServer type
      });
    }
  };

  // Reset state when card closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedDiscoveredServer('');
      setFormDefaults(undefined);
    }
  }, [isOpen]);

  const handleSubmit = (values: MCPServerCreate) => {
    void (async () => {
      try {
        if (editingServer) {
          // Update existing server
          await updateMCPServer(editingServer.toolgroup_id, values);
          console.log('MCP server updated successfully');
          onEditComplete?.();
        } else {
          // Create new server
          await createMCPServer(values);
          console.log('MCP server created successfully');
        }
        setIsOpen(false);
      } catch (error) {
        console.error('Error with MCP server operation:', error);
      }
    })();
  };

  const handleCancel = () => {
    resetCreateError();
    resetUpdateError();
    setIsOpen(false);
    onEditComplete?.();
  };

  const isSubmitting = isCreating || isUpdating;
  const error = createError || updateError;

  return (
    <Card isExpanded={isOpen} isClickable={!isOpen} style={{ overflow: 'visible' }}>
      <CardHeader
        selectableActions={{
          onClickAction: () => setIsOpen(!isOpen),
          selectableActionAriaLabelledby: 'clickable-mcp-card-title-1',
        }}
      >
        <CardTitle>
          {!isOpen ? (
            <Flex>
              <FlexItem>
                <PlusIcon />
              </FlexItem>
              <FlexItem>
                <Title headingLevel="h3">
                  {editingServer ? `Edit ${editingServer.name}` : 'New MCP Server'}
                </Title>
              </FlexItem>
            </Flex>
          ) : (
            <Title headingLevel="h3">
              {editingServer ? `Edit ${editingServer.name}` : 'New MCP Server'}
            </Title>
          )}
        </CardTitle>
      </CardHeader>
      <CardExpandableContent style={{ overflow: 'visible' }}>
        <CardBody style={{ overflow: 'visible' }}>
          <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
            {/* Show discovered servers dropdown only when creating new server (not editing) */}
            {!editingServer && discoveredServers && discoveredServers.length > 0 && (
              <FlexItem>
                <FormGroup label="Use Discovered MCP Server" fieldId="discovered-server-select">
                  <FormSelect
                    id="discovered-server-select"
                    value={selectedDiscoveredServer}
                    onChange={handleDiscoveredServerChange}
                    aria-label="Select discovered MCP server"
                  >
                    <FormSelectOption key="empty" value="" label="Select a discovered server..." />
                    {discoveredServers.map((server) => (
                      <FormSelectOption
                        key={server.name}
                        value={server.name}
                        label={`${server.name} (${server.source})`}
                      />
                    ))}
                  </FormSelect>
                </FormGroup>
              </FlexItem>
            )}

            {/* Show discovery error if any */}
            {!editingServer && discoverError && (
              <FlexItem>
                <Alert variant="warning" title="Could not discover MCP servers" isInline>
                  {discoverError.message}
                </Alert>
              </FlexItem>
            )}

            <FlexItem>
              <MCPServerForm
                defaultServer={editingServer || formDefaults}
                isSubmitting={isSubmitting}
                onSubmit={handleSubmit}
                onCancel={handleCancel}
                error={error}
                isEditing={!!editingServer}
              />
            </FlexItem>
          </Flex>
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
