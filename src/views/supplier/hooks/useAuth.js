// src/views/supplier/hooks/useAuth.js
import { computed } from 'vue'
import { checkPermission } from '@/utils/auth'

/**
 * 供应商评分权限 hooks
 */
export function useSupplierScoreAuth() {
  const hasEditPermission = computed(() => checkPermission('supplier:score:edit'))
  const hasViewPermission = computed(() => checkPermission('supplier:score:view'))
  const hasBatchPermission = computed(() => checkPermission('supplier:score:batch'))

  return {
    hasEditPermission,
    hasViewPermission,
    hasBatchPermission
  }
}
