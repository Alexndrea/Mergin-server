<!--
Copyright (C) Lutra Consulting Limited

SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-MerginMaps-Commercial
-->

<template>
  <div class="flex flex-column align-items-center pb-4 text-center gap-4">
    <img
      v-if="severity === 'danger'"
      src="@/assets/trash.svg"
      alt="Cover for confirm dialog"
    />
    <img
      v-else-if="severity === 'warning'"
      src="@/assets/warning-dialog.svg"
      alt="Cover for confirm dialog"
    />
    <img v-else src="@/assets/neutral.svg" alt="Cover for confirm dialog" />
    <span class="text-color-forest title-t1">{{ text }}</span>
    <span class="paragraph-p6 opacity-80">{{ description }}</span>
    <span class="title-t2">{{ hint }}</span>
    <span v-if="confirmField" class="flex p-float-label w-full p-input-filled">
      <PInputText
        autofocus
        id="confirmValue"
        v-model="confirmValue"
        type="text"
        class="flex-grow-1"
      />
      <label for="confirmValue">{{ confirmField.label }}</label>
    </span>

    <slot></slot>

    <!-- Footer -->
    <div
      class="w-full flex flex-column lg:flex-row justify-content-between align-items-center mt-4"
    >
      <PButton
        severity="secondary"
        @click="close"
        class="flex w-12 mb-2 lg:mb-0 lg:mr-2 lg:w-6 justify-content-center"
        data-cy="clone-dialog-close-btn"
        >{{ cancelText }}</PButton
      >

      <PButton
        :disabled="!isConfirmed"
        @click="confirm"
        :severity="severity"
        class="flex w-12 lg:w-6 justify-content-center"
      >
        {{ confirmText }}
      </PButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineEmits, withDefaults } from 'vue'

import { ConfirmDialogProps } from '../types'

import { useDialogStore } from '@/modules/dialog/store'

const props = withDefaults(defineProps<ConfirmDialogProps>(), {
  confirmText: 'Ok',
  cancelText: 'Cancel',
  severity: 'primary'
})

const confirmValue = ref('')
const emit = defineEmits(['confirm'])

const isConfirmed = computed(() => {
  return props.confirmField
    ? props.confirmField.expected === confirmValue.value
    : true
})

const { close } = useDialogStore()

function confirm() {
  close()
  emit('confirm')
}
</script>
