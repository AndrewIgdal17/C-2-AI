import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  CardExpandableContent,
  Dropdown,
  DropdownList,
  DropdownItem,
  MenuToggle,
  MenuToggleElement,
  Title,
  Flex,
  FlexItem,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Icon,
  Alert,
  Label,
} from '@patternfly/react-core';
import { EllipsisVIcon, TrashIcon } from '@patternfly/react-icons';
import { useState, Fragment } from 'react';
import { Model } from '@/types/models';

interface ModelCardProps {
  model: Model;
  onDelete?: (model_id: string) => void;
  isDeleting?: boolean;
  deleteError?: Error | null;
  resetDeleteError?: () => void;
}

export function ModelCard({
  model,
  onDelete,
  isDeleting = false,
  deleteError,
  resetDeleteError,
}: ModelCardProps) {
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [modalOpen, setModalOpen] = useState<boolean>(false);

  const onExpand = () => setIsExpanded(!isExpanded);

  const toggleModal = () => {
    if (modalOpen && resetDeleteError) {
      // Clear error when closing modal
      resetDeleteError();
    }
    setModalOpen(!modalOpen);
  };

  const handleDeleteModel = () => {
    onDelete?.(model.model_id);
  };

  const dropdownItems = (
    <>
      <DropdownItem
        isDanger
        icon={<TrashIcon />}
        value={0}
        key="delete"
        onClick={() => {
          toggleModal();
          setDropdownOpen(false);
        }}
      >
        Delete
      </DropdownItem>
    </>
  );

  const headerActions = (
    <Fragment>
      <Dropdown
        isOpen={dropdownOpen}
        onOpenChange={(isOpen: boolean) => setDropdownOpen(isOpen)}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            aria-label="kebab dropdown toggle"
            variant="plain"
            onClick={(e) => {
              e.stopPropagation(); // Prevent header click
              setDropdownOpen(!dropdownOpen);
            }}
            isExpanded={dropdownOpen}
            icon={
              <Icon iconSize="lg">
                <EllipsisVIcon />
              </Icon>
            }
          />
        )}
        shouldFocusToggleOnSelect
        popperProps={{ position: 'right' }}
      >
        <DropdownList>{dropdownItems}</DropdownList>
      </Dropdown>
      <Modal
        isOpen={modalOpen}
        onClose={toggleModal}
        variant="small"
        aria-labelledby="delete-model-modal-title"
        aria-describedby="delete-model-modal-desc"
      >
        <ModalHeader title="Delete Model" labelId="delete-model-modal-title" />
        <ModalBody id="delete-model-modal-desc">
          {deleteError ? (
            <Alert variant="danger" title="Error deleting model" isInline>
              {deleteError.message}
            </Alert>
          ) : (
            'Are you sure you want to delete this model? This action cannot be undone.'
          )}
        </ModalBody>
        {!deleteError && (
          <ModalFooter>
            <Button isLoading={isDeleting} onClick={handleDeleteModel} variant="danger">
              Delete
            </Button>
            <Button variant="link" onClick={toggleModal}>
              Cancel
            </Button>
          </ModalFooter>
        )}
      </Modal>
    </Fragment>
  );

  return (
    <Card id={`expandable-model-card-${model.model_id}`} isExpanded={isExpanded}>
      <CardHeader
        actions={{ actions: headerActions }}
        onExpand={onExpand}
        toggleButtonProps={{
          id: `toggle-model-button-${model.model_id}`,
          'aria-label': 'Details',
          'aria-labelledby': `expandable-model-title-${model.model_id} toggle-model-button-${model.model_id}`,
          'aria-expanded': isExpanded,
        }}
      >
        <CardTitle id={`expandable-model-title-${model.model_id}`}>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
            <FlexItem>
              <Title className="pf-v6-u-mb-0" headingLevel="h2">
                {model.model_id}
              </Title>
            </FlexItem>
            <FlexItem>
              <Label color={model.model_type === 'llm' ? 'blue' : 'green'}>
                {model.model_type}
              </Label>
            </FlexItem>
            {model.is_shield && (
              <FlexItem>
                <Label color="purple">shield</Label>
              </FlexItem>
            )}
            {model.provider_id && (
              <FlexItem>
                <Label color="grey">{model.provider_id}</Label>
              </FlexItem>
            )}
          </Flex>
        </CardTitle>
      </CardHeader>
      <CardExpandableContent>
        <CardBody>
          <Flex direction={{ default: 'column' }}>
            {model.provider_id && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle">Provider ID: </span>
                {model.provider_id}
              </FlexItem>
            )}
            {model.provider_model_id && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle">Provider Model ID: </span>
                {model.provider_model_id}
              </FlexItem>
            )}
            {model.metadata && Object.keys(model.metadata).length > 0 && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle">Metadata: </span>
                <pre className="pf-v6-u-font-size-sm pf-v6-u-mt-xs">
                  {JSON.stringify(model.metadata, null, 2)}
                </pre>
              </FlexItem>
            )}
            {model.created_at && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle">Created: </span>
                {new Date(model.created_at).toLocaleString()}
              </FlexItem>
            )}
          </Flex>
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
