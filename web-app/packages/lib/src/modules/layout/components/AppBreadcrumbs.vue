<!--
Copyright (C) Lutra Consulting Limited

SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-MerginMaps-Commercial
-->

<template>
  <PBreadcrumb
    v-if="items.length > 0"
    :model="items"
    :pt="{
      root: {
        style: {
          backgroundColor: 'transparent'
        },
        class: 'border-none p-2 w-full overflow-x-auto'
      }
    }"
  >
    <template #separator>
      <i class="ti ti-chevron-right" />
    </template>
    <template #item="{ item, props }">
      <router-link
        v-if="item.path"
        v-slot="{ href, navigate }"
        :to="{
          path: item.path
        }"
        custom
      >
        <a :href="href" v-bind="props.action" @click="navigate">
          <span :class="[item.icon, 'text-color']" />
          <span
            :class="[
              'opacity-80 paragraph-p5',
              item.active ? 'text-color-forest font-semibold' : 'text-color'
            ]"
            >{{ item.label }}</span
          >
        </a>
      </router-link>
    </template>
  </PBreadcrumb>
</template>

<script setup lang="ts">
import { MenuItem } from 'primevue/menuitem'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useLayoutStore } from '../store'

type EnhancedMenuItem = MenuItem & { path: string; active?: boolean }

const layoutStore = useLayoutStore()
const route = useRoute()
// Merge all matched meta.breadcrumps with current route breadcrumps

const items = computed(() =>
  layoutStore.breadcrumps?.length
    ? layoutStore.breadcrumps?.map((item, index, items) => ({
        label: item.title,
        path: item.path,
        active: index === items.length - 1
      }))
    : [
        ...route.matched.reduce<EnhancedMenuItem[]>((acc, curr) => {
          if (curr.name === route.name) return acc

          return [
            ...acc,
            ...(curr.meta?.breadcrump ?? []).map((item) => ({
              label: item.title,
              path: item.path
            }))
          ]
        }, []),
        // adding current route wich is not in matched meta
        ...(route.meta.breadcrump ?? []).map((item) => ({
          label: item.title,
          path: item.path
        }))
      ]
        // last will be active
        .map((item, index, items) => ({
          ...item,
          active: index === items.length - 1
        }))
)
</script>

<style scoped lang="scss"></style>
