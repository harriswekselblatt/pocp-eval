import {readFileSync} from 'node:fs';
import pMap, {pMapSettled, pMapKeyed, pMapSkip} from '../index.js';
import {check} from '../bench-support/assertions.mjs';
const expected = JSON.parse(readFileSync(new URL('./fixtures/bench-expected.json', import.meta.url)));
const actual = await pMap([1, 2, 3], x => x === 2 ? pMapSkip : x * 2);
console.log('BENCH_ACTUAL='+JSON.stringify(actual));
check(actual, expected);
