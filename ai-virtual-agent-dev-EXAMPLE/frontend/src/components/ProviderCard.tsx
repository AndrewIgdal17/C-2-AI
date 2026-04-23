import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  CardExpandableContent,
  Title,
  Flex,
  FlexItem,
  Label,
  LabelGroup,
} from '@patternfly/react-core';
import { useState } from 'react';
import { ModelProvider, Model } from '@/types/models';

interface ProviderCardProps {
  provider: ModelProvider;
  models: Model[];
}

export function ProviderCard({ provider, models }: ProviderCardProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const onExpand = () => setIsExpanded(!isExpanded);

  return (
    <Card id={`expandable-provider-card-${provider.provider_id}`} isExpanded={isExpanded}>
      <CardHeader
        onExpand={onExpand}
        toggleButtonProps={{
          id: `toggle-provider-button-${provider.provider_id}`,
          'aria-label': 'Details',
          'aria-labelledby': `expandable-provider-title-${provider.provider_id} toggle-provider-button-${provider.provider_id}`,
          'aria-expanded': isExpanded,
        }}
      >
        <CardTitle id={`expandable-provider-title-${provider.provider_id}`}>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapMd' }}>
            <FlexItem>
              <Title className="pf-v6-u-mb-0" headingLevel="h3">
                {provider.provider_id}
              </Title>
            </FlexItem>
            {!isExpanded && (
              <>
                <FlexItem>
                  <Label color="blue">{provider.api}</Label>
                </FlexItem>
                <FlexItem>
                  <Label color="grey">{provider.provider_type}</Label>
                </FlexItem>
                <FlexItem>
                  <Label color="teal">
                    {models.length} {models.length === 1 ? 'model' : 'models'}
                  </Label>
                </FlexItem>
              </>
            )}
          </Flex>
        </CardTitle>
      </CardHeader>
      <CardExpandableContent>
        <CardBody>
          <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
            {/* API */}
            <FlexItem>
              <Flex
                direction={{ default: 'row' }}
                gap={{ default: 'gapMd' }}
                alignItems={{ default: 'alignItemsCenter' }}
              >
                <FlexItem style={{ minWidth: '150px' }}>
                  <strong>API</strong>
                </FlexItem>
                <FlexItem flex={{ default: 'flex_1' }}>
                  <Label color="blue">{provider.api}</Label>
                </FlexItem>
              </Flex>
            </FlexItem>

            {/* Provider Type */}
            <FlexItem>
              <Flex
                direction={{ default: 'row' }}
                gap={{ default: 'gapMd' }}
                alignItems={{ default: 'alignItemsCenter' }}
              >
                <FlexItem style={{ minWidth: '150px' }}>
                  <strong>Provider Type</strong>
                </FlexItem>
                <FlexItem flex={{ default: 'flex_1' }}>
                  <Label color="grey">{provider.provider_type}</Label>
                </FlexItem>
              </Flex>
            </FlexItem>

            {/* Configuration */}
            {provider.config && Object.keys(provider.config).length > 0 && (
              <FlexItem>
                <Flex direction={{ default: 'row' }} gap={{ default: 'gapMd' }}>
                  <FlexItem style={{ minWidth: '150px' }}>
                    <strong>Configuration</strong>
                  </FlexItem>
                  <FlexItem flex={{ default: 'flex_1' }}>
                    <pre
                      style={{
                        backgroundColor: '#f5f5f5',
                        padding: '1rem',
                        borderRadius: '4px',
                        overflow: 'auto',
                      }}
                    >
                      <code>{JSON.stringify(provider.config, null, 2)}</code>
                    </pre>
                  </FlexItem>
                </Flex>
              </FlexItem>
            )}

            {/* Models */}
            <FlexItem>
              <Flex direction={{ default: 'row' }} gap={{ default: 'gapMd' }}>
                <FlexItem style={{ minWidth: '150px' }}>
                  <strong>Models</strong>
                </FlexItem>
                <FlexItem flex={{ default: 'flex_1' }}>
                  {models.length > 0 ? (
                    <LabelGroup numLabels={10}>
                      {models
                        .sort(
                          (a, b) => Date.parse(b.created_at ?? '') - Date.parse(a.created_at ?? '')
                        )
                        .map((model) => (
                          <Label key={model.model_id} color="teal">
                            {model.model_id}
                          </Label>
                        ))}
                    </LabelGroup>
                  ) : (
                    <span className="pf-v6-u-text-color-subtle pf-v6-u-font-size-sm">
                      No models registered yet.
                    </span>
                  )}
                </FlexItem>
              </Flex>
            </FlexItem>
          </Flex>
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
