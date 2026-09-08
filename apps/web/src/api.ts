export type Actor = { subject: string; customer_id: string | null; role: 'customer' | 'staff'; display_name: string }
export type OrderItem = { sku: string; name: string; quantity: number; unit_price: string; category: string; opened: boolean }
export type Order = { order_id: string; customer_id: string; status: string; delivered_on: string | null; items: OrderItem[]; tracking_number: string | null; carrier: string | null }
export type ReturnProposal = { return_id: string; order_id: string; customer_id: string; amount: string; reason: string; status: string; created_at: string }
export type Case = { case_id: string; customer_id: string; subject: string; summary: string; status: string; resolution: string | null; created_at: string; updated_at: string }

function csrf() {
  return document.cookie.split('; ').find((value) => value.startsWith('circuitcare_csrf='))?.split('=')[1] ?? ''
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf(), ...init.headers } })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.error?.message ?? body.detail ?? 'CircuitCare could not complete that request.')
  }
  return response.status === 204 ? (undefined as T) : response.json()
}
