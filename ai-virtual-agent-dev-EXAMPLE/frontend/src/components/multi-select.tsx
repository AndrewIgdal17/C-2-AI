import {
  Button,
  Label,
  LabelGroup,
  MenuToggle,
  MenuToggleElement,
  SelectOptionProps as PFSelectOptionProps,
  Select,
  SelectList,
  SelectOption,
  TextInputGroup,
  TextInputGroupMain,
  TextInputGroupUtilities,
} from '@patternfly/react-core';
import TimesIcon from '@patternfly/react-icons/dist/esm/icons/times-icon';
import React, { useEffect, useRef, useState } from 'react';

export interface CustomSelectOptionProps extends PFSelectOptionProps {
  value: string;
  children: string;
}

interface MultiSelectProps {
  id: string;
  value: string[];
  options: CustomSelectOptionProps[];
  onBlur: () => void;
  onChange: (newValue: string[]) => void;
  ariaLabel?: string;
  isDisabled?: boolean;
  placeholder?: string;
}

export function MultiSelect({
  id,
  value,
  options,
  onBlur,
  onChange,
  ariaLabel,
  isDisabled = false,
  placeholder = 'Select options...',
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState<string>('');
  const [filteredOptions, setFilteredOptions] = useState<CustomSelectOptionProps[]>(options);
  const [focusedItemIndex, setFocusedItemIndex] = useState<number | null>(null);
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const textInputRef = useRef<HTMLInputElement>(null);

  const NO_RESULTS_VALUE = '___no-results___';

  useEffect(() => {
    if (!isOpen) {
      if (!inputValue) setFilteredOptions(options);
      return;
    }

    let newFilteredOptions: CustomSelectOptionProps[];

    if (inputValue) {
      newFilteredOptions = options.filter((menuItem) =>
        String(menuItem.children).toLowerCase().includes(inputValue.toLowerCase())
      );

      if (!newFilteredOptions.length) {
        newFilteredOptions = [
          {
            isAriaDisabled: true,
            children: `No results found for "${inputValue}"`,
            value: NO_RESULTS_VALUE,
            id: `${id}-${NO_RESULTS_VALUE}`,
          },
        ];
      }
    } else {
      newFilteredOptions = options;
    }
    setFilteredOptions(newFilteredOptions);
  }, [inputValue, options, isOpen, id]);

  const createItemId = (optionValue: string | number | undefined): string => {
    // Ensure optionValue is a string before calling replace
    const stringValue = String(optionValue || ''); // Convert to string, default to empty string if null/undefined
    return `${id}-option-${stringValue.replace(/\s+/g, '-')}`;
  };

  const setActiveAndFocusedItem = (itemIndex: number) => {
    setFocusedItemIndex(itemIndex);
    const focusedItem = filteredOptions[itemIndex];
    if (focusedItem && focusedItem.value && focusedItem.value !== NO_RESULTS_VALUE) {
      setActiveItemId(createItemId(focusedItem.value));
    } else {
      setActiveItemId(null);
    }
  };

  const resetActiveAndFocusedItem = () => {
    setFocusedItemIndex(null);
    setActiveItemId(null);
  };

  const closeMenu = (runOnBlur = true) => {
    setIsOpen(false);
    resetActiveAndFocusedItem();
    if (runOnBlur) {
      onBlur();
    }
  };

  const onInputClick = () => {
    if (isDisabled) return;
    if (!isOpen) {
      setIsOpen(true);
    }
  };

  const handlePFSelect = (
    _event: React.MouseEvent | React.ChangeEvent | undefined,
    selectionValue: string | number | undefined // PF SelectOption value can be string or number
  ) => {
    if (isDisabled || typeof selectionValue !== 'string' || selectionValue === NO_RESULTS_VALUE) {
      return;
    }

    const clickedValue = selectionValue;
    const newSelectedState = value.includes(clickedValue)
      ? value.filter((v) => v !== clickedValue)
      : [...value, clickedValue];

    onChange(newSelectedState);
    textInputRef.current?.focus();
  };

  const onTextInputChange = (_event: React.FormEvent<HTMLInputElement>, newInputValue: string) => {
    setInputValue(newInputValue);
    if (!isOpen && newInputValue) {
      setIsOpen(true);
    }
    resetActiveAndFocusedItem();
  };

  const handleMenuArrowKeys = (key: string) => {
    if (
      isDisabled ||
      !isOpen ||
      filteredOptions.every((opt) => opt.isAriaDisabled || opt.isDisabled)
    ) {
      return;
    }

    let indexToFocus = focusedItemIndex === null ? -1 : focusedItemIndex;

    if (key === 'ArrowUp') {
      indexToFocus = indexToFocus <= 0 ? filteredOptions.length - 1 : indexToFocus - 1;
    } else if (key === 'ArrowDown') {
      indexToFocus = indexToFocus >= filteredOptions.length - 1 ? 0 : indexToFocus + 1;
    }

    let attempts = 0;
    while (
      attempts < filteredOptions.length &&
      (filteredOptions[indexToFocus].isAriaDisabled || filteredOptions[indexToFocus].isDisabled)
    ) {
      if (key === 'ArrowUp') {
        indexToFocus = indexToFocus <= 0 ? filteredOptions.length - 1 : indexToFocus - 1;
      } else {
        indexToFocus = indexToFocus >= filteredOptions.length - 1 ? 0 : indexToFocus + 1;
      }
      attempts++;
    }
    if (attempts < filteredOptions.length) {
      setActiveAndFocusedItem(indexToFocus);
    }
  };

  const onInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (isDisabled) return;

    const focusedItem = focusedItemIndex !== null ? filteredOptions[focusedItemIndex] : null;

    switch (event.key) {
      case 'Enter':
        event.preventDefault();
        if (
          isOpen &&
          focusedItem &&
          focusedItem.value !== NO_RESULTS_VALUE &&
          !focusedItem.isAriaDisabled &&
          !focusedItem.isDisabled
        ) {
          handlePFSelect(undefined, focusedItem.value);
        } else if (!isOpen) {
          setIsOpen(true);
        }
        break;
      case 'ArrowUp':
      case 'ArrowDown':
        event.preventDefault();
        if (!isOpen && filteredOptions.length > 0) setIsOpen(true);
        handleMenuArrowKeys(event.key);
        break;
      case 'Escape':
        event.preventDefault();
        closeMenu();
        break;
      case 'Tab':
        closeMenu();
        break;
      case 'Backspace':
        if (!inputValue && value.length > 0) {
          event.preventDefault();
          onChange(value.slice(0, -1));
        }
        break;
    }
  };

  const onToggleClick = () => {
    if (isDisabled) return;
    setIsOpen(!isOpen);
    if (!isOpen) {
      textInputRef.current?.focus();
    } else {
      onBlur();
    }
  };

  const onClearButtonClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange([]);
    setInputValue('');
    resetActiveAndFocusedItem();
    textInputRef.current?.focus();
    if (!isOpen) setIsOpen(true);
  };

  const toggle = (toggleRef: React.Ref<MenuToggleElement>) => (
    <MenuToggle
      variant="typeahead"
      aria-label={ariaLabel || 'Multi typeahead menu toggle'}
      onClick={onToggleClick}
      innerRef={toggleRef}
      isExpanded={isOpen}
      isDisabled={isDisabled}
      isFullWidth
    >
      <TextInputGroup isPlain isDisabled={isDisabled}>
        <TextInputGroupMain
          value={inputValue}
          onClick={onInputClick}
          onChange={onTextInputChange}
          onKeyDown={onInputKeyDown}
          id={`${id}-input`}
          autoComplete="off"
          innerRef={textInputRef}
          placeholder={value.length > 0 ? '' : placeholder}
          {...(activeItemId && { 'aria-activedescendant': activeItemId })}
          role="combobox"
          isExpanded={isOpen}
          aria-controls={`${id}-listbox`}
        >
          <LabelGroup aria-label="Current selections" numLabels={5}>
            {value.map((selectedValue) => {
              const option = options.find((opt) => opt.value === selectedValue);
              return (
                <Label
                  key={selectedValue}
                  variant="outline"
                  onClose={(ev) => {
                    ev.stopPropagation();
                    handlePFSelect(undefined, selectedValue);
                  }}
                  isDisabled={isDisabled}
                >
                  {option?.children || selectedValue}
                </Label>
              );
            })}
          </LabelGroup>
        </TextInputGroupMain>
        {(value.length > 0 || inputValue) && (
          <TextInputGroupUtilities>
            <Button
              variant="plain"
              onClick={onClearButtonClick}
              aria-label="Clear selections and input"
              isDisabled={isDisabled}
              icon={<TimesIcon />}
            />
          </TextInputGroupUtilities>
        )}
      </TextInputGroup>
    </MenuToggle>
  );

  return (
    <Select
      id={id}
      isOpen={isOpen}
      selected={value}
      onSelect={handlePFSelect}
      onOpenChange={(newIsOpenState) => {
        setIsOpen(newIsOpenState);
        if (!newIsOpenState) {
          closeMenu();
        }
      }}
      toggle={toggle}
    >
      <SelectList isAriaMultiselectable id={`${id}-listbox`}>
        {filteredOptions.map((option, index) => (
          <SelectOption
            key={option.id || option.value || index}
            isFocused={focusedItemIndex === index}
            isSelected={value.includes(option.value)}
            value={option.value} // This is what onSelect receives
            isDisabled={option.isDisabled || option.isAriaDisabled}
            // Use the option's own id if provided and unique, otherwise generate one
            id={
              option.id && option.id !== NO_RESULTS_VALUE ? option.id : createItemId(option.value)
            }
            className={option.className}
          >
            {option.children}
          </SelectOption>
        ))}
      </SelectList>
    </Select>
  );
}
