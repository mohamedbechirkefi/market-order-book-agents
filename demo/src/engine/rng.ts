// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Port of src/market/rng.py: numpy SeedSequence(seed).spawn(6), one PCG64 Generator per
// named stream, Generator.random() doubles. The value sequence is bit-identical to the
// Python engine (checked against a fixture in engine.test.ts).

export const STREAM_NAMES = ["activation", "zi", "strategic", "pa", "shock", "init"] as const;
export type StreamName = (typeof STREAM_NAMES)[number];

const M32 = 0xffffffffn;
const M64 = (1n << 64n) - 1n;
const M128 = (1n << 128n) - 1n;

// numpy/random/bit_generator.pyx constants
const INIT_A = 0x43b0d7e5;
const MULT_A = 0x931e8875;
const INIT_B = 0x8b51f9dd;
const MULT_B = 0x58f38ded;
const MIX_MULT_L = 0xca01f9dd;
const MIX_MULT_R = 0x4973f715;
const XSHIFT = 16;
const POOL_SIZE = 4;

const mul32 = (a: number, b: number): number => Math.imul(a, b) >>> 0;

function seedEntropy(seed: number): number[] {
  // _coerce_to_uint32_array for a non-negative int: little-endian 32-bit words, at least one.
  const words: number[] = [];
  let v = BigInt(seed);
  do {
    words.push(Number(v & M32));
    v >>= 32n;
  } while (v > 0n);
  return words;
}

function makePool(entropy: number[], spawnKey: number[]): number[] {
  const run = [...entropy];
  if (spawnKey.length > 0 && run.length < POOL_SIZE) while (run.length < POOL_SIZE) run.push(0);
  const ent = [...run, ...spawnKey];
  const pool = new Array<number>(POOL_SIZE).fill(0);
  let hashConst = INIT_A;
  const hashmix = (value: number): number => {
    value = (value ^ hashConst) >>> 0;
    hashConst = mul32(hashConst, MULT_A);
    value = mul32(value, hashConst);
    value = (value ^ (value >>> XSHIFT)) >>> 0;
    return value;
  };
  const mix = (x: number, y: number): number => {
    let r = (mul32(MIX_MULT_L, x) - mul32(MIX_MULT_R, y)) >>> 0;
    r = (r ^ (r >>> XSHIFT)) >>> 0;
    return r;
  };
  for (let i = 0; i < POOL_SIZE; i++) pool[i] = hashmix(i < ent.length ? ent[i] : 0);
  for (let s = 0; s < POOL_SIZE; s++)
    for (let d = 0; d < POOL_SIZE; d++) if (s !== d) pool[d] = mix(pool[d], hashmix(pool[s]));
  for (let s = POOL_SIZE; s < ent.length; s++) for (let d = 0; d < POOL_SIZE; d++) pool[d] = mix(pool[d], hashmix(ent[s]));
  return pool;
}

/** SeedSequence.generate_state(n, uint64) for the given pool. */
export function generateState64(pool: number[], n: number): bigint[] {
  let hashConst = INIT_B;
  const w32: number[] = [];
  for (let i = 0; i < 2 * n; i++) {
    let v = pool[i % POOL_SIZE];
    v = (v ^ hashConst) >>> 0;
    hashConst = mul32(hashConst, MULT_B);
    v = mul32(v, hashConst);
    v = (v ^ (v >>> XSHIFT)) >>> 0;
    w32.push(v);
  }
  const out: bigint[] = [];
  for (let i = 0; i < n; i++) out.push(BigInt(w32[2 * i]) | (BigInt(w32[2 * i + 1]) << 32n));
  return out;
}

export function childPool(seed: number, child: number): number[] {
  return makePool(seedEntropy(seed), [child]);
}

const PCG_MULT = (0x2360ed051fc65da4n << 64n) | 0x4385df649fccf645n;

/** Buffered U[0, 1) stream from one PCG64 bit generator, as market.rng.Stream. */
export class Stream {
  private state: bigint;
  private inc: bigint;
  drawn = 0;

  constructor(pool: number[]) {
    const v = generateState64(pool, 4);
    const initstate = (v[0] << 64n) | v[1];
    const initseq = (v[2] << 64n) | v[3];
    this.state = 0n;
    this.inc = ((initseq << 1n) | 1n) & M128;
    this.step();
    this.state = (this.state + initstate) & M128;
    this.step();
  }

  private step(): void {
    this.state = (this.state * PCG_MULT + this.inc) & M128;
  }

  private next64(): bigint {
    this.step();
    const s = this.state;
    const x = ((s >> 64n) ^ s) & M64;
    const rot = s >> 122n;
    return ((x >> rot) | (x << ((64n - rot) & 63n))) & M64;
  }

  uniform(): number {
    this.drawn++;
    return Number(this.next64() >> 11n) * (1.0 / 9007199254740992.0);
  }

  /** Uniform integer on 0..n-1 from one uniform draw. */
  integer(n: number): number {
    if (n < 1) throw new Error("n must be >= 1");
    const k = Math.floor(this.uniform() * n);
    return k < n ? k : n - 1;
  }
}

export function makeStreams(seed: number): Record<StreamName, Stream> {
  if (!Number.isInteger(seed) || seed < 0) throw new Error(`seed must be a non-negative int, got ${seed}`);
  const out = {} as Record<StreamName, Stream>;
  STREAM_NAMES.forEach((name, i) => {
    out[name] = new Stream(childPool(seed, i));
  });
  return out;
}
