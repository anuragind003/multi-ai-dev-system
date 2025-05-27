<template>
  <button
    :type="type"
    :class="['base-button', `base-button--${variant}`, `base-button--${size}`, { 'base-button--disabled': disabled || loading }]"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <span v-if="loading" class="base-button__spinner"></span>
    <slot v-else></slot>
  </button>
</template>

<script>
export default {
  name: 'BaseButton',
  props: {
    /**
     * The HTML type attribute for the button.
     * @values 'button', 'submit', 'reset'
     */
    type: {
      type: String,
      default: 'button',
      validator: (value) => ['button', 'submit', 'reset'].includes(value)
    },
    /**
     * The visual style variant of the button.
     * @values 'primary', 'secondary', 'danger', 'success', 'outline'
     */
    variant: {
      type: String,
      default: 'primary',
      validator: (value) => ['primary', 'secondary', 'danger', 'success', 'outline'].includes(value)
    },
    /**
     * The size of the button.
     * @values 'small', 'medium', 'large'
     */
    size: {
      type: String,
      default: 'medium',
      validator: (value) => ['small', 'medium', 'large'].includes(value)
    },
    /**
     * Whether the button is disabled.
     */
    disabled: {
      type: Boolean,
      default: false
    },
    /**
     * Whether the button is in a loading state, showing a spinner.
     */
    loading: {
      type: Boolean,
      default: false
    }
  },
  methods: {
    /**
     * Handles the click event, preventing it if the button is disabled or loading.
     * @param {Event} event - The DOM click event.
     */
    handleClick(event) {
      if (!this.disabled && !this.loading) {
        this.$emit('click', event);
      }
    }
  }
};
</script>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, opacity 0.2s ease;
  white-space: nowrap;
  user-select: none;
  -webkit-appearance: none; /* Remove default button styles for consistency */
  -moz-appearance: none;
  appearance: none;
  font-family: inherit; /* Inherit font from parent */
}

/* Variants */
.base-button--primary {
  background-color: #007bff; /* Blue */
  color: #fff;
  border-color: #007bff;
}
.base-button--primary:hover:not(.base-button--disabled) {
  background-color: #0056b3;
  border-color: #0056b3;
}

.base-button--secondary {
  background-color: #6c757d; /* Gray */
  color: #fff;
  border-color: #6c757d;
}
.base-button--secondary:hover:not(.base-button--disabled) {
  background-color: #5a6268;
  border-color: #5a6268;
}

.base-button--danger {
  background-color: #dc3545; /* Red */
  color: #fff;
  border-color: #dc3545;
}
.base-button--danger:hover:not(.base-button--disabled) {
  background-color: #c82333;
  border-color: #c82333;
}

.base-button--success {
  background-color: #28a745; /* Green */
  color: #fff;
  border-color: #28a745;
}
.base-button--success:hover:not(.base-button--disabled) {
  background-color: #218838;
  border-color: #218838;
}

.base-button--outline {
  background-color: transparent;
  color: #007bff;
  border-color: #007bff;
}
.base-button--outline:hover:not(.base-button--disabled) {
  background-color: #e9f5ff; /* Light blue background on hover */
  color: #0056b3;
  border-color: #0056b3;
}

/* Sizes */
.base-button--small {
  padding: 6px 12px;
  font-size: 0.875rem;
}

.base-button--medium {
  padding: 8px 16px;
  font-size: 1rem;
}

.base-button--large {
  padding: 10px 20px;
  font-size: 1.125rem;
}

/* Disabled state */
.base-button--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Loading spinner */
.base-button__spinner {
  display: inline-block;
  width: 1em;
  height: 1em;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff; /* Default spinner color for solid buttons */
  animation: spin 1s ease-in-out infinite;
  margin-right: 0; /* No margin if only spinner is present */
}

/* Adjust spinner color for outline variant */
.base-button--outline .base-button__spinner {
  border-color: rgba(0, 123, 255, 0.3);
  border-top-color: #007bff;
}

/* Add margin to spinner if there's text content */
.base-button:not(.base-button--disabled) .base-button__spinner + *:not(:empty) {
  margin-left: 8px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>