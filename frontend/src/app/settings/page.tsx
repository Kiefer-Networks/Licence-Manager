'use client';

import { useEffect, useState } from 'react';
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
import { api, PaymentMethod, PaymentMethodCreate } from '@/lib/api';
import { Plus, Pencil, Trash2, CheckCircle2, XCircle, Loader2, Globe, X, CreditCard, Landmark, Wallet, AlertTriangle } from 'lucide-react';

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Company Domains state
  const [companyDomains, setCompanyDomains] = useState<string[]>([]);
  const [newDomain, setNewDomain] = useState('');
  const [savingDomains, setSavingDomains] = useState(false);

  // Payment Methods state
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [paymentMethodDialogOpen, setPaymentMethodDialogOpen] = useState(false);
  const [editingPaymentMethod, setEditingPaymentMethod] = useState<PaymentMethod | null>(null);
  const [savingPaymentMethod, setSavingPaymentMethod] = useState(false);
  const [paymentMethodForm, setPaymentMethodForm] = useState({
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
    Promise.all([fetchCompanyDomains(), fetchPaymentMethods()]).finally(() => setLoading(false));
  }, []);

  async function fetchCompanyDomains() {
    try {
      const domains = await api.getCompanyDomains();
      setCompanyDomains(domains);
    } catch (error) {
      console.error('Failed to fetch company domains:', error);
    }
  }

  async function fetchPaymentMethods() {
    try {
      const data = await api.getPaymentMethods();
      setPaymentMethods(data.items);
    } catch (error) {
      console.error('Failed to fetch payment methods:', error);
    }
  }

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  // Company Domains handlers
  const handleAddDomain = () => {
    const domain = newDomain.trim().toLowerCase();
    if (!domain) return;
    if (companyDomains.includes(domain)) {
      showToast('error', 'Domain already exists');
      return;
    }
    setCompanyDomains([...companyDomains, domain]);
    setNewDomain('');
  };

  const handleRemoveDomain = (domain: string) => {
    setCompanyDomains(companyDomains.filter((d) => d !== domain));
  };

  const handleSaveDomains = async () => {
    setSavingDomains(true);
    try {
      await api.setCompanyDomains(companyDomains);
      showToast('success', 'Company domains saved');
    } catch (error: any) {
      showToast('error', error.message || 'Failed to save domains');
    } finally {
      setSavingDomains(false);
    }
  };

  // Payment Methods handlers
  const resetPaymentMethodForm = () => {
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
  };

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
        notes: method.notes || '',
        is_default: method.is_default,
      });
    } else {
      setEditingPaymentMethod(null);
      resetPaymentMethodForm();
    }
    setPaymentMethodDialogOpen(true);
  };

  const handleSavePaymentMethod = async () => {
    setSavingPaymentMethod(true);
    try {
      const details: Record<string, any> = {};

      if (paymentMethodForm.type === 'credit_card') {
        details.card_holder = paymentMethodForm.card_holder;
        details.card_last_four = paymentMethodForm.card_last_four;
        details.expiry_month = paymentMethodForm.expiry_month;
        details.expiry_year = paymentMethodForm.expiry_year;
      } else if (paymentMethodForm.type === 'bank_account') {
        details.bank_name = paymentMethodForm.bank_name;
        details.account_holder = paymentMethodForm.account_holder;
        details.iban_last_four = paymentMethodForm.iban_last_four;
      } else {
        details.provider_name = paymentMethodForm.provider_name;
      }

      const data: PaymentMethodCreate = {
        name: paymentMethodForm.name,
        type: paymentMethodForm.type,
        details,
        is_default: paymentMethodForm.is_default,
        notes: paymentMethodForm.notes || undefined,
      };

      if (editingPaymentMethod) {
        await api.updatePaymentMethod(editingPaymentMethod.id, data);
        showToast('success', 'Payment method updated');
      } else {
        await api.createPaymentMethod(data);
        showToast('success', 'Payment method added');
      }

      await fetchPaymentMethods();
      setPaymentMethodDialogOpen(false);
      resetPaymentMethodForm();
      setEditingPaymentMethod(null);
    } catch (error: any) {
      showToast('error', error.message || 'Failed to save payment method');
    } finally {
      setSavingPaymentMethod(false);
    }
  };

  const handleDeletePaymentMethod = async (id: string) => {
    try {
      await api.deletePaymentMethod(id);
      await fetchPaymentMethods();
      showToast('success', 'Payment method deleted');
    } catch (error: any) {
      showToast('error', error.message || 'Failed to delete payment method');
    }
  };

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

  if (loading) {
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
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="text-muted-foreground text-sm mt-0.5">Manage company settings and payment methods</p>
        </div>

        {/* Company Domains Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">Company Domains</h2>
            </div>
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              Configure your company email domains. Licenses assigned to users with external email addresses will be highlighted with a warning.
            </p>

            <div className="flex gap-2">
              <Input
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder="e.g., company.com"
                className="flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddDomain();
                  }
                }}
              />
              <Button variant="outline" size="sm" onClick={handleAddDomain}>
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Add
              </Button>
            </div>

            {companyDomains.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {companyDomains.map((domain) => (
                  <Badge
                    key={domain}
                    variant="secondary"
                    className="bg-zinc-100 text-zinc-700 pr-1.5 flex items-center gap-1"
                  >
                    {domain}
                    <button
                      onClick={() => handleRemoveDomain(domain)}
                      className="ml-1 hover:bg-zinc-200 rounded p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">No domains configured</p>
            )}

            <div className="pt-2 border-t">
              <Button size="sm" onClick={handleSaveDomains} disabled={savingDomains}>
                {savingDomains ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Save Domains
              </Button>
            </div>
          </div>
        </section>

        {/* Payment Methods Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">Payment Methods</h2>
            </div>
            <Button size="sm" variant="outline" onClick={() => handleOpenPaymentMethodDialog()}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Add Payment Method
            </Button>
          </div>

          {paymentMethods.length > 0 ? (
            <div className="border rounded-lg bg-white divide-y">
              {paymentMethods.map((method) => (
                <div key={method.id} className="flex items-center justify-between p-4">
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
                          <Badge variant="secondary" className="text-xs">Default</Badge>
                        )}
                        {method.is_expiring && (
                          <Badge variant="outline" className="text-xs text-amber-600 border-amber-200 bg-amber-50">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            Expires {method.days_until_expiry !== null && method.days_until_expiry !== undefined
                              ? (method.days_until_expiry <= 0 ? 'soon' : `in ${method.days_until_expiry} days`)
                              : 'soon'}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {method.type === 'credit_card' && method.details.card_last_four && (
                          <>•••• {method.details.card_last_four} · Expires {method.details.expiry_month}/{method.details.expiry_year}</>
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
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenPaymentMethodDialog(method)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600" onClick={() => handleDeletePaymentMethod(method.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="border rounded-lg bg-white p-6 text-center">
              <CreditCard className="h-8 w-8 mx-auto text-zinc-300 mb-2" />
              <p className="text-sm text-muted-foreground">No payment methods configured</p>
              <p className="text-xs text-muted-foreground mt-1">Add credit cards, bank accounts, or other payment methods</p>
            </div>
          )}
        </section>
      </div>

      {/* Payment Method Dialog */}
      <Dialog open={paymentMethodDialogOpen} onOpenChange={setPaymentMethodDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingPaymentMethod ? 'Edit Payment Method' : 'Add Payment Method'}</DialogTitle>
            <DialogDescription>
              {editingPaymentMethod ? 'Update the payment method details.' : 'Add a new payment method for tracking.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium">Name</Label>
              <Input
                value={paymentMethodForm.name}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, name: e.target.value })}
                placeholder="e.g., Company Visa"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">Type</Label>
              <Select
                value={paymentMethodForm.type}
                onValueChange={(v) => setPaymentMethodForm({ ...paymentMethodForm, type: v })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="bank_account">Bank Account</SelectItem>
                  <SelectItem value="credit_card">Credit Card</SelectItem>
                  <SelectItem value="invoice">Invoice</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                  <SelectItem value="paypal">PayPal</SelectItem>
                  <SelectItem value="stripe">Stripe</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {paymentMethodForm.type === 'credit_card' && (
              <>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">Card Holder</Label>
                  <Input
                    value={paymentMethodForm.card_holder}
                    onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, card_holder: e.target.value })}
                    placeholder="Name on card"
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">Last 4 Digits</Label>
                    <Input
                      value={paymentMethodForm.card_last_four}
                      onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, card_last_four: e.target.value.slice(0, 4) })}
                      placeholder="1234"
                      maxLength={4}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">Expiry Month</Label>
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
                    <Label className="text-xs font-medium">Expiry Year</Label>
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
                  <Label className="text-xs font-medium">Bank Name</Label>
                  <Input
                    value={paymentMethodForm.bank_name}
                    onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, bank_name: e.target.value })}
                    placeholder="e.g., Deutsche Bank"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">Account Holder</Label>
                    <Input
                      value={paymentMethodForm.account_holder}
                      onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, account_holder: e.target.value })}
                      placeholder="Account holder name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">IBAN Last 4</Label>
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
                <Label className="text-xs font-medium">Provider / Account</Label>
                <Input
                  value={paymentMethodForm.provider_name}
                  onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, provider_name: e.target.value })}
                  placeholder="e.g., account@company.com"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label className="text-xs font-medium">Notes (optional)</Label>
              <Input
                value={paymentMethodForm.notes}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, notes: e.target.value })}
                placeholder="Any additional notes"
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
              <Label htmlFor="is_default" className="text-xs font-medium cursor-pointer">Set as default payment method</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPaymentMethodDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSavePaymentMethod} disabled={!paymentMethodForm.name || savingPaymentMethod}>
              {savingPaymentMethod ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Saving...</> : (editingPaymentMethod ? 'Save Changes' : 'Add Payment Method')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
