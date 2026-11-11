import assert from 'node:assert/strict';
export function check(actual, expected) { assert.deepEqual(JSON.parse(JSON.stringify(actual)), expected); }
