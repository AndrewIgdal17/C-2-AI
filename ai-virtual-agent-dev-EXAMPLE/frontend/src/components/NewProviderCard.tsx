import { useState } from 'react';
import {
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Title,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Alert,
  Spinner,
} from '@patternfly/react-core';
import { PlusIcon } from '@patternfly/react-icons';
import { ProviderCreate } from '@/types/models';
import { ProviderForm } from './ProviderForm';
import { useModelsManagement } from '@/hooks/useModelsManagement';

export function NewProviderCard() {
  const [isOpen, setIsOpen] = useState(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);
  const [pendingProvider, setPendingProvider] = useState<ProviderCreate | null>(null);
  const [registeredProviderName, setRegisteredProviderName] = useState<string>('');
  const [registrationStatus, setRegistrationStatus] = useState<string>('');
  const {
    createProvider,
    isCreatingProvider,
    createProviderError,
    resetCreateProviderError,
    refreshModels,
  } = useModelsManagement();

  const handleSubmit = (values: ProviderCreate) => {
    // Store the values and show confirmation modal
    setPendingProvider(values);
    setIsConfirmModalOpen(true);
  };

  const handleConfirmRegistration = async () => {
    if (!pendingProvider) return;

    try {
      setRegistrationStatus('Updating configuration and restarting LlamaStack...');
      await createProvider(pendingProvider);
      setRegistrationStatus('');
      setIsConfirmModalOpen(false);
      setRegisteredProviderName(pendingProvider.provider_id);
      setPendingProvider(null);
      // Refresh both models and providers lists
      refreshModels();
      setIsSuccessModalOpen(true);
      setIsOpen(false);
    } catch (error) {
      console.error('Error creating provider:', error);
      setRegistrationStatus('');
      setIsConfirmModalOpen(false);
    }
  };

  const handleCancelConfirmation = () => {
    setIsConfirmModalOpen(false);
    setPendingProvider(null);
  };

  const handleCancel = () => {
    resetCreateProviderError();
    setIsOpen(false);
  };

  return (
    <>
      <Card isExpanded={isOpen} isClickable={!isOpen} style={{ overflow: 'visible' }}>
        <CardHeader
          selectableActions={{
            onClickAction: () => setIsOpen(!isOpen),
            selectableActionAriaLabelledby: 'clickable-provider-card-title-1',
          }}
        >
          <CardTitle>
            {!isOpen ? (
              <Flex>
                <FlexItem>
                  <PlusIcon />
                </FlexItem>
                <FlexItem>
                  <Title headingLevel="h3">Register New Provider</Title>
                </FlexItem>
              </Flex>
            ) : (
              <Title headingLevel="h3">Register New Provider</Title>
            )}
          </CardTitle>
        </CardHeader>
        <CardExpandableContent style={{ overflow: 'visible' }}>
          <CardBody style={{ overflow: 'visible' }}>
            <ProviderForm
              isSubmitting={isCreatingProvider}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              error={createProviderError}
            />
          </CardBody>
        </CardExpandableContent>
      </Card>

      <Modal
        isOpen={isConfirmModalOpen}
        onClose={handleCancelConfirmation}
        variant="small"
        aria-labelledby="confirm-provider-modal-title"
        aria-describedby="confirm-provider-modal-desc"
      >
        <ModalHeader title="Confirm Provider Registration" labelId="confirm-provider-modal-title" />
        <ModalBody id="confirm-provider-modal-desc">
          {registrationStatus ? (
            <Alert variant="info" title={registrationStatus} isInline>
              <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                <FlexItem>
                  <Spinner size="md" />
                </FlexItem>
                <FlexItem>
                  Please wait while LlamaStack restarts. This may take up to 2 minutes...
                </FlexItem>
              </Flex>
            </Alert>
          ) : (
            <>
              Registering a new provider will restart LlamaStack. This process may take a few
              seconds to complete. During this time, LlamaStack services will be temporarily
              unavailable.
              <br />
              <br />
              Are you sure you want to continue?
            </>
          )}
        </ModalBody>
        <ModalFooter>
          <Button
            isLoading={isCreatingProvider}
            onClick={() => void handleConfirmRegistration()}
            variant="primary"
            isDisabled={isCreatingProvider}
          >
            Yes, Register Provider
          </Button>
          <Button variant="link" onClick={handleCancelConfirmation} isDisabled={isCreatingProvider}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>

      <Modal
        isOpen={isSuccessModalOpen}
        onClose={() => setIsSuccessModalOpen(false)}
        variant="small"
        aria-labelledby="success-provider-modal-title"
        aria-describedby="success-provider-modal-desc"
      >
        <ModalHeader
          title="Provider Registered Successfully"
          labelId="success-provider-modal-title"
        />
        <ModalBody id="success-provider-modal-desc">
          <Alert
            variant="success"
            title={`Provider "${registeredProviderName}" has been registered`}
            isInline
          >
            LlamaStack has been restarted and the new provider is now available for use. You can now
            register models using this provider.
          </Alert>
        </ModalBody>
        <ModalFooter>
          <Button onClick={() => setIsSuccessModalOpen(false)} variant="primary">
            OK
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}
