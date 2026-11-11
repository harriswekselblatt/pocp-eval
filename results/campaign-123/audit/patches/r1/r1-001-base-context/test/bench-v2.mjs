import {readFileSync} from 'node:fs';
import pMap, {pMapSettled, pMapKeyed, pMapSkip} from '../index.js';
import {check} from '../bench-support/assertions.mjs';
const expected = JSON.parse(readFileSync(new URL('./fixtures/bench-expected.json', import.meta.url)));
const actual = await pMapSettled([1, 2], x => x === 1 ? x * 2 : Promise.reject('bad'));
console.log('BENCH_ACTUAL='+JSON.stringify(actual));
check(actual, expected);
