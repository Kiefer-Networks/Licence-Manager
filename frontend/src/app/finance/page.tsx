'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
import { AppLayout } from '@/components/layout/app-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import {
  Plus,
  Pencil,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  CreditCard,
  Landmark,
  Wallet,
  AlertTriangle,
} from 'lucide-react';
import { usePaymentMethods } from '@/hooks/use-payment-methods';

export default function FinancePage() {
  const t = useTranslations('finance');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();
  const canCreate = hasPermission(Permissions.PAYMENT_METHODS_CREATE);
  const canUpdate = hasPermission(Permissions.PAYMENT_METHODS_UPDATE);
  const canDelete = hasPermission(Permissions.PAYMENT_METHODS_DELETE);

  const {
    loading,
    toast,
    paymentMethods,
    paymentMethodDialogOpen,
    setPaymentMethodDialogOpen,
    editingPaymentMethod,
    savingPaymentMethod,
    paymentMethodForm,
    setPaymentMethodForm,
    handleOpenPaymentMethodDialog,
    handleSavePaymentMethod,
    handleDeletePaymentMethod,
  } = usePaymentMethods(t, tCommon);

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.PAYMENT_METHODS_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  const getPaymentMethodIcon = (type: string) => {
    switch (type) {
      case 'credit_card':
        return <CreditCard className="h-4 w-4" />;
      case 'bank_account':
        return <Landmark className="h-4 w-4" />;
      default:
        return <Wallet className="h-4 w-4" />;
    }
  };

  if (authLoading || loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Toast */}
        {toast && (
          <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'success' ? 'bg-zinc-900 text-white' : 'bg-red-600 text-white'
          }`}>
            {toast.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            {toast.text}
          </div>
        )}

        {/* Header */}
        <div className="pt-2">
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{t('description')}</p>
        </div>

        {/* Payment Methods Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('paymentMethods')}</h2>
            </div>
            {canCreate && (
              <Button size="sm" variant="outline" onClick={() => handleOpenPaymentMethodDialog()}>
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                {t('addPaymentMethod')}
              </Button>
            )}
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              {t('paymentMethodsDescription')}
            </p>

            {paymentMethods.length > 0 ? (
              <div className="divide-y -mx-4">
                {paymentMethods.map((method) => (
                  <div key={method.id} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${
                        method.is_expiring ? 'bg-amber-50 text-amber-600' : 'bg-zinc-100 text-zinc-600'
                      }`}>
                        {getPaymentMethodIcon(method.type)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-sm">{method.name}</p>
                          {method.is_default && (
                            <Badge variant="secondary" className="text-xs">{t('default')}</Badge>
                          )}
                          {method.is_expiring && (
                            <Badge variant="outline" className="text-xs text-amber-600 border-amber-200 bg-amber-50">
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              {method.days_until_expiry !== null && method.days_until_expiry !== undefined && method.days_until_expiry > 0
                                ? t('expiresInDays', { days: method.days_until_expiry })
                                : t('expiresSoon')}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {method.type === 'credit_card' && method.details.card_last_four && (
                            <>•••• {method.details.card_last_four} · {t('expires')} {method.details.expiry_month}/{method.details.expiry_year}</>
                          )}
                          {method.type === 'bank_account' && method.details.bank_name && (
                            <>{method.details.bank_name} {method.details.iban_last_four && `· •••• ${method.details.iban_last_four}`}</>
                          )}
                          {method.type !== 'credit_card' && method.type !== 'bank_account' && method.details.provider_name && (
                            <>{method.details.provider_name}</>
                          )}
                          {method.type !== 'credit_card' && method.type !== 'bank_account' && !method.details.provider_name && (
                            <span className="capitalize">{method.type.replace('_', ' ')}</span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {canUpdate && (
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenPaymentMethodDialog(method)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                      )}
                      {canDelete && (
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600" onClick={() => handleDeletePaymentMethod(method.id)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <CreditCard className="h-8 w-8 mx-auto text-zinc-300 mb-2" />
                <p className="text-sm text-muted-foreground">{t('noPaymentMethods')}</p>
                <p className="text-xs text-muted-foreground mt-1">{t('addPaymentMethodsNote')}</p>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Payment Method Dialog */}
      <Dialog open={paymentMethodDialogOpen} onOpenChange={setPaymentMethodDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingPaymentMethod ? t('editPaymentMethod') : t('addPaymentMethod')}</DialogTitle>
            <DialogDescription>
              {editingPaymentMethod ? t('editPaymentMethodDescription') : t('createPaymentMethodDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium">{tCommon('name')}</Label>
              <Input
                value={paymentMethodForm.name}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, name: e.target.value })}
                placeholder={t('paymentNamePlaceholder')}
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">{tCommon('type')}</Label>
              <Select
                value={paymentMethodForm.type}
                onValueChange={(v) => setPaymentMethodForm({ ...paymentMethodForm, type: v })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="apple_pay">{t('applePay')}</SelectItem>
                  <SelectItem value="bank_account">{t('bankAccount')}</SelectItem>
                  <SelectItem value="check">{t('check')}</SelectItem>
                  <SelectItem value="credit_card">{t('creditCard')}</SelectItem>
                  <SelectItem value="google_pay">{t('googlePay')}</SelectItem>
                  <SelectItem value="invoice">{tCommon('invoice')}</SelectItem>
                  <SelectItem value="klarna">{t('klarna')}</SelectItem>
                  <SelectItem value="paypal">{t('paypal')}</SelectItem>
                  <SelectItem value="sepa">{t('sepa')}</SelectItem>
                  <SelectItem value="stripe">{t('stripe')}</SelectItem>
                  <SelectItem value="wire_transfer">{t('wireTransfer')}</SelectItem>
                  <SelectItem value="other">{t('otherPayment')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {paymentMethodForm.type === 'credit_card' && (
              <>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">{t('cardHolder')}</Label>
                  <Input
                    value={paymentMethodForm.card_holder}
                    onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, card_holder: e.target.value })}
                    placeholder={t('nameOnCard')}
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('lastFourDigits')}</Label>
                    <Input
                      value={paymentMethodForm.card_last_four}
                      onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, card_last_four: e.target.value.slice(0, 4) })}
                      placeholder="1234"
                      maxLength={4}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('expiryMonth')}</Label>
                    <Select
                      value={paymentMethodForm.expiry_month}
                      onValueChange={(v) => setPaymentMethodForm({ ...paymentMethodForm, expiry_month: v })}
                    >
                      <SelectTrigger><SelectValue placeholder="MM" /></SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 12 }, (_, i) => {
                          const m = String(i + 1).padStart(2, '0');
                          return <SelectItem key={m} value={m}>{m}</SelectItem>;
                        })}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('expiryYear')}</Label>
                    <Select
                      value={paymentMethodForm.expiry_year}
                      onValueChange={(v) => setPaymentMethodForm({ ...paymentMethodForm, expiry_year: v })}
                    >
                      <SelectTrigger><SelectValue placeholder="YY" /></SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 10 }, (_, i) => {
                          const y = String(new Date().getFullYear() + i).slice(-2);
                          return <SelectItem key={y} value={y}>{y}</SelectItem>;
                        })}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}

            {paymentMethodForm.type === 'bank_account' && (
              <>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">{t('bankName')}</Label>
                  <Input
                    value={paymentMethodForm.bank_name}
                    onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, bank_name: e.target.value })}
                    placeholder={t('bankNamePlaceholder')}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('accountHolder')}</Label>
                    <Input
                      value={paymentMethodForm.account_holder}
                      onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, account_holder: e.target.value })}
                      placeholder={t('accountHolderPlaceholder')}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('ibanLastFour')}</Label>
                    <Input
                      value={paymentMethodForm.iban_last_four}
                      onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, iban_last_four: e.target.value.slice(0, 4) })}
                      placeholder="1234"
                      maxLength={4}
                    />
                  </div>
                </div>
              </>
            )}

            {paymentMethodForm.type !== 'credit_card' && paymentMethodForm.type !== 'bank_account' && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('providerName')}</Label>
                <Input
                  value={paymentMethodForm.provider_name}
                  onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, provider_name: e.target.value })}
                  placeholder={t('providerNamePlaceholder')}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('notes')}</Label>
              <Textarea
                value={paymentMethodForm.notes}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, notes: e.target.value })}
                placeholder={t('notesPlaceholder')}
                rows={2}
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_default"
                checked={paymentMethodForm.is_default}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, is_default: e.target.checked })}
                className="rounded border-zinc-300"
              />
              <Label htmlFor="is_default" className="text-sm cursor-pointer">{t('setAsDefault')}</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPaymentMethodDialogOpen(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleSavePaymentMethod} disabled={!paymentMethodForm.name || savingPaymentMethod}>
              {savingPaymentMethod && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {editingPaymentMethod ? tCommon('save') : tCommon('create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
