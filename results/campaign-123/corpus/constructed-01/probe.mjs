// Differential behavior probe for constructed-01. Usage: node probe.mjs <dir-with-index.js>. Prints JSON.
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const lib = await import(pathToFileURL(path.resolve(process.argv[2], 'index.js')));
const {default: pMap, pMapSettled, pMapKeyed, pMapSettledKeyed, pMapIterable, pMapSkip, pMapStop} = lib;

const describe = value => {
	if (value instanceof Error) return {error: value.constructor.name, message: value.message, errors: value.errors?.map(describe)};
	if (value instanceof Map) return {map: [...value].map(([k, v]) => [describe(k), describe(v)])};
	if (typeof value === 'symbol') return {symbol: value.description};
	if (typeof value === 'number' && Number.isNaN(value)) return {nan: true};
	if (value && typeof value === 'object') {
		return {proto: Object.getPrototypeOf(value) === null ? 'null' : (Array.isArray(value) ? 'array' : 'object'),
			own: Reflect.ownKeys(value).map(k => [describe(k), Object.getOwnPropertyDescriptor(value, k).enumerable, describe(value[k])])};
	}
	return value;
};
const outcome = async thunk => {
	try {
		return {ok: describe(await thunk())};
	} catch (error) {
		return {threw: describe(error)};
	}
};
const collect = async iterable => {
	const out = [];
	for await (const v of iterable) out.push(v);
	return out;
};
const closingSource = log => ({
	[Symbol.iterator]() {
		let i = 0;
		return {next: () => ({done: i >= 5, value: i++}), return() { log.push('return'); return {done: true}; }};
	},
});

const s = {};
s.contract_mapping = await outcome(() => pMap([1, 2], x => x * 2));
s.contract_settled = await outcome(() => pMapSettled([1, 2], x => x === 1 ? x * 2 : Promise.reject('bad')));
s.contract_keyed = await outcome(() => pMapKeyed({a: 2, b: 3}, x => x * 2));
s.skip_stop = await outcome(() => pMap([1, pMapSkip, 2, 3, 4], x => x === 3 ? pMapStop : x, {concurrency: 1}));
for (const [name, opts] of [['reject', {}], ['stop', {}], ['done', {}]]) {
	const log = [];
	const mapper = name === 'reject' ? x => { if (x === 1) throw new Error('m'); return x; } : name === 'stop' ? x => x === 2 ? pMapStop : x : x => x;
	s[`close_${name}`] = {result: await outcome(() => pMap(closingSource(log), mapper, {concurrency: 1, ...opts})), log};
}
s.aggregate = await outcome(() => pMap([1, 2, 3, 4], async x => { if (x % 2 === 0) throw new Error(`e${x}`); return x; }, {stopOnError: false, concurrency: 2}));
s.aggregate_undefined = await outcome(() => pMap([1, 2], async x => { if (x === 2) throw undefined; return x; }, {stopOnError: false}));
s.aggregate_input = await outcome(() => pMap([Promise.reject(new Error('in')), 2], x => x, {stopOnError: false}));
s.aggregate_after_stop = await outcome(() => pMap([1, 2, 3], x => { if (x === 1) throw new Error('a'); if (x === 2) return pMapStop; throw new Error('c'); }, {stopOnError: false, concurrency: 1}));
const sym = Symbol('k');
s.keyed_object = await outcome(() => pMapKeyed(Object.assign(JSON.parse('{"__proto__": 1, "toString": 2, "1": 3}'), {[sym]: 4}), (v, k) => [v, typeof k]));
s.keyed_map = await outcome(() => pMapKeyed(new Map([[{}, 1], [Number.NaN, 2], ['x', 3]]), v => v * 2));
s.keyed_skip = await outcome(() => pMapKeyed({a: 1, b: 2, c: 3}, v => v === 2 ? pMapSkip : v));
s.settled_keyed = await outcome(() => pMapSettledKeyed({a: 1, b: Promise.reject(new Error('b'))}, v => v));
s.iterable = await outcome(() => collect(pMapIterable([1, 2, 3, 4], x => x * 3, {concurrency: 2})));
s.iterable_unordered = await outcome(async () => (await collect(pMapIterable([1, 2, 3], async x => x, {concurrency: 3, preserveOrder: false}))).sort());
s.async_source = await outcome(() => pMap((async function * () { yield 1; yield 2; })(), x => x + 1, {concurrency: 2}));
s.string_input = await outcome(() => pMapSettled('a\u{1F600}b', v => v));
for (const [name, opts] of [['c0', {concurrency: 0}], ['c15', {concurrency: 1.5}], ['cstr', {concurrency: '2'}]]) s[`validate_${name}`] = await outcome(() => pMap([], x => x, opts));
s.validate_backpressure = await outcome(() => collect(pMapIterable([], x => x, {concurrency: 2, backpressure: 1})));
s.validate_null = await outcome(() => pMap(null, x => x));
s.validate_number = await outcome(() => pMap(5, x => x));
s.validate_iterable_null = await outcome(async () => pMapIterable(null, x => x));
s.validate_mapper = await outcome(() => pMap([], 'nope'));
for (const [name, signal] of [['object', {}], ['string', 'x'], ['null', null], ['aborted_like', {aborted: true}]]) s[`signal_${name}`] = await outcome(() => pMap([1], x => x, {signal}));
s.signal_real = await outcome(() => { const c = new AbortController(); c.abort(new Error('stop')); return pMap([1], x => x, {signal: c.signal}); });
console.log(JSON.stringify(s, null, 1));
