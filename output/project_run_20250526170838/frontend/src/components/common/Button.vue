<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="['button', `button--${variant}`, `button--${size}`, { 'button--disabled': disabled || loading }]"
    @click="handleClick"
  >
    <span v-if="loading" class="button__spinner"></span>
    <span v-else>{{ text }}</span>
  </button>
</template>

<script>
export default {
  name: 'Button',
  props: {
    /**
     * The text displayed inside the button.
     */
    text: {
      type: String,
      required: true
    },
    /**
     * The HTML type attribute for the button.
     * Can be 'button', 'submit', or 'reset'.
     */
    type: {
      type: String,
      default: 'button',
      validator: (value) => ['button', 'submit', 'reset'].includes(value)
    },
    /**
     * The visual style variant of the button.
     * Can be 'primary', 'secondary', 'danger', 'outline', or 'text'.
     */
    variant: {
      type: String,
      default: 'primary',
      validator: (value) => ['primary', 'secondary', 'danger', 'outline', 'text'].includes(value)
    },
    /**
     * The size of the button.
     * Can be 'small', 'medium', or 'large'.
     */
    size: {
      type: String,
      default: 'medium',
      validator: (value) => ['small', 'medium', 'large'].includes(value)
    },
    /**
     * If true, the button will be disabled and unclickable.
     */
    disabled: {
      type: Boolean,
      default: false
    },
    /**
     * If true, a loading spinner will be shown and the button will be disabled.
     */
    loading: {
      type: Boolean,
      default: false
    }
  },
  methods: {
    /**
     * Emits a 'click' event when the button is clicked,
     * unless it is disabled or in a loading state.
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
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, opacity 0.2s ease;
  white-space: nowrap; /* Prevent text wrapping */
  box-sizing: border-box; /* Include padding and border in the element's total width and height */
}

/* Variants */
.button--primary {
  background-color: #007bff; /* Bootstrap primary blue */
  color: white;
  border-color: #007bff;
}
.button--primary:hover:not(.button--disabled) {
  background-color: #0056b3;
  border-color: #0056b3;
}

.button--secondary {
  background-color: #6c757d; /* Bootstrap secondary gray */
  color: white;
  border-color: #6c757d;
}
.button--secondary:hover:not(.button--disabled) {
  background-color: #5a6268;
  border-color: #5a6268;
}

.button--danger {
  background-color: #dc3545; /* Bootstrap danger red */
  color: white;
  border-color: #dc3545;
}
.button--danger:hover:not(.button--disabled) {
  background-color: #c82333;
  border-color: #c82333;
}

.button--outline {
  background-color: transparent;
  color: #007bff;
  border-color: #007bff;
}
.button--outline:hover:not(.button--disabled) {
  background-color: #e9f5ff; /* Light blue hover */
  color: #0056b3;
  border-color: #0056b3;
}

.button--text {
  background-color: transparent;
  color: #007bff;
  border: none;
  padding: 8px 0; /* Adjust padding for text-only buttons */
}
.button--text:hover:not(.button--disabled) {
  text-decoration: underline;
  color: #0056b3;
}

/* Sizes */
.button--small {
  padding: 6px 12px;
  font-size: 14px;
}

.button--medium {
  padding: 8px 16px;
  font-size: 16px;
}

.button--large {
  padding: 10px 20px;
  font-size: 18px;
}

/* Disabled state */
.button--disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background-color: #e0e0e0; /* Light gray background for disabled */
  color: #a0a0a0; /* Darker gray text for disabled */
  border-color: #e0e0e0;
}
.button--disabled.button--outline {
  background-color: transparent;
  color: #a0a0a0;
  border-color: #e0e0e0;
}
.button--disabled.button--text {
  background-color: transparent;
  color: #a0a0a0;
  border: none;
}


/* Loading spinner */
.button__spinner {
  display: inline-block;
  width: 1em;
  height: 1em;
  border: 2px solid rgba(255, 255, 255, 0.3); /* Default for solid buttons */
  border-radius: 50%;
  border-top-color: #fff; /* Default for solid buttons */
  animation: spin 1s ease-in-out infinite;
  /* No margin-right needed as it replaces text */
}

/* Adjust spinner color for outline and text variants */
.button--outline .button__spinner,
.button--text .button__spinner {
  border-color: rgba(0, 123, 255, 0.3); /* Match outline/text color */
  border-top-color: #007bff; /* Match outline/text color */
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>