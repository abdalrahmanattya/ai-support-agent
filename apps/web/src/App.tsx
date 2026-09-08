import { FormEvent, useEffect, useState } from 'react'
import { ArrowRight, CircleUserRound, Headphones, LifeBuoy, LogOut, MessageSquareText, PackageCheck, RotateCcw, Send, ShieldCheck } from 'lucide-react'
import { Actor, Case, Order, ReturnProposal, request } from './api'

type View = 'support' | 'orders' | 'requests'
type Message = { role: 'user' | 'assistant'; text: string }

function App() {
  const [me, setMe] = useState<Actor | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => { request<Actor>('/api/me').then(setMe).catch(() => setMe(null)).finally(() => setLoading(false)) }, [])
  if (loading) return <div className="center"><div className="spinner" /><p>Opening CircuitCare…</p></div>
  if (!me) return <SignIn />
  return me.role === 'staff' ? <Staff actor={me} /> : <Customer actor={me} />
}

function SignIn() {
  return <main className="signin">
    <section className="brand-panel"><div className="brand"><span className="brand-mark"><Headphones /></span>CircuitCare</div><div><p className="eyebrow">Support that stays with you</p><h1>Good answers.<br />Clear next steps.</h1><p className="lead">Get help with an order, troubleshoot a device, or start a return from one calm place.</p></div><p className="fine">Secure access powered by AWS</p></section>
    <section className="signin-card"><div><p className="eyebrow dark">Customer care</p><h2>Welcome back</h2><p>Sign in with your CircuitCare account to see your orders and support history.</p></div><a className="primary wide" href="/auth/login">Continue to sign in <ArrowRight size={18} /></a><p className="privacy"><ShieldCheck size={18} /> Your account determines which records you can access.</p></section>
  </main>
}

function Shell({ actor, view, setView, children }: { actor: Actor; view: View; setView: (v: View) => void; children: React.ReactNode }) {
  const logout = () => request('/auth/logout', { method: 'POST' }).then(() => location.reload())
  return <div className="app-shell"><header><div className="brand"><span className="brand-mark"><Headphones /></span>CircuitCare</div><nav aria-label="Main navigation"><button className={view === 'support' ? 'active' : ''} onClick={() => setView('support')}><MessageSquareText />Support</button><button className={view === 'orders' ? 'active' : ''} onClick={() => setView('orders')}><PackageCheck />Orders</button><button className={view === 'requests' ? 'active' : ''} onClick={() => setView('requests')}><LifeBuoy />Requests</button></nav><div className="account"><CircleUserRound /><span><strong>{actor.display_name}</strong><small>{actor.customer_id}</small></span><button aria-label="Sign out" onClick={logout}><LogOut /></button></div></header><main>{children}</main></div>
}

function Customer({ actor }: { actor: Actor }) {
  const [view, setView] = useState<View>('support')
  return <Shell actor={actor} view={view} setView={setView}>{view === 'support' ? <Support actor={actor} /> : view === 'orders' ? <Orders /> : <Cases />}</Shell>
}

function Support({ actor }: { actor: Actor }) {
  const [messages, setMessages] = useState<Message[]>([{ role: 'assistant', text: `Hi ${actor.display_name.split(' ')[0]}. I can help with products, policies, troubleshooting, and your support questions.` }])
  const [prompt, setPrompt] = useState('')
  const [busy, setBusy] = useState(false)
  const [conversation] = useState(() => crypto.randomUUID())
  async function send(event: FormEvent) { event.preventDefault(); const text = prompt.trim(); if (!text || busy) return; setPrompt(''); setMessages(m => [...m, { role: 'user', text }]); setBusy(true); try { const result = await request<{answer:string}>('/api/chat', { method: 'POST', body: JSON.stringify({ prompt: text, conversation_id: conversation }) }); setMessages(m => [...m, { role: 'assistant', text: result.answer }]) } catch (error) { setMessages(m => [...m, { role: 'assistant', text: error instanceof Error ? error.message : 'Support is unavailable.' }]) } finally { setBusy(false) } }
  return <section className="support-layout"><aside className="welcome-card"><p className="eyebrow">Your support space</p><h1>How can we help?</h1><p>Ask a question or choose a common request.</p><div className="quick"><button onClick={() => setPrompt('Where is my latest order?')}>Track my order <ArrowRight /></button><button onClick={() => setPrompt('How do I reset my headphones?')}>Troubleshoot a device <ArrowRight /></button><button onClick={() => setPrompt('Explain the return policy for opened headphones.')}>Check a return policy <ArrowRight /></button></div></aside><div className="conversation"><div className="conversation-head"><span className="status-dot" /><div><strong>CircuitCare assistant</strong><small>Grounded in approved support information</small></div></div><div className="messages" aria-live="polite">{messages.map((message, index) => <div className={`message ${message.role}`} key={index}>{message.text}</div>)}{busy && <div className="message assistant typing">Thinking <span>•••</span></div>}</div><form className="composer" onSubmit={send}><label className="sr-only" htmlFor="prompt">Support question</label><textarea id="prompt" value={prompt} onChange={e => setPrompt(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} placeholder="Ask CircuitCare…" rows={1} /><button aria-label="Send" disabled={!prompt.trim() || busy}><Send /></button></form></div></section>
}

function Orders() {
  const [orders, setOrders] = useState<Order[]>([]); const [selected, setSelected] = useState<Order | null>(null); const [reason, setReason] = useState(''); const [proposal, setProposal] = useState<ReturnProposal | null>(null); const [notice, setNotice] = useState('')
  useEffect(() => { void request<Order[]>('/api/orders').then(setOrders).catch(error => setNotice(error instanceof Error ? error.message : 'Orders are unavailable.')) }, [])
  async function propose(event: FormEvent) { event.preventDefault(); setNotice(''); try { setProposal(await request('/api/returns/proposals', { method: 'POST', body: JSON.stringify({ order_id: selected?.order_id, reason }) })) } catch (e) { setNotice(e instanceof Error ? e.message : 'Unable to start return') } }
  async function confirm() { if (!proposal) return; try { const value = await request<ReturnProposal>('/api/returns/confirm', { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({ proposal }) }); setProposal(null); setSelected(null); setNotice(`Return ${value.return_id} has been recorded.`) } catch (error) { setNotice(error instanceof Error ? error.message : 'Unable to confirm return.'); setSelected(null) } }
  return <section className="page"><p className="eyebrow dark">Order care</p><h1>Your orders</h1><p className="page-lead">Track deliveries and request eligible returns.</p>{notice && <div className="notice">{notice}</div>}<div className="order-grid">{orders.map(order => <article className="order-card" key={order.order_id}><div className="order-top"><span>{order.status.replaceAll('_', ' ')}</span><small>{order.order_id}</small></div><h2>{order.items.map(i => i.name).join(', ')}</h2><p>{order.items.length} item · ${order.items.reduce((sum, item) => sum + Number(item.unit_price) * item.quantity, 0).toFixed(2)}</p>{order.tracking_number && <p className="tracking">{order.carrier} · {order.tracking_number}</p>}<button className="secondary" onClick={() => { setSelected(order); setProposal(null); setReason('') }}><RotateCcw /> Request a return</button></article>)}</div>{selected && <div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true"><button className="close" onClick={() => setSelected(null)}>×</button><p className="eyebrow dark">Return request</p><h2>{selected.items[0].name}</h2>{proposal ? <><div className="proposal"><strong>Review before confirming</strong><p>Order: {proposal.order_id}</p><p>Simulated refund: ${Number(proposal.amount).toFixed(2)}</p><p>Reason: {proposal.reason}</p></div><button className="primary wide" onClick={confirm}>Confirm return request</button></> : <form onSubmit={propose}><label>Why are you returning this order?<textarea required minLength={3} value={reason} onChange={e => setReason(e.target.value)} /></label><button className="primary wide">Review request</button></form>}</div></div>}</section>
}

function Cases() {
  const [cases, setCases] = useState<Case[]>([]); const [returns, setReturns] = useState<ReturnProposal[]>([]); const [subject, setSubject] = useState(''); const [summary, setSummary] = useState(''); const [error, setError] = useState(''); const load = () => Promise.all([request<Case[]>('/api/cases').then(setCases), request<ReturnProposal[]>('/api/returns').then(setReturns)]).catch(value => setError(value instanceof Error ? value.message : 'Requests are unavailable.'))
  useEffect(() => { void load() }, [])
  async function create(event: FormEvent) { event.preventDefault(); setError(''); try { await request('/api/cases', { method: 'POST', body: JSON.stringify({ subject, summary }) }); setSubject(''); setSummary(''); void load() } catch (value) { setError(value instanceof Error ? value.message : 'Unable to create request.') } }
  return <section className="page"><p className="eyebrow dark">Human support</p><h1>Your requests</h1><p className="page-lead">Follow returns and contact a specialist.</p>{error && <div className="notice">{error}</div>}{returns.length > 0 && <div className="case-list return-list">{returns.map(item => <article key={item.return_id}><span className="pill">{item.status}</span><h2>Return for {item.order_id}</h2><p>Simulated refund: ${Number(item.amount).toFixed(2)} · {item.reason}</p><small>{item.return_id}</small></article>)}</div>}<div className="case-layout"><form className="panel" onSubmit={create}><h2>Contact a specialist</h2><label>Subject<input value={subject} minLength={3} required onChange={e => setSubject(e.target.value)} /></label><label>What happened?<textarea value={summary} minLength={3} required onChange={e => setSummary(e.target.value)} /></label><button className="primary">Create request</button></form><div className="case-list">{cases.length ? cases.map(item => <article key={item.case_id}><span className={`pill ${item.status.toLowerCase()}`}>{item.status.replace('_', ' ')}</span><h2>{item.subject}</h2><p>{item.summary}</p>{item.resolution && <div className="resolution"><strong>Resolution</strong><p>{item.resolution}</p></div>}<small>{item.case_id}</small></article>) : <div className="empty"><LifeBuoy /><h2>No support cases</h2><p>Your specialist cases will appear here.</p></div>}</div></div></section>
}

function Staff({ actor }: { actor: Actor }) {
  const [cases, setCases] = useState<Case[]>([]); const load = () => request<Case[]>('/api/cases').then(setCases); useEffect(() => { void load() }, [])
  async function resolve(item: Case) { const resolution = prompt('Resolution note'); if (!resolution) return; await request(`/api/cases/${item.case_id}`, { method: 'PATCH', body: JSON.stringify({ status: 'RESOLVED', resolution }) }); load() }
  const logout = () => request('/auth/logout', { method: 'POST' }).then(() => location.reload())
  return <div className="app-shell"><header><div className="brand"><span className="brand-mark"><Headphones /></span>CircuitCare <em>Staff</em></div><div className="account"><CircleUserRound /><strong>{actor.display_name}</strong><button aria-label="Sign out" onClick={logout}><LogOut /></button></div></header><main className="page"><p className="eyebrow dark">Support operations</p><h1>Escalation queue</h1><p className="page-lead">Review and resolve customer cases.</p><div className="case-list staff-list">{cases.map(item => <article key={item.case_id}><span className={`pill ${item.status.toLowerCase()}`}>{item.status}</span><small>{item.customer_id} · {item.case_id}</small><h2>{item.subject}</h2><p>{item.summary}</p>{item.status !== 'RESOLVED' && <button className="primary" onClick={() => resolve(item)}>Resolve case</button>}{item.resolution && <div className="resolution">{item.resolution}</div>}</article>)}</div></main></div>
}

export default App
