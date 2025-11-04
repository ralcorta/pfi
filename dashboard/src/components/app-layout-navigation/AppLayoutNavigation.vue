<template>
  <div class="flex gap-2 justify-between items-center">
  <div class="flex gap-2">
    <VaIconMenuCollapsed
      class="cursor-pointer"
      :class="{ 'x-flip': !isSidebarMinimized }"
      :color="collapseIconColor"
      @click="isSidebarMinimized = !isSidebarMinimized"
    />

    <nav class="flex items-center">
      <VaBreadcrumbs>
        <VaBreadcrumbsItem
            v-for="item in breadcrumbItems"
          :key="item.label"
          :label="item.label"
            :to="item.to"
          @click="handleBreadcrumbClick(item)"
        />
      </VaBreadcrumbs>
    </nav>
    </div>

    <VaButton preset="secondary" color="danger" @click="handleLogout">
      <VaIcon name="mso-logout" class="mr-2" />
      Cerrar Sesión
    </VaButton>
  </div>
</template>

<script setup lang="ts">import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useColors, useToast } from 'vuestic-ui'
import VaIconMenuCollapsed from '../icons/VaIconMenuCollapsed.vue'
import { storeToRefs } from 'pinia'
import { useGlobalStore } from '../../stores/global-store'
import NavigationRoutes from '../sidebar/NavigationRoutes'
import { logout } from '../../services/auth'
const { isSidebarMinimized } = storeToRefs(useGlobalStore())
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
type BreadcrumbNavigationItem = {
  label: string
  to: string
  hasChildren: boolean
}
const findRouteName = (name: string) => {
  const traverse = (routers: any[]): string => {
    for (const router of routers) {
      if (router.name === name) {
        return router.displayName
      }
      if (router.children) {
        const result = traverse(router.children)
        if (result) {
          return result
        }
      }
    }
    return ''
  }
  return traverse(NavigationRoutes.routes)
}
const items = computed(() => {
  const result: { label: string; to: string; hasChildren: boolean }[] = []
  route.matched.forEach((matchedRoute) => {
    if (matchedRoute.name === 'app') {
      return
    }
    const labelKey = findRouteName(matchedRoute.name as string)
    if (!labelKey) {
      return
    }
    result.push({
      label: t(labelKey),
      to: matchedRoute.path,
      hasChildren: matchedRoute.children && matchedRoute.children.length > 0,
    })
  })
  return result
})
const breadcrumbItems = computed(() => {
  return items.value
})
const { getColor } = useColors()
const collapseIconColor = computed(() => getColor('secondary'))
const handleBreadcrumbClick = (item: BreadcrumbNavigationItem) => {
  if (!item.hasChildren) {
    router.push(item.to)
  }
}
const { init } = useToast()
const handleLogout = () => {
  logout()
  init({
    message: 'Sesión cerrada exitosamente',
    color: 'success',
  })
  router.push({ name: 'login' })
}</script>

<style lang="scss" scoped>
.x-flip {
  transform: scaleX(-100%);
}
</style>
