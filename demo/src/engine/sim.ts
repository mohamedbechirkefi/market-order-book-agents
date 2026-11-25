// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Port of src/market/book.py, ledger.py, agents.py and simulate.py (the research engine),
// statement for statement. Integer prices and quantities; trades at the resting order's
// price; price-time priority; market orders walk the book and cancel their remainder.
// engine.test.ts compares this port with a fixture produced by the Python engine.
import { makeStreams, type Stream } from "./rng";

export const BUY = 1;
export const SELL = -1;
type Side = 1 | -1;

export interface Composition {
  ZI: number;
  TF: number;
  MR: number;
  PA: number;
}

export interface SimConfig {
  composition: Composition;
  steps: number;
  burn_in: number;
  sample_interval: number;
  tick: number;
  initial_price: number;
  max_order_size: number;
  zi_market_prob: number;
  zi_limit_offset: number;
  order_lifetime: number;
  lookback: number;
  strategic_market_prob: number;
  pa_skip_prob: number;
  initial_cash: number;
  initial_inventory: number;
  initial_orders_per_side: number;
  shock_step: number | null;
  shock_fraction: number;
  shock_inventory: number;
}

/** Defaults of src/market/config.py (the frozen EXP-001 values). */
export const DEFAULT_CONFIG: SimConfig = {
  composition: { ZI: 100, TF: 0, MR: 0, PA: 0 },
  steps: 100_000,
  burn_in: 10_000,
  sample_interval: 50,
  tick: 1,
  initial_price: 1_000,
  max_order_size: 5,
  zi_market_prob: 0.2,
  zi_limit_offset: 10,
  order_lifetime: 2_000,
  lookback: 500,
  strategic_market_prob: 0.5,
  pa_skip_prob: 0.0,
  initial_cash: 1_000_000,
  initial_inventory: 1_000,
  initial_orders_per_side: 20,
  shock_step: null,
  shock_fraction: 0.5,
  shock_inventory: 1_000_000,
};

export class SimError extends Error {}

const isInt = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v);
const isProb = (v: unknown): boolean => typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 1;

export function validateConfig(c: SimConfig): SimConfig {
  const comp = c.composition;
  for (const k of ["ZI", "TF", "MR", "PA"] as const) if (!isInt(comp[k]) || comp[k] < 0) throw new SimError(`composition.${k} must be an int >= 0`);
  if (comp.ZI + comp.TF + comp.MR + comp.PA < 1) throw new SimError("composition must contain at least one agent");
  const ints: [keyof SimConfig, number][] = [
    ["steps", 1], ["burn_in", 0], ["sample_interval", 1], ["tick", 1], ["initial_price", 1], ["max_order_size", 1],
    ["zi_limit_offset", 0], ["order_lifetime", 1], ["lookback", 1], ["initial_cash", 0], ["initial_inventory", 0],
    ["initial_orders_per_side", 0],
  ];
  for (const [k, lo] of ints) {
    const v = c[k];
    if (!isInt(v) || v < lo) throw new SimError(`${k} must be an int >= ${lo}`);
  }
  if (c.burn_in >= c.steps) throw new SimError("burn_in must be < steps");
  if (c.initial_price % c.tick !== 0) throw new SimError("initial_price must be a multiple of tick");
  for (const k of ["zi_market_prob", "strategic_market_prob", "pa_skip_prob"] as const) if (!isProb(c[k])) throw new SimError(`${k} must be in [0, 1]`);
  if (c.initial_orders_per_side > 0 && comp.ZI < 1) throw new SimError("initial book seeding needs at least one ZI agent");
  if (c.shock_step !== null) {
    if (!isInt(c.shock_step) || c.shock_step < 1 || c.shock_step > c.steps) throw new SimError("shock_step out of range");
    if (!isProb(c.shock_fraction)) throw new SimError("shock_fraction must be in [0, 1]");
    if (!isInt(c.shock_inventory) || c.shock_inventory < 0) throw new SimError("shock_inventory must be an int >= 0");
  }
  return c;
}

// ---------------------------------------------------------------- book.py

class Order {
  constructor(
    public oid: number,
    public owner: number,
    public side: Side,
    public price: number,
    public qty: number,
    public seq: number,
    public expiry: number | null,
  ) {}
}

interface Fill {
  maker_oid: number;
  maker_owner: number;
  taker_owner: number;
  taker_side: Side;
  price: number;
  qty: number;
}

/** FIFO queue with O(1) popleft (collections.deque in the Python engine). */
class Queue {
  items: Order[] = [];
  head = 0;
  get length(): number {
    return this.items.length - this.head;
  }
  first(): Order {
    return this.items[this.head];
  }
  popleft(): void {
    this.head++;
    if (this.head > 64 && this.head * 2 > this.items.length) {
      this.items = this.items.slice(this.head);
      this.head = 0;
    }
  }
  push(o: Order): void {
    this.items.push(o);
  }
  live(): Order[] {
    return this.items.slice(this.head).filter((o) => o.qty > 0);
  }
}

/** Binary min-heap (heapq). Only the minimum matters, so any valid heap gives the same results. */
class MinHeap<T> {
  a: T[] = [];
  constructor(private less: (x: T, y: T) => boolean) {}
  get size(): number {
    return this.a.length;
  }
  top(): T {
    return this.a[0];
  }
  push(v: T): void {
    const a = this.a;
    a.push(v);
    let i = a.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (!this.less(a[i], a[p])) break;
      [a[i], a[p]] = [a[p], a[i]];
      i = p;
    }
  }
  pop(): T {
    const a = this.a;
    const top = a[0];
    const last = a.pop() as T;
    if (a.length > 0) {
      a[0] = last;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1;
        const r = l + 1;
        let m = i;
        if (l < a.length && this.less(a[l], a[m])) m = l;
        if (r < a.length && this.less(a[r], a[m])) m = r;
        if (m === i) break;
        [a[i], a[m]] = [a[m], a[i]];
        i = m;
      }
    }
    return top;
  }
}

class OrderBook {
  levels = new Map<Side, Map<number, Queue>>([[BUY, new Map()], [SELL, new Map()]]);
  levelQty = new Map<Side, Map<number, number>>([[BUY, new Map()], [SELL, new Map()]]);
  heaps = new Map<Side, MinHeap<number>>([[BUY, new MinHeap((x, y) => x < y)], [SELL, new MinHeap((x, y) => x < y)]]);
  orders = new Map<number, Order>();
  nextOid = 1;
  nextSeq = 1;

  best(side: Side): number | null {
    const heap = this.heaps.get(side)!;
    const lq = this.levelQty.get(side)!;
    while (heap.size > 0) {
      const p = side === BUY ? -heap.top() : heap.top();
      if ((lq.get(p) ?? 0) > 0) return p;
      heap.pop();
      lq.delete(p);
      this.levels.get(side)!.delete(p);
    }
    return null;
  }

  qtyAt(side: Side, price: number): number {
    return this.levelQty.get(side)!.get(price) ?? 0;
  }

  depth(side: Side): number {
    let s = 0;
    for (const q of this.levelQty.get(side)!.values()) s += q;
    return s;
  }

  snapshot(side: Side, levels: number): [number, number][] {
    const lq = this.levelQty.get(side)!;
    const prices = [...lq.entries()].filter(([, q]) => q > 0).map(([p]) => p);
    prices.sort((x, y) => (side === BUY ? y - x : x - y));
    return prices.slice(0, levels).map((p) => [p, lq.get(p)!]);
  }

  rest(owner: number, side: Side, price: number, qty: number, expiry: number | null): Order {
    const o = new Order(this.nextOid, owner, side, price, qty, this.nextSeq, expiry);
    this.nextOid++;
    this.nextSeq++;
    const lv = this.levels.get(side)!;
    if (!lv.has(price)) lv.set(price, new Queue());
    lv.get(price)!.push(o);
    const lq = this.levelQty.get(side)!;
    if ((lq.get(price) ?? 0) === 0) this.heaps.get(side)!.push(side === BUY ? -price : price);
    lq.set(price, (lq.get(price) ?? 0) + qty);
    this.orders.set(o.oid, o);
    return o;
  }

  match(takerOwner: number, side: Side, qty: number, limit: number | null, cashCap: number | null): [Fill[], number] {
    const opp = (-side) as Side;
    const fills: Fill[] = [];
    let remaining = qty;
    let budget = cashCap;
    const lv = this.levels.get(opp)!;
    const lq = this.levelQty.get(opp)!;
    while (remaining > 0) {
      const p = this.best(opp);
      if (p === null) break;
      if (limit !== null && ((side === BUY && p > limit) || (side === SELL && p < limit))) break;
      if (budget !== null) {
        if (Math.floor(budget / p) <= 0) break;
      }
      const queue = lv.get(p)!;
      while (remaining > 0 && queue.length > 0) {
        const o = queue.first();
        if (o.qty === 0) {
          queue.popleft();
          continue;
        }
        let take = Math.min(remaining, o.qty);
        if (budget !== null) {
          take = Math.min(take, Math.floor(budget / p));
          if (take <= 0) break;
          budget -= take * p;
        }
        o.qty -= take;
        lq.set(p, lq.get(p)! - take);
        remaining -= take;
        fills.push({ maker_oid: o.oid, maker_owner: o.owner, taker_owner: takerOwner, taker_side: side, price: p, qty: take });
        if (o.qty === 0) {
          queue.popleft();
          this.orders.delete(o.oid);
        }
      }
      if (budget !== null && Math.floor(budget / p) <= 0 && remaining > 0 && (lq.get(p) ?? 0) > 0) break;
    }
    return [fills, remaining];
  }

  submitLimit(owner: number, side: Side, price: number, qty: number, expiry: number | null): [Fill[], Order | null] {
    if (!isInt(price) || price < 1 || !isInt(qty) || qty < 1) throw new SimError("price and qty must be positive ints");
    const [fills, remaining] = this.match(owner, side, qty, price, null);
    const rested = remaining > 0 ? this.rest(owner, side, price, remaining, expiry) : null;
    if (rested === null) this.nextSeq++;
    return [fills, rested];
  }

  submitMarket(owner: number, side: Side, qty: number, cashCap: number | null): [Fill[], number] {
    if (!isInt(qty) || qty < 1) throw new SimError("qty must be a positive int");
    this.nextSeq++;
    return this.match(owner, side, qty, null, cashCap);
  }

  cancel(oid: number): Order {
    const o = this.orders.get(oid);
    if (o === undefined) throw new SimError(`unknown or inactive order id ${oid}`);
    this.orders.delete(oid);
    const removed = new Order(o.oid, o.owner, o.side, o.price, o.qty, o.seq, o.expiry);
    const lq = this.levelQty.get(o.side)!;
    lq.set(o.price, lq.get(o.price)! - o.qty);
    o.qty = 0;
    return removed;
  }

  restingOrders(): Order[] {
    const out: Order[] = [];
    for (const side of [BUY, SELL] as Side[]) {
      const lv = this.levels.get(side)!;
      const prices = [...lv.keys()].sort((x, y) => (side === BUY ? y - x : x - y));
      for (const p of prices) out.push(...lv.get(p)!.live());
    }
    return out;
  }

  checkInvariants(): void {
    let live = 0;
    for (const side of [BUY, SELL] as Side[]) {
      for (const [p, queue] of this.levels.get(side)!) {
        const q = queue.live();
        let s = 0;
        for (const o of q) s += o.qty;
        if (s !== (this.levelQty.get(side)!.get(p) ?? 0)) throw new SimError("level quantity mismatch");
        for (let i = 1; i < q.length; i++) if (q[i].seq < q[i - 1].seq) throw new SimError("time priority broken within a level");
        for (const o of q) if (o.price !== p || o.side !== side || this.orders.get(o.oid) !== o) throw new SimError("order filed at wrong level");
        live += q.length;
      }
      for (const qty of this.levelQty.get(side)!.values()) if (qty < 0) throw new SimError("negative level quantity");
    }
    if (live !== this.orders.size) throw new SimError("orphan orders in index");
    const bb = this.best(BUY);
    const ba = this.best(SELL);
    if (bb !== null && ba !== null && !(bb < ba)) throw new SimError("crossed book");
  }
}

// ---------------------------------------------------------------- ledger.py

class Ledger {
  rcash: number[];
  rinv: number[];
  totalCash: number;
  totalInv: number;
  constructor(public cash: number[], public inv: number[]) {
    this.rcash = cash.map(() => 0);
    this.rinv = cash.map(() => 0);
    this.totalCash = cash.reduce((a, b) => a + b, 0);
    this.totalInv = inv.reduce((a, b) => a + b, 0);
  }
  freeCash(a: number): number {
    return this.cash[a] - this.rcash[a];
  }
  freeInv(a: number): number {
    return this.inv[a] - this.rinv[a];
  }
  canPlaceLimit(a: number, side: Side, price: number, qty: number): boolean {
    return side === BUY ? this.freeCash(a) >= price * qty : this.freeInv(a) >= qty;
  }
  reserve(o: Order): void {
    if (o.side === BUY) {
      const amt = o.price * o.qty;
      if (this.freeCash(o.owner) < amt) throw new SimError("insufficient free cash to reserve");
      this.rcash[o.owner] += amt;
    } else {
      if (this.freeInv(o.owner) < o.qty) throw new SimError("insufficient free inventory to reserve");
      this.rinv[o.owner] += o.qty;
    }
  }
  release(owner: number, side: Side, price: number, qty: number): void {
    if (side === BUY) this.rcash[owner] -= price * qty;
    else this.rinv[owner] -= qty;
    if (this.rcash[owner] < 0 || this.rinv[owner] < 0) throw new SimError("reservation released below zero");
  }
  settle(f: Fill): void {
    const q = f.qty;
    const amt = f.price * q;
    const m = f.maker_owner;
    const t = f.taker_owner;
    if (f.taker_side === BUY) {
      this.rinv[m] -= q;
      this.inv[m] -= q;
      this.cash[m] += amt;
      this.cash[t] -= amt;
      this.inv[t] += q;
    } else {
      this.rcash[m] -= amt;
      this.cash[m] -= amt;
      this.inv[m] += q;
      this.inv[t] -= q;
      this.cash[t] += amt;
    }
    if (this.cash[t] < 0 || this.inv[t] < 0 || this.cash[m] < 0 || this.inv[m] < 0) throw new SimError("negative balance after settlement");
  }
  checkInvariants(resting: Order[]): void {
    if (this.cash.reduce((a, b) => a + b, 0) !== this.totalCash) throw new SimError("cash not conserved");
    if (this.inv.reduce((a, b) => a + b, 0) !== this.totalInv) throw new SimError("inventory not conserved");
    for (let a = 0; a < this.cash.length; a++) {
      if (this.cash[a] < 0 || this.inv[a] < 0) throw new SimError(`negative balance for agent ${a}`);
      if (this.rcash[a] < 0 || this.rcash[a] > this.cash[a] || this.rinv[a] < 0 || this.rinv[a] > this.inv[a]) throw new SimError(`bad reservation for agent ${a}`);
    }
    const rc = this.cash.map(() => 0);
    const ri = this.cash.map(() => 0);
    for (const o of resting) {
      if (o.side === BUY) rc[o.owner] += o.price * o.qty;
      else ri[o.owner] += o.qty;
    }
    for (let a = 0; a < rc.length; a++) if (rc[a] !== this.rcash[a] || ri[a] !== this.rinv[a]) throw new SimError("reservations do not match resting orders");
  }
}

// ---------------------------------------------------------------- agents.py

interface View {
  best_bid: number | null;
  best_ask: number | null;
  mid: number;
  mid_lag: number;
  mid_ma: number;
  tick: number;
}

type Intent = ["M", Side, number] | ["L", Side, number, number];

export function snap(price: number, tick: number, side: Side): number {
  const p = side === BUY ? Math.floor(price / tick) * tick : Math.ceil(price / tick) * tick;
  return Math.max(tick, Math.trunc(p));
}

function drawSize(u: number, maxSize: number): number {
  const k = Math.floor(u * maxSize);
  return (k < maxSize ? k : maxSize - 1) + 1;
}

function ziRule(v: View, s: Stream, marketProb: number, maxOffset: number, maxSize: number): Intent {
  const uMkt = s.uniform();
  const uSide = s.uniform();
  const uSize = s.uniform();
  const uOff = s.uniform();
  const side: Side = uSide < 0.5 ? BUY : SELL;
  const qty = drawSize(uSize, maxSize);
  if (uMkt < marketProb) return ["M", side, qty];
  let off = Math.floor(uOff * (maxOffset + 1));
  off = off <= maxOffset ? off : maxOffset;
  if (side === BUY) {
    const ref = v.best_ask !== null ? v.best_ask : v.mid;
    return ["L", side, snap(ref - off, v.tick, BUY), qty];
  }
  const ref = v.best_bid !== null ? v.best_bid : v.mid;
  return ["L", side, snap(ref + off, v.tick, SELL), qty];
}

function passivePrice(v: View, side: Side): number {
  const t = v.tick;
  if (side === BUY) {
    if (v.best_bid !== null) return v.best_bid;
    if (v.best_ask !== null) return Math.max(t, v.best_ask - t);
    return snap(v.mid, t, BUY);
  }
  if (v.best_ask !== null) return v.best_ask;
  if (v.best_bid !== null) return v.best_bid + t;
  return snap(v.mid, t, SELL);
}

function directional(side: Side, v: View, uMkt: number, uSize: number, marketProb: number, maxSize: number): Intent {
  const qty = drawSize(uSize, maxSize);
  if (uMkt < marketProb) return ["M", side, qty];
  return ["L", side, passivePrice(v, side), qty];
}

const sign = (x: number): number => (x > 0 ? 1 : 0) - (x < 0 ? 1 : 0);

function tfRule(v: View, s: Stream, mp: number, maxSize: number): Intent | null {
  const uMkt = s.uniform();
  const uSize = s.uniform();
  const d = sign(v.mid - v.mid_lag);
  if (d === 0) return null;
  return directional(d > 0 ? BUY : SELL, v, uMkt, uSize, mp, maxSize);
}

function mrRule(v: View, s: Stream, mp: number, maxSize: number): Intent | null {
  const uMkt = s.uniform();
  const uSize = s.uniform();
  const d = -sign(v.mid - v.mid_ma);
  if (d === 0) return null;
  return directional(d > 0 ? BUY : SELL, v, uMkt, uSize, mp, maxSize);
}

function paRule(v: View, s: Stream, mp: number, maxSize: number, skipProb: number): Intent | null {
  const uSkip = s.uniform();
  const uSide = s.uniform();
  const uMkt = s.uniform();
  const uSize = s.uniform();
  if (uSkip < skipProb) return null;
  return directional(uSide < 0.5 ? BUY : SELL, v, uMkt, uSize, mp, maxSize);
}

// ---------------------------------------------------------------- simulate.py

export type AgentType = "ZI" | "TF" | "MR" | "PA";

export interface BookSnapshot {
  step: number;
  bids: [number, number][];
  asks: [number, number][];
}

export interface SimOutput {
  seed: number;
  config: SimConfig;
  best_bid: Int32Array;
  best_ask: Int32Array;
  mid: Float64Array;
  depth_best: Int32Array;
  volume: Int32Array;
  counts: Record<string, number | Record<AgentType, number>>;
  final_cash: number[];
  final_inventory: number[];
  shock: { step: number; bid_depth: number; qty: number; pre_shock_mid: number; filled: number } | null;
  snapshots: BookSnapshot[];
  invariants_passed: boolean;
}

export interface SimOptions {
  /** Record a book snapshot (top levels per side) every this many steps; 0 records none. */
  snapshotEvery?: number;
  snapshotLevels?: number;
  /** Called every progressEvery steps; returning false cancels the run. */
  onProgress?: (t: number) => boolean | Promise<boolean>;
  progressEvery?: number;
}

export class Cancelled extends Error {}

function types(c: Composition): AgentType[] {
  const out: AgentType[] = [];
  for (const k of ["ZI", "TF", "MR", "PA"] as const) for (let i = 0; i < c[k]; i++) out.push(k);
  return out;
}

export async function simulate(cfg: SimConfig, seed: number, opts: SimOptions = {}): Promise<SimOutput> {
  validateConfig(cfg);
  const st = makeStreams(seed);
  const tys = types(cfg.composition);
  const n = tys.length;
  const hasShock = cfg.shock_step !== null;
  const ledger = new Ledger(
    [...tys.map(() => cfg.initial_cash), ...(hasShock ? [0] : [])],
    [...tys.map(() => cfg.initial_inventory), ...(hasShock ? [cfg.shock_inventory] : [])],
  );
  const book = new OrderBook();
  const expiries = new MinHeap<[number, number]>((x, y) => x[0] < y[0] || (x[0] === y[0] && x[1] < y[1]));
  const tick = cfg.tick;
  const T = cfg.steps;
  const L = cfg.lookback;
  const zero = (): Record<AgentType, number> => ({ ZI: 0, TF: 0, MR: 0, PA: 0 });
  const activations = zero();
  const noOrder = zero();
  const c = {
    submitted: 0, submitted_post_burn_in: 0, rejected: 0, rejected_post_burn_in: 0, market_orders: 0, limit_orders: 0,
    fills: 0, self_fills: 0, expired: 0, market_unfilled_units: 0, seed_orders_placed: 0, seed_orders_rejected: 0,
  };

  const place = (owner: number, intent: Intent, t: number): number => {
    const post = t > cfg.burn_in;
    c.submitted++;
    if (post) c.submitted_post_burn_in++;
    let fills: Fill[];
    if (intent[0] === "M") {
      const [, side, qty] = intent;
      c.market_orders++;
      let left: number;
      if (side === BUY) {
        const cap = ledger.freeCash(owner);
        const ba = book.best(SELL);
        if (ba !== null && cap < ba) {
          c.rejected++;
          if (post) c.rejected_post_burn_in++;
          return 0;
        }
        [fills, left] = book.submitMarket(owner, BUY, qty, cap);
      } else {
        if (ledger.freeInv(owner) < qty) {
          c.rejected++;
          if (post) c.rejected_post_burn_in++;
          return 0;
        }
        [fills, left] = book.submitMarket(owner, SELL, qty, null);
      }
      c.market_unfilled_units += left;
    } else {
      const [, side, price, qty] = intent;
      c.limit_orders++;
      if (!ledger.canPlaceLimit(owner, side, price, qty)) {
        c.rejected++;
        if (post) c.rejected_post_burn_in++;
        return 0;
      }
      let rested: Order | null;
      [fills, rested] = book.submitLimit(owner, side, price, qty, t + cfg.order_lifetime);
      if (rested !== null) {
        ledger.reserve(rested);
        expiries.push([rested.expiry as number, rested.oid]);
      }
    }
    let traded = 0;
    for (const f of fills) {
      ledger.settle(f);
      traded += f.qty;
      if (f.maker_owner === f.taker_owner) c.self_fills++;
    }
    c.fills += fills.length;
    return traded;
  };

  // initial book (t = 0) from the init stream
  const ziIds = tys.map((ty, i) => (ty === "ZI" ? i : -1)).filter((i) => i >= 0);
  const p0 = cfg.initial_price;
  const sInit = st.init;
  for (const side of [BUY, SELL] as Side[]) {
    for (let k0 = 0; k0 < cfg.initial_orders_per_side; k0++) {
      const owner = ziIds[sInit.integer(ziIds.length)];
      const k = 1 + sInit.integer(Math.max(1, cfg.zi_limit_offset));
      const qty = 1 + sInit.integer(cfg.max_order_size);
      let price = side === BUY ? snap(p0 - k, tick, BUY) : snap(p0 + k, tick, SELL);
      if (side === BUY && price >= p0) price = Math.max(tick, p0 - tick);
      if (!ledger.canPlaceLimit(owner, side, price, qty)) {
        c.seed_orders_rejected++;
        continue;
      }
      const [fills, rested] = book.submitLimit(owner, side, price, qty, cfg.order_lifetime);
      for (const f of fills) ledger.settle(f);
      if (rested !== null) {
        ledger.reserve(rested);
        expiries.push([rested.expiry as number, rested.oid]);
      }
      c.seed_orders_placed++;
    }
  }

  const bestBid = new Int32Array(T + 1);
  const bestAsk = new Int32Array(T + 1);
  const mid = new Float64Array(T + 1);
  const depthBest = new Int32Array(T + 1);
  const volume = new Int32Array(T + 1);
  const midOf = (bb: number | null, ba: number | null, last: number): number => (bb !== null && ba !== null ? (bb + ba) / 2.0 : last);
  const snapEvery = opts.snapshotEvery ?? 0;
  const snapLevels = opts.snapshotLevels ?? 10;
  const snapshots: BookSnapshot[] = [];
  const takeSnap = (t: number) => snapshots.push({ step: t, bids: book.snapshot(BUY, snapLevels), asks: book.snapshot(SELL, snapLevels) });

  let bb = book.best(BUY);
  let ba = book.best(SELL);
  let lastMid = midOf(bb, ba, p0);
  bestBid[0] = bb ?? 0;
  bestAsk[0] = ba ?? 0;
  mid[0] = lastMid;
  depthBest[0] = (bb ? book.qtyAt(BUY, bb) : 0) + (ba ? book.qtyAt(SELL, ba) : 0);
  const prefix = new Float64Array(T + 2);
  prefix[1] = lastMid;
  if (snapEvery > 0) takeSnap(0);
  let shock: SimOutput["shock"] = null;
  const progressEvery = opts.progressEvery ?? 5_000;

  for (let t = 1; t <= T; t++) {
    while (expiries.size > 0 && expiries.top()[0] <= t) {
      const [, oid] = expiries.pop();
      if (book.orders.has(oid)) {
        const r = book.cancel(oid);
        ledger.release(r.owner, r.side, r.price, r.qty);
        c.expired++;
      }
    }
    let traded = 0;
    if (hasShock && t === cfg.shock_step) {
      const bidDepth = book.depth(BUY);
      const qty = Math.max(1, Math.floor(cfg.shock_fraction * bidDepth));
      st.shock.uniform();
      shock = { step: t, bid_depth: bidDepth, qty, pre_shock_mid: mid[t - 1], filled: 0 };
      traded += place(n, ["M", SELL, qty], t);
      shock.filled = traded;
    }
    const a = st.activation.integer(n);
    const ty = tys[a];
    activations[ty]++;
    bb = book.best(BUY);
    ba = book.best(SELL);
    const curMid = midOf(bb, ba, lastMid);
    const lagIdx = t - L > 0 ? t - L : 0;
    const lo = t - L > 0 ? t - L : 0;
    const ma = (prefix[t] - prefix[lo]) / (t - lo);
    const view: View = { best_bid: bb, best_ask: ba, mid: curMid, mid_lag: mid[lagIdx], mid_ma: ma, tick };
    let intent: Intent | null;
    if (ty === "ZI") intent = ziRule(view, st.zi, cfg.zi_market_prob, cfg.zi_limit_offset, cfg.max_order_size);
    else if (ty === "TF") intent = tfRule(view, st.strategic, cfg.strategic_market_prob, cfg.max_order_size);
    else if (ty === "MR") intent = mrRule(view, st.strategic, cfg.strategic_market_prob, cfg.max_order_size);
    else intent = paRule(view, st.pa, cfg.strategic_market_prob, cfg.max_order_size, cfg.pa_skip_prob);
    if (intent === null) noOrder[ty]++;
    else traded += place(a, intent, t);
    bb = book.best(BUY);
    ba = book.best(SELL);
    lastMid = midOf(bb, ba, lastMid);
    bestBid[t] = bb ?? 0;
    bestAsk[t] = ba ?? 0;
    mid[t] = lastMid;
    depthBest[t] = (bb ? book.qtyAt(BUY, bb) : 0) + (ba ? book.qtyAt(SELL, ba) : 0);
    volume[t] = traded;
    prefix[t + 1] = prefix[t] + lastMid;
    if (snapEvery > 0 && t % snapEvery === 0) takeSnap(t);
    if (opts.onProgress && t % progressEvery === 0) {
      if ((await opts.onProgress(t)) === false) throw new Cancelled("cancelled");
    }
  }

  book.checkInvariants();
  ledger.checkInvariants(book.restingOrders());
  return {
    seed,
    config: cfg,
    best_bid: bestBid,
    best_ask: bestAsk,
    mid,
    depth_best: depthBest,
    volume,
    counts: { ...c, activations, no_order: noOrder },
    final_cash: [...ledger.cash],
    final_inventory: [...ledger.inv],
    shock,
    snapshots,
    invariants_passed: true,
  };
}
