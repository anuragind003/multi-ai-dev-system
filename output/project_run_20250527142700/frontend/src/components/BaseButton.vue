<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[
      'base-button',
      `base-button--${variant}`,
      `base-button--${size}`,
      { 'base-button--disabled': disabled || loading },
      { 'base-button--loading': loading }
    ]"
    @click="handleClick"
  >
    <span v-if="loading" class="base-button__spinner"></span>
    <span :class="{ 'base-button__content--hidden': loading }">
      <slot></slot>
    </span>
  </button>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

const props = defineProps({
  /**
   * Defines the visual style of the button.
   * @values 'primary', 'secondary', 'danger', 'outline'
   */
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'danger', 'outline'].includes(value),
  },
  /**
   * Defines the size of the button.
   * @values 'small', 'medium', 'large'
   */
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value),
  },
  /**
   * If true, the button will be disabled and non-interactive.
   */
  disabled: {
    type: Boolean,
    default: false,
  },
  /**
   * If true, a loading spinner will be shown, and the button will be disabled.
   */
  loading: {
    type: Boolean,
    default: false,
  },
  /**
   * The native HTML button type.
   * @values 'button', 'submit', 'reset'
   */
  type: {
    type: String,
    default: 'button',
    validator: (value) => ['button', 'submit', 'reset'].includes(value),
  },
});

const emit = defineEmits(['click']);

/**
 * Handles the click event, preventing it if the button is disabled or in a loading state.
 * @param {Event} event - The DOM click event.
 */
const handleClick = (event) => {
  if (!props.disabled && !props.loading) {
    emit('click', event);
  }
};
</script>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, opacity 0.2s ease;
  position: relative;
  white-space: nowrap; /* Prevent text wrapping */
}

/* Variants */
.base-button--primary {
  background-color: #007bff; /* Bootstrap primary blue */
  color: white;
}
.base-button--primary:hover:not(.base-button--disabled) {
  background-color: #0056b3;
}

.base-button--secondary {
  background-color: #6c757d; /* Bootstrap secondary gray */
  color: white;
}
.base-button--secondary:hover:not(.base-button--disabled) {
  background-color: #545b62;
}

.base-button--danger {
  background-color: #dc3545; /* Bootstrap danger red */
  color: white;
}
.base-button--danger:hover:not(.base-button--disabled) {
  background-color: #bd2130;
}

.base-button--outline {
  background-color: transparent;
  color: #007bff;
  border: 1px solid #007bff;
}
.base-button--outline:hover:not(.base-button--disabled) {
  background-color: #e9f5ff; /* Light blue background on hover */
  color: #0056b3;
  border-color: #0056b3;
}

/* Sizes */
.base-button--small {
  padding: 6px 12px;
  font-size: 14px;
  line-height: 1.5;
}
.base-button--medium {
  padding: 10px 20px;
  font-size: 16px;
  line-height: 1.5;
}
.base-button--large {
  padding: 14px 28px;
  font-size: 18px;
  line-height: 1.5;
}

/* Disabled state */
.base-button--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Loading state */
.base-button--loading {
  cursor: progress;
}

.base-button__spinner {
  display: inline-block;
  width: 1.2em; /* Slightly larger than font size for visibility */
  height: 1.2em;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff; /* Spinner color for solid buttons */
  animation: spin 1s linear infinite;
  position: absolute;
}

/* Adjust spinner color for outline variant */
.base-button--outline .base-button__spinner {
  border-color: rgba(0, 123, 255, 0.3);
  border-top-color: #007bff;
}

/* Hide content when loading to show only spinner */
.base-button__content--hidden {
  visibility: hidden;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>