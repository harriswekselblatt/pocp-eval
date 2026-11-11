with open('test.js','a') as f:
    f.write('''
test('pMapKeyed - keeps `Map` keys that are not strings by identity', async t => {
	const objectKey = {id: 1};
	const input = new Map([[objectKey, 1], [Number.NaN, 2], [3, 3]]);
	const seenKeys = [];

	const result = await pMapKeyed(input, (value, key) => {
		seenKeys.push(key);
		return value * 10;
	});

	t.true(result instanceof Map);
	t.is([...result.keys()][0], objectKey);
	t.is(result.get(objectKey), 10);
	t.is(result.get(Number.NaN), 20);
	t.is(result.get(3), 30);
	t.false(result.has('3'));
	t.is(seenKeys[0], objectKey);
	t.true(Number.isNaN(seenKeys[1]));
	t.is(seenKeys[2], 3);
});
''')
