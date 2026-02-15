'use client';

import { useEffect, useState } from 'react';
import { api, PaymentMethod, PaymentMethodCreate, PaymentMethodDetails } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

/**
 * Toast state for user feedback.
 */
export interface PaymentMethodsToast {
  type: 'success' | 'error';
  text: string;
}

/**
 * Form state for creating/editing a payment method.
 */
export interface PaymentMethodFormState {
  name: string;
  type: string;
  card_holder: string;
  card_last_four: string;
  expiry_month: string;
  expiry_year: string;
  bank_name: string;
  account_holder: string;
  iban_last_four: string;
  provider_name: string;
  notes: string;
  is_default: boolean;
}

/**
 * Return type for the usePaymentMethods hook.
 */
export interface UsePaymentMethodsReturn {
  // Loading & toast
  loading: boolean;
  toast: PaymentMethodsToast | null;

  // Data
  paymentMethods: PaymentMethod[];

  // Dialog states
  paymentMethodDialogOpen: boolean;
  setPaymentMethodDialogOpen: (open: boolean) => void;
  editingPaymentMethod: PaymentMethod | null;
  savingPaymentMethod: boolean;

  // Form
  paymentMethodForm: PaymentMethodFormState;
  setPaymentMethodForm: React.Dispatch<React.SetStateAction<PaymentMethodFormState>>;

  // Actions
  handleOpenPaymentMethodDialog: (method?: PaymentMethod) => void;
  handleSavePaymentMethod: () => Promise<void>;
  handleDeletePaymentMethod: (id: string) => Promise<void>;
}

/**
 * Custom hook that encapsulates all business logic for the Finance page.
 * Manages payment methods CRUD, dialog states, and form management.
 */
export function usePaymentMethods(
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
): UsePaymentMethodsReturn {
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<PaymentMethodsToast | null>(null);

  // Payment Methods state
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [paymentMethodDialogOpen, setPaymentMethodDialogOpen] = useState(false);
  const [editingPaymentMethod, setEditingPaymentMethod] = useState<PaymentMethod | null>(null);
  const [savingPaymentMethod, setSavingPaymentMethod] = useState(false);
  const [paymentMethodForm, setPaymentMethodForm] = useState<PaymentMethodFormState>({
    name: '',
    type: 'credit_card',
    card_holder: '',
    card_last_four: '',
    expiry_month: '',
    expiry_year: '',
    bank_name: '',
    account_holder: '',
    iban_last_four: '',
    provider_name: '',
    notes: '',
    is_default: false,
  });

  useEffect(() => {
    fetchPaymentMethods().finally(() => setLoading(false));
  }, []);

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  async function fetchPaymentMethods() {
    try {
      const data = await api.getPaymentMethods();
      setPaymentMethods(data.items);
    } catch (error) {
      handleSilentError('fetchPaymentMethods', error);
    }
  }

  const handleOpenPaymentMethodDialog = (method?: PaymentMethod) => {
    if (method) {
      setEditingPaymentMethod(method);
      setPaymentMethodForm({
        name: method.name,
        type: method.type,
        card_holder: method.details.card_holder || '',
        card_last_four: method.details.card_last_four || '',
        expiry_month: method.details.expiry_month || '',
        expiry_year: method.details.expiry_year || '',
        bank_name: method.details.bank_name || '',
        account_holder: method.details.account_holder || '',
        iban_last_four: method.details.iban_last_four || '',
        provider_name: method.details.provider_name || '',
        notes: String(method.details.notes || ''),
        is_default: method.is_default,
      });
    } else {
      setEditingPaymentMethod(null);
      setPaymentMethodForm({
        name: '',
        type: 'credit_card',
        card_holder: '',
        card_last_four: '',
        expiry_month: '',
        expiry_year: '',
        bank_name: '',
        account_holder: '',
        iban_last_four: '',
        provider_name: '',
        notes: '',
        is_default: false,
      });
    }
    setPaymentMethodDialogOpen(true);
  };

  const handleSavePaymentMethod = async () => {
    setSavingPaymentMethod(true);
    try {
      const details: PaymentMethodDetails = {};
      if (paymentMethodForm.type === 'credit_card') {
        details.card_holder = paymentMethodForm.card_holder || undefined;
        details.card_last_four = paymentMethodForm.card_last_four || undefined;
        details.expiry_month = paymentMethodForm.expiry_month || undefined;
        details.expiry_year = paymentMethodForm.expiry_year || undefined;
      } else if (paymentMethodForm.type === 'bank_account') {
        details.bank_name = paymentMethodForm.bank_name || undefined;
        details.account_holder = paymentMethodForm.account_holder || undefined;
        details.iban_last_four = paymentMethodForm.iban_last_four || undefined;
      } else {
        details.provider_name = paymentMethodForm.provider_name || undefined;
      }
      details.notes = paymentMethodForm.notes || undefined;

      const data: PaymentMethodCreate = {
        name: paymentMethodForm.name,
        type: paymentMethodForm.type as PaymentMethodCreate['type'],
        is_default: paymentMethodForm.is_default,
        details,
      };

      if (editingPaymentMethod) {
        await api.updatePaymentMethod(editingPaymentMethod.id, data);
        showToast('success', t('paymentMethodUpdated'));
      } else {
        await api.createPaymentMethod(data);
        showToast('success', t('paymentMethodCreated'));
      }

      setPaymentMethodDialogOpen(false);
      await fetchPaymentMethods();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSave');
      showToast('error', message);
    } finally {
      setSavingPaymentMethod(false);
    }
  };

  const handleDeletePaymentMethod = async (id: string) => {
    try {
      await api.deletePaymentMethod(id);
      await fetchPaymentMethods();
      showToast('success', t('paymentMethodDeleted'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToDelete');
      showToast('error', message);
    }
  };

  return {
    // Loading & toast
    loading,
    toast,

    // Data
    paymentMethods,

    // Dialog states
    paymentMethodDialogOpen,
    setPaymentMethodDialogOpen,
    editingPaymentMethod,
    savingPaymentMethod,

    // Form
    paymentMethodForm,
    setPaymentMethodForm,

    // Actions
    handleOpenPaymentMethodDialog,
    handleSavePaymentMethod,
    handleDeletePaymentMethod,
  };
}
