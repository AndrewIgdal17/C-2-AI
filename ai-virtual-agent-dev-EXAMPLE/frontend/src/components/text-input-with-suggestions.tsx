import {
  Button,
  MenuToggle,
  MenuToggleElement,
  Select,
  SelectList,
  SelectOption,
  TextInputGroup,
  TextInputGroupMain,
  TextInputGroupUtilities,
} from '@patternfly/react-core';
import TimesIcon from '@patternfly/react-icons/dist/esm/icons/times-icon';
import React, { useEffect, useRef, useState } from 'react';

interface TextInputWithSuggestionsProps {
  id: string;
  value: string;
  suggestions: string[];
  onBlur?: () => void;
  onChange: (newValue: string) => void;
  ariaLabel?: string;
  isDisabled?: boolean;
  placeholder?: string;
  allowClear?: boolean;
}

export function TextInputWithSuggestions({
  id,
  value,
  suggestions,
  onBlur,
  onChange,
  ariaLabel,
  isDisabled = false,
  placeholder = 'Type to see suggestions...',
  allowClear = true,
}: TextInputWithSuggestionsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>(suggestions);
  const [focusedItemIndex, setFocusedItemIndex] = useState<number | null>(null);
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const textInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isOpen && !value) {
      setFilteredSuggestions(suggestions);
      return;
    }

    let newFilteredSuggestions: string[];

    if (value) {
      newFilteredSuggestions = suggestions.filter((suggestion) =>
        suggestion.toLowerCase().includes(value.toLowerCase())
      );

      if (!newFilteredSuggestions.length && isOpen) {
        newFilteredSuggestions = [`No suggestions found for "${value}"`];
      }
    } else {
      newFilteredSuggestions = suggestions;
    }
    setFilteredSuggestions(newFilteredSuggestions);
  }, [value, suggestions, isOpen]);

  const createItemId = (suggestionValue: string): string => {
    return `${id}-option-${suggestionValue.replace(/\s+/g, '-')}`;
  };

  const setActiveAndFocusedItem = (itemIndex: number) => {
    setFocusedItemIndex(itemIndex);
    const focusedItem = filteredSuggestions[itemIndex];
    if (focusedItem && !focusedItem.startsWith('No suggestions found')) {
      setActiveItemId(createItemId(focusedItem));
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
    if (runOnBlur && onBlur) {
      onBlur();
    }
  };

  const onInputClick = () => {
    if (isDisabled) return;
    if (!isOpen) {
      setIsOpen(true);
    }
  };

  const handleSuggestionSelect = (
    _event: React.MouseEvent | React.ChangeEvent | undefined,
    selectionValue: string | number | undefined
  ) => {
    if (
      isDisabled ||
      typeof selectionValue !== 'string' ||
      selectionValue.startsWith('No suggestions found')
    ) {
      return;
    }

    onChange(selectionValue);
    setIsOpen(false);
    resetActiveAndFocusedItem();
    textInputRef.current?.focus();
  };

  const onTextInputChange = (_event: React.FormEvent<HTMLInputElement>, newInputValue: string) => {
    onChange(newInputValue);
    if (!isOpen && newInputValue) {
      setIsOpen(true);
    }
    resetActiveAndFocusedItem();
  };

  const handleMenuArrowKeys = (key: string) => {
    if (isDisabled || !isOpen || filteredSuggestions.length === 0) {
      return;
    }

    let indexToFocus = focusedItemIndex === null ? -1 : focusedItemIndex;

    if (key === 'ArrowUp') {
      indexToFocus = indexToFocus <= 0 ? filteredSuggestions.length - 1 : indexToFocus - 1;
    } else if (key === 'ArrowDown') {
      indexToFocus = indexToFocus >= filteredSuggestions.length - 1 ? 0 : indexToFocus + 1;
    }

    // Skip no-results entries
    let attempts = 0;
    while (
      attempts < filteredSuggestions.length &&
      filteredSuggestions[indexToFocus].startsWith('No suggestions found')
    ) {
      if (key === 'ArrowUp') {
        indexToFocus = indexToFocus <= 0 ? filteredSuggestions.length - 1 : indexToFocus - 1;
      } else {
        indexToFocus = indexToFocus >= filteredSuggestions.length - 1 ? 0 : indexToFocus + 1;
      }
      attempts++;
    }

    if (attempts < filteredSuggestions.length) {
      setActiveAndFocusedItem(indexToFocus);
    }
  };

  const onInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (isDisabled) return;

    const focusedItem = focusedItemIndex !== null ? filteredSuggestions[focusedItemIndex] : null;

    switch (event.key) {
      case 'Enter':
        event.preventDefault();
        if (isOpen && focusedItem && !focusedItem.startsWith('No suggestions found')) {
          handleSuggestionSelect(undefined, focusedItem);
        } else if (!isOpen && value) {
          setIsOpen(true);
        }
        break;
      case 'ArrowUp':
      case 'ArrowDown':
        event.preventDefault();
        if (!isOpen && filteredSuggestions.length > 0) {
          setIsOpen(true);
        }
        handleMenuArrowKeys(event.key);
        break;
      case 'Escape':
        event.preventDefault();
        closeMenu();
        break;
      case 'Tab':
        closeMenu();
        break;
    }
  };

  const onToggleClick = () => {
    if (isDisabled) return;
    setIsOpen(!isOpen);
    if (!isOpen) {
      textInputRef.current?.focus();
    } else {
      closeMenu();
    }
  };

  const onClearButtonClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange('');
    resetActiveAndFocusedItem();
    textInputRef.current?.focus();
    if (!isOpen) setIsOpen(true);
  };

  const toggle = (toggleRef: React.Ref<MenuToggleElement>) => (
    <MenuToggle
      variant="typeahead"
      aria-label={ariaLabel || 'Text input with suggestions'}
      onClick={onToggleClick}
      innerRef={toggleRef}
      isExpanded={isOpen}
      isDisabled={isDisabled}
      isFullWidth
    >
      <TextInputGroup isPlain isDisabled={isDisabled}>
        <TextInputGroupMain
          value={value}
          onClick={onInputClick}
          onChange={onTextInputChange}
          onKeyDown={onInputKeyDown}
          id={`${id}-input`}
          autoComplete="off"
          innerRef={textInputRef}
          placeholder={placeholder}
          {...(activeItemId && { 'aria-activedescendant': activeItemId })}
          role="combobox"
          isExpanded={isOpen}
          aria-controls={`${id}-listbox`}
        />
        {allowClear && value && (
          <TextInputGroupUtilities>
            <Button
              variant="plain"
              onClick={onClearButtonClick}
              aria-label="Clear input"
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
      onSelect={handleSuggestionSelect}
      onOpenChange={(newIsOpenState) => {
        setIsOpen(newIsOpenState);
        if (!newIsOpenState) {
          closeMenu();
        }
      }}
      toggle={toggle}
    >
      <SelectList id={`${id}-listbox`}>
        {filteredSuggestions.map((suggestion, index) => (
          <SelectOption
            key={suggestion}
            isFocused={focusedItemIndex === index}
            value={suggestion}
            isDisabled={suggestion.startsWith('No suggestions found')}
            id={createItemId(suggestion)}
          >
            <div>
              <div className="pf-v5-u-font-weight-bold">{suggestion}</div>
            </div>
          </SelectOption>
        ))}
      </SelectList>
    </Select>
  );
}
