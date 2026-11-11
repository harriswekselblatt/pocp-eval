from edit import sub
sub('index.js','''		validateOptions(iterable, mapper, concurrency);

		const result = [];''','''		validateOptions(iterable, mapper, concurrency);

		// A wrong `signal` would otherwise fail later with an internal error about `addEventListener`, or be ignored when it is falsy.
		if (signal !== undefined && signal !== null && typeof signal.addEventListener !== 'function') {
			throw new TypeError(`Expected \\`signal\\` to be an \\`AbortSignal\\`, got (${typeof signal})`);
		}

		const result = [];''')
sub('readme.md','''Type: [`AbortSignal`](https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal)

You can abort the promises''','''Type: [`AbortSignal`](https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal)

Any other value, except `undefined` or `null`, rejects with a `TypeError`.

You can abort the promises''')
sub('index.d.ts','''	/**
	You can abort the promises using [`AbortController`](https://developer.mozilla.org/en-US/docs/Web/API/AbortController).
''','''	/**
	You can abort the promises using [`AbortController`](https://developer.mozilla.org/en-US/docs/Web/API/AbortController).

	Any other value than an `AbortSignal`, except `undefined` or `null`, rejects with a `TypeError`.
''')
with open('test.js','a') as f:
    f.write('''
test('rejects a `signal` that is not an `AbortSignal`', async t => {
	for (const signal of [{}, 'abort', 1, true, {aborted: true}]) {
		const message = `Expected \\`signal\\` to be an \\`AbortSignal\\`, got (${typeof signal})`;
		await t.throwsAsync(pMap([1], value => value, {signal}), {instanceOf: TypeError, message}); // eslint-disable-line no-await-in-loop
		await t.throwsAsync(pMapSettled([1], value => value, {signal}), {instanceOf: TypeError, message}); // eslint-disable-line no-await-in-loop
		await t.throwsAsync(pMapKeyed({a: 1}, value => value, {signal}), {instanceOf: TypeError, message}); // eslint-disable-line no-await-in-loop
		await t.throwsAsync(pMapSettledKeyed(new Map([['a', 1]]), value => value, {signal}), {instanceOf: TypeError, message}); // eslint-disable-line no-await-in-loop
	}

	t.deepEqual(await pMap([1], value => value, {signal: undefined}), [1]);
	t.deepEqual(await pMap([1], value => value, {signal: null}), [1]);
	t.deepEqual(await pMap([1], value => value, {signal: new AbortController().signal}), [1]);
});
''')
