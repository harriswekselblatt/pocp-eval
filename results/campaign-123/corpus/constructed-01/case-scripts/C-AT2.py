with open('test.js','a') as f:
    f.write('''
test('pMapSettledKeyed - a value that is a thenable that rejects settles as rejected, without calling the mapper for it', async t => {
	const error = new Error('thenable');
	const thenable = {
		then(resolve, reject) { // eslint-disable-line unicorn/no-thenable
			reject(error);
		},
	};
	const mappedValues = [];

	const result = await pMapSettledKeyed({a: 1, b: thenable}, value => {
		mappedValues.push(value);
		return value * 2;
	});

	t.deepEqual(result.a, {status: 'fulfilled', value: 2});
	t.is(result.b.status, 'rejected');
	t.is(result.b.reason, error);
	t.deepEqual(mappedValues, [1]);
});
''')
